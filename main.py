#!/bin/env - python
#Copyright 2017 Tobias Gustavsson <tobias at rackrymd.se>
#License - See LICENSE file
from sys import stdout
from datetime import datetime, timedelta
import re
import operator
from enum import Enum, auto
import jsonpickle
import click
from logbook import Logger, StreamHandler

#TODO: Games restarts where team is not set and player modes changes is not counted
#Example: 2015-05-19 21:28:01

def get_datetime(line):
    """ Convert a logline to a datetime for the log entry """
    return datetime.strptime(line, "%Y-%m-%d %X")

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
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] '
                       r'Starting minecraft server version (.*)'), server_start),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\]'
                       r' .*Stopping the server.*'), server_stop),
           (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[ERROR\] This crash report has been saved to:'),
            server_crash)]

class State(Enum):
    """ Enumerate the state a game can be in """
    STARTED = auto()
    STOPPED = auto()
    CRASHED = auto()
    ABORTED = auto()

class Game(object):
    """ Simple container for calculating game stuff like players, teams, winners """
    def __init__(self, start_action):
        self.sid = get_datetime(start_action['timestamp'])
        self._log = [start_action]
        self.mc_version = start_action['version']
        self._stop_log = []
        self.stopped = False
        self.game_started = None
        self.game_info = {}
        self._teams = {}
        self._players = []
        self._deaths = []
        self._player_info = {}
        self.log = Logger('Game '+start_action['timestamp'])
        self._state = State.STARTED
        self.winning_team = None

    def __repr__(self):
        return "<Game {start}>".format(start=self.sid.isoformat())

    @property
    def state(self):
        """ Expose the game/server state, can only be set to Class State instance """
        return self._state

    @state.setter
    def state(self, state):
        if isinstance(state, State):
            self._state = state

    def game_start(self, action):
        """ The game is ON! """
        self._players = [player for player in self.get_playing_players()]
        self.game_started = len(self._log)
        self.game_info = action

    def add_action(self, action):
        """ Add an action to the log if active game, else save it for prosperity """
        if not self.stopped:
            #save the action to the general log
            self._log.append(action)
            #check if this did something to alter state
            self.check_action(action)
        else:
            self._stop_log.append(action)

    def check_action(self, action):
        """ Check if the action did something we should register """
        #get this class method from the action
        method = getattr(self, action['action'], None)
        if method is not None:
            #call the method with the action
            method(action)

    def death(self, action):
        """ Someone did something that should be counted as a score """
        #Not kill
        if len(action) < 5:
            self.log.debug("Player {p} died reason {r} "
                           .format(p=action['player'], r=action['reason']))
        else:
            #killed
            self.log.debug("Player {p} was killed by {p2} "
                           .format(p=action['player'], p2=action['killed_by']))
        self._deaths.append(action['player'])
        #Was this the winning move?
        self.check_for_winner()

    def player_mode(self, action):
        """ Handle a player mode change """
        self.log.debug("Player {p} mode changed: {m}"
                       .format(p=action['player'], m=action['mode']))
        if action['mode'] == 'Survival':
            if action['player'] not in self._players:
                self._players.append(action['player'])
        else:
            if action['player'] in self._players and not self.stopped:
                self._players.remove(action['player'])

    def player_join(self, action):
        """ Register player when someone joins """
        self.log.debug("Player {p} joined game {g}"
                       .format(p=action['player'], g=self))
        player = self._player_info.get(action['player'])
        if player is not None:
            player['uuid'] = action['uuid']
        else:
            self._player_info[action['player']] = {'uuid': action['uuid']}

    def player_ip(self, action):
        """ Sets a players ip address """
        self.log.debug("Player {p} have ip-address {ip}"
                       .format(p=action['player'], ip=action['ipaddress']))
        player = self._player_info.get(action['player'])
        player = {**player, **{'ipaddress': action['ipaddress']}}
        #unnessary assignment?
        self._player_info[action['player']] = player

    def team_members(self, action):
        """ Set team info on players """
        for player in action['players']:
            g_player = self._player_info.get(player)
            if g_player is not None:
                g_player['team'] = action['team']
            else:
                self._player_info[player] = {'team': action['team']}

            self.log.debug("Player {p} in team {team}"
                           .format(p=player, team=action['team']))

    def check_for_winner(self):
        """ Check the info if we only have one team left (and the winners!) """
        #just loop through all players and see if they belong to the same team
        t_players = [player for player in self.get_playing_players()]
        if len(t_players) < 3:
            #Not a valid game, can't decide on a winner.
            self.stopped = True
            self.state = State.ABORTED
            return
        team = None
        players = set(t_players) - set(self._deaths)
        for player in players:
            if team is not None:
                if team != self._player_info[player]['team']:
                    #We do not have a winner, more teams still alive
                    return
            else:
                team = self._player_info[player]['team']
        #If we get here, all remaining players are on the same team
        self.stopped = True
        self.state = State.STOPPED
        self.winning_team = team

    def get_playing_players(self):
        """ Return all players as a list that have joined the server and has a team set
        This can be used when player modes is not set in the beginning for some reason """
        for player, info in self._player_info.items():
            if info.get('uuid') is not None and info.get('team') is not None:
                yield player


class Store(object):
    """ Store class for storing games """
    def __init__(self):
        self._store = []

    @property
    def last(self):
        """ Expose the last item in store as Store.last """
        if len(self._store) > 0:
            return self._store[-1]
        else:
            return None

    @property
    def count(self):
        """ The number of games in the store """
        return len(self._store)

    def add(self, game):
        """ Add a game to the store """
        self._store.append(game)

    def items(self):
        """ Generator for returning the games in the store """
        for item in self._store:
            if item.state == State.STOPPED:
                yield item

GAME_STORE = Store()
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
    print("No. of games:", GAME_STORE.count)
    cnt = 0
    for game in GAME_STORE.items():
        #games has been parsed, actions, winners sets
        #TODO: time to count player scores and save game info
        print(game, game.winning_team, game.state)
        cnt = cnt + 1
    print("good games", cnt)

@click.command()
@click.option('--debug', is_flag=True, default=False, help='Turn on debugging')
@click.argument('file', type=click.Path(exists=True), required=True)
@click.option('--save', type=click.Path(exists=True), help='save to directory specified')
def start_parse(debug, file, save):
    """ main function for starting everything"""
    if debug:
        log_level = 'DEBUG'
    else:
        log_level = 'WARNING'

    StreamHandler(stdout, level=log_level).push_application()
    log = Logger('main')
    log.debug('Starting up...')

    parse(file)

    #print("Games:", games.count)
    #if save:
    #    log.debug('Saving data to json files')
    #    for key, server in servers.items():
    #        check = server.validate()
    #        filename = None
    #        if not check:
    #            filename = save+server.not_valid+"."+server.started.strftime("%Y-%m-%d_%H%M%S")
    #            filename = filename+".json"
    #        else:
    #            filename = save+server.started.strftime("%Y-%m-%d_%H%M%S")+".json"

    #        with open(filename, 'w') as file:
    #            file.write(jsonpickle.encode(server))
    #            log.debug("wrote game info to {file}".format(file=filename))

    log.debug('End of program...')


if __name__ == "__main__":
    #for kaka in Action.__subclasses__():
    #    print(kaka.regex)
    start_parse(None, None, None)
