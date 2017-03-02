""" Parser module for UHC Parser
Here we have everything converting the logfile into actions based on
regular expressions, it calls a function that will return an 'action dict'
"""
import re
from logbook import Logger

from . models import State, Game, Store
__ALL__ = [
    "death",
    "game_start",
    "player_mode",
    "team_color",
    "team_members",
    "server_start",
    "server_stop",
    "server_crash",
    "player_join",
    "player_ip",
    "parse"
]

GAME_STORE = Store()

def death(data, reason=None):
    """ Creates a action log entry for a players death """
    action = {'action': 'death', 'player': data[1], 'timestamp':data[0], 'reason': reason}
    if len(data) > 2:
        action['killed_by'] = data[2]
    return action

def game_start(data):
    """ Creates an action log entry for game start"""
    action = {'action': 'game_start',
              'timestamp': data[0],
              'end_blocks': data[1],
              'start_blocks': data[2],
              'seconds': data[3]}
    return action

def player_mode(data):
    """ Creates an action log entry when players mode changes """
    action = {'action': 'player_mode',
              'timestamp': data[0],
              'player': data[1],
              'mode': data[2]}
    return action

def team_color(data):
    """ Creates an action log entry for team color """
    action = {'action': 'team_color',
              'timestamp': data[0],
              'team': data[1],
              'color': data[2]}
    return action

def team_members(data):
    """ Creates an action log entry for team creation and member assigment"""
    action = {'action': 'team_members',
              'timestamp': data[0],
              'team': data[1]}
    players = []
    for player in data[2].split(' '):
        if 'and' in player:
            continue
        players.append(player.rstrip(','))
    action['players'] = players
    return action

def server_start(data):
    """ Create an action log entry for server start """
    action = {'action': 'server_start',
              'timestamp': data[0],
              'version': data[1]}
    return action

def server_stop(data):
    """ Create an action log entry for server stop """
    action = {'action': 'server_stop',
              'timestamp': data[0]}

    return action

def server_crash(data):
    """ Create an action log entry for server crash """
    action = {'action': 'server_crash',
              'timestamp': data[0],}
    return action

def player_join(data):
    """ Create an action log entry for when a player joins """
    action = {'action':'player_join',
              'timestamp': data[0],
              'player': data[1],
              'uuid': data[2]}
    return action

def player_ip(data):
    """ Create an action log entry for a players ip address """
    action = {'action':'player_ip',
              'timestamp': data[0],
              'player': data[1],
              'ipaddress': data[2]}
    return action

#Big list of regexes and the function we want to apply to it for formatting the data back
ACTIONS = [(re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' was slain by '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'), death, 'slain'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' was shot by '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'), death, 'shot'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' blew up'), death, 'blew_up'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' was blown up by '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'), death, 'blown_up'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' suffocated in a wall'), death, 'suffocated_wall'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' fell from a high place'), death, 'fell'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' burned to death'), death, 'burned'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' was burnt to a crisp whilst fighting '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'), death, 'burned_fighting'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' drowned'), death, 'drowned'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' tried to swim in lava'), death, 'lava'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+)'
                       r' \[INFO\] (?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1} '
                       r'tried to swim in lava to escape (?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'),
            death, 'lava_escape'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'(?:[§?][0-9a-z]){0,1}(\w+)(?:[§?]r){0,1}'
                       r' hit the ground too hard'), death, 'fell_hit'),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] Shrinking world border to '
                       r'(\d+.\d) blocks wide '
                       r'\(down from (\d+.\d) blocks\) over (\d+) seconds'), game_start),
           (re.compile(r"(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] \[\w+: Set (\w+)'s"
                       r" game mode to (\w+) Mode\]"), player_mode),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] \[(\w+): Set own '
                       r'game mode to (\w+) Mode\]'), player_mode),
           (re.compile(r"(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] Set (\w+)'s "
                       r"game mode to (\w+) Mode"), player_mode),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] UUID of player (?P<player>.*) '
                       r'is (?P<uuid>.*)'), player_join),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] (?P<player>.*)\[/(?P<ip>.*):\d+\]'
                       r' logged in'), player_ip),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] Set option color'
                       r' for team (?P<team>\w+) to (?P<color>\w+)'), team_color),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] Added \d player\(s\)'
                       r' to team (?P<team>\w+): (?P<members>.*)'), team_members),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] Could not add \d player\(s\) '
                       r'to team (?P<team>\w+): (?P<members>.*)'), team_members),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] \[(?:\w+): '
                       r'Added \d player\(s\) to team (?P<team>\w+): '
                       r'(?P<members>.*)\]'), team_members),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'Starting minecraft server version (.*)'), server_start),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\]'
                       r' .*Stopping the server.*'), server_stop),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[ERROR\] This crash report has been saved to:'),
            server_crash)]


def handle_action(action):
    """ Handles the action we matched, checks to see if should create/stop a game
    else adds it to an existing game for evaluation """
    #Check if the server did something we need to handle
    #like start, stop or crashed
    log = Logger('handle_action')
    if action['action'] == 'server_start':
        if GAME_STORE.last is not None:
            if GAME_STORE.last.state == State.CRASHED:
                GAME_STORE.last.add_action(action)
                log.debug("Game {g} crashed, continuing with same game"
                          .format(g=GAME_STORE.last.sid))
                return
            elif GAME_STORE.last.state == State.STARTED:
                # Mark the last game as aborted since we will start a new one
                GAME_STORE.last.state = State.ABORTED
        GAME_STORE.add(Game(action))
        log.debug("Created new game {g}".format(g=GAME_STORE.last.sid))
    elif action['action'] == 'server_stop':
        if GAME_STORE.last is None:
            return
        if GAME_STORE.last.winning_team is not None:
            GAME_STORE.last.state = State.STOPPED
        else:
            GAME_STORE.last.state = State.ABORTED
        log.debug("Stopped game {g}".format(g=GAME_STORE.last.sid))
    elif action['action'] == 'server_crash':
        if GAME_STORE.last is not None:
            GAME_STORE.last.state = State.CRASHED
            log.info("Game {g} crashed".format(g=GAME_STORE.last.sid))
    else:
        if GAME_STORE.last is not None:
            GAME_STORE.last.add_action(action)

def parse(logfile):
    """ Parse the UHC server log file for entries """
    with open(logfile, 'r') as file:
        for line in file:
            for action in ACTIONS:
                match = action[0].search(line)
                if match:
                    if action[1] == death:
                        #if it is the death, include how death happend
                        data = action[1](match.groups(), action[2])
                    else:
                        data = action[1](match.groups())
                    handle_action(data)
    return GAME_STORE
