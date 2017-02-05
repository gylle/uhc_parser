"""Count the total score for games"""
from logbook import Logger

log = Logger('Count')
SCORE = {
    'winner': 3,
    'kill': 1,
    'death': 0,
    'killed': 0,
}

def count_highscore(servers):
    """input a list of server/games to be countend"""
    log.debug("Started counting the highscore")

    players = {}

    for server in servers.items():
        print(server)

    return True


