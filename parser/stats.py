""" Calculate all the stats we want to know about games and players """
from operator import itemgetter

PLAYERS = {}

def score_count(games):
    """ Main count of all games in a store """
    highscore = Highscore()
    for game in games.items():
        players = [(player, game.player_info(player)) for player in game.get_playing_players()]
        highscore.add_players(players)
        for action in game.get_actions():
            if action['action'] == 'death':
                highscore.count_kill_action(action)
            elif action['action'] == 'team_win':
                highscore.count_team_win(action)
            elif action['action'] == 'survivors':
                highscore.count_survivors(action)
    return highscore.get_highscore()

class Highscore(object):
    """ Defines a highscore table to track the players score """
    def __init__(self):
        self.players = {}

    def __repr__(self):
        return '<Class Higscore>'

    def _add_player(self, player, uuid):
        """ Found new player that we should add to the highscore table """
        #we dont want to overwrite an existing player
        if self.players.get(player) is None:
            self.players[player] = {'uuid': uuid,
                                    'kills': 0,
                                    'deaths': 0,
                                    'wins': 0,
                                    'games': 0,
                                    'survived': 0}

    def add_players(self, players):
        """ Add all players in the game so we know they have a spot in the highscore"""
        for player in players:
            self._add_player(player[0], player[1]['uuid'])
            self.count_game(player[0])

    def count_kill_action(self, action):
        """ An action was found that we need to count """
        killer = action.get('killed_by')
        died = action['player']
        if killer is not None:
            #something killed player
            if self.players.get(killer) is not None:
                #something is not a mob, count it!
                self.players[killer]['kills'] = self.players[killer]['kills'] + 1
        #register death of player
        self.players[died]['deaths'] = self.players[died]['deaths'] + 1

    def count_survivors(self, action):
        """ count the points for survivors """
        for player in action['players']:
            self.players[player]['survived'] = self.players[player]['survived'] + 1

    def count_team_win(self, action):
        """ count the players in a team for scoring """
        for player in action['players']:
            self.players[player]['wins'] = self.players[player]['wins'] + 1

    def count_game(self, player):
        """ Add a game to the player since playing """
        self.players[player]['games'] = self.players[player]['games'] + 1

    def get_highscore(self):
        """ Returns the highscore as an ordered list, leader first """
        data = []
        for player, info in self.players.items():
            score = 0
            #kills is 1 point
            score = info['kills'] * 1
            #team win is 1 point
            score = score + info['wins'] * 1
            #alive at the end is 1 point
            score = score + info['survived'] * 1
            self.players[player]['nickname'] = player
            self.players[player]['score'] = score
            self.players[player]['kd'] = round(info['kills'] / info['deaths'], 3)
            data.append(self.players[player])
        sort_list = sorted(data, key=itemgetter('score'), reverse=True)
        for index, player in enumerate(sort_list):
            player['place'] = index+1
        return sort_list
