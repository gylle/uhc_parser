"""Count the total score for games"""
from logbook import Logger

log = Logger('Count')

class PlayerStore(object):
    SCORE = {
        'winner': 3,
        'winner_dead': 2,
        'kill': 1,
        'death': 0,
        'killed': 0,
    }
    def __init__(self):
        self.players = {}

    def add_winner(self, server):
        """Add and give score for all surviving team members"""
        for player in server.games[-1].players:
            check = self.players.get(player)
            if not check:
                check = self.new_player(player, server)
            check['winner'] = check['winner'] + self.SCORE['winner']
            self.players[player] = check

    def new_player(self, player, server):
        """Add new new player """
        server_player = server.players.get(player)
        if not server_player:
            print("FETT FEL!")
        play = {'uuid': server_player.uuid, 'winner':0,}
        self.players[player] = play
        return play


def count_highscore(servers):
    """input a list of server/games to be countend"""
    log.debug("Started counting the highscore")

    store = PlayerStore()

    for server in servers.items():
        if server[1].validate():
            store.add_winner(server[1])
    print(store.players)
    return True
