"""Count the total score for games"""
import operator
from decimal import Decimal, getcontext

from logbook import Logger

log = Logger('Count')
getcontext().prec = 3

class PlayerStore(object):
    SCORE = {
        'winner': 3,
        'dead_winner': 2,
        'kills': 1,
        'deaths': 0,
        'games': 0
    }
    def __init__(self):
        self.players = {}

    def add_winner(self, server):
        """Add and give score for all surviving team members"""
        for player in server.games[-1].players:
            check = self.players.get(player)
            if not check:
                check = self.new_player(player, server)
                if not check:
                    continue
            check['winner'] = check['winner'] + 1
            self.players[player] = check

    def add_dead_winners(self, server):
        """Add a player that is dead but on a winning team"""
        deads = set(server.winning_team.players) - set(server.games[-1].players)
        for dead in deads:
            check = self.players.get(dead)
            if not check:
                check = self.new_player(dead, server)
                if not check:
                    continue
            check['dead_winner'] = check['dead_winner'] + 1
            self.players[dead] = check

    def new_player(self, player, server):
        """Add new new player """
        server_player = server.players.get(player)
        if not server_player:
            return False
        play = {'uuid': server_player.uuid,
                'winner':0,
                'dead_winner':0,
                'games': 0,
                'deaths': 0,
                'kills': 0}

        self.players[player] = play
        return play

    def add_game(self, server):
        """Adds that game to the player """
        #add everyone that joined the server, even spectators.
        for player in server.players.items():
            check = self.players.get(player[1].nickname)
            if not check:
                check = self.new_player(player[1].nickname, server)
            check['games'] = check['games'] +1
            self.players[player[1].nickname] = check

    def count_kills(self, server):
        """Count the kills for players"""
        for died, killer in server.games[-1].killed.items():
            #is this a player killer?
            #all players should be in the big list now so just check that one
            if not self.players.get(killer):
                #if the name doesn't exist by now, its a mob
                self.players[died]['deaths'] = self.players[died]['deaths'] + 1
                continue
            self.players[died]['deaths'] = self.players[died]['deaths'] + 1
            self.players[killer]['kills'] = self.players[killer]['kills'] + 1


def count_highscore(servers):
    """input a list of server/games to be countend"""
    log.debug("Started counting the highscore")

    store = PlayerStore()
    #count the different type of info from the games
    for server in servers.items():
        if server[1].validate():
            store.add_winner(server[1])
            store.add_dead_winners(server[1])
            store.add_game(server[1])
            store.count_kills(server[1])
    #now we have everything counted
    #time merge same users
    for player1 in store.players.copy().items():
        for player2 in store.players.copy().items():
            if player1[1]['uuid'] == player2[1]['uuid']:
                if player1[0] != player2[0]:
                    #not same nick, time to merge
                    player2[1]['winner'] = player2[1]['winner']+player1[1]['winner']
                    player2[1]['dead_winner'] = player2[1]['dead_winner']+player1[1]['dead_winner']
                    player2[1]['games'] = player2[1]['games']+player1[1]['games']
                    player2[1]['deaths'] = player2[1]['deaths']+player1[1]['deaths']
                    player2[1]['kills'] = player2[1]['kills']+player1[1]['kills']
                    check = player2[1].get('alt_nicks')
                    if not check:
                        player2[1]['alt_nicks'] = [player1[0]]
                    else:
                        player2[1]['alt_nicks'].append(player1[0])

                    del store.players[player1[0]]
    #print(store.players)
    #time to count the score
    scorechart = {}
    for item, points in store.SCORE.items():
        for player in store.players.items():
            score = scorechart.get(player[0])
            number = player[1][item]
            if not score:
                score = 0
            score = score + number*points
            scorechart[player[0]] = score
    listan = sorted(scorechart.items(), key=operator.itemgetter(1))

    #finally, reverse the list and add the highscore data
    highlist = []
    i = 1
    for item in reversed(listan):
        player_info = {
            'nickname': item[0],
            'score': item[1],
            'wins': store.players[item[0]]['winner'],
            'dead_wins':  store.players[item[0]]['dead_winner'],
            'games':  store.players[item[0]]['games'],
            'deaths':  store.players[item[0]]['deaths'],
            'kills':  store.players[item[0]]['kills'],
            'uuid': store.players[item[0]]['uuid'],
            'kd': str(+Decimal(store.players[item[0]]['kills']/store.players[item[0]]['deaths'])),
            'place': i
        }
        highlist.append(player_info)
        i = i + 1

    return highlist
