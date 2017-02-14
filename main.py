#!/bin/env - python
#Copyright 2017 Tobias Gustavsson <tobias at rackrymd.se>
#License - See LICENSE file
from sys import stdout
import jsonpickle
import re
import operator
from enum import Enum
import click
from logbook import Logger, StreamHandler
from datetime import datetime, timedelta

def get_datetime(line):
    return datetime.strptime(line[0:19], "%Y-%m-%d %X")

#from parser import parse, count_highscore

class UHCParser(object):
    """The little class that only parse the files, splitting it up into different server chunks"""
    log = Logger('UHCParser')
    def __init__(self, filename):
        self.servers = ServerStore()
        self._file = filename

    def run(self):
        """ Run the actual parsing of the server log file"""
        with open(self._file, 'r') as file:
            for line in file:
            #check each line if it is starting
                if "Starting minecraft server version" in line[27:]:
                    #check if the previous server have been stopped
                    if self.servers.count > 0:
                        if self.servers.last.stop_time is None:
                            self.log.debug("Forced stopp of {server}"
                                           .format(server=self.servers.last))
                            self.servers.last.stop()
                    self.log.debug("New server found at {date}".format(date=line[0:16]))
                    self.servers.add(Server(line))
                #or stopping
                elif "Stopping server" in line[27:]:
                    self.log.debug("Server stopping")
                    self.servers.last.stop(line)
                #ignore
                elif "Successfully found the block at" in line[27:]:
                    continue
                #handle it
                elif "This crash report has been saved to:" in line[28:]:
                    self.log.debug("Server crash!")
                    #read the next 20 or so lines so we don't start a new server.
                    for i in range(20):
                        event = file.readline()
                        self.servers.last.add_event(event)
                #handle normal events
                else:
                    self.servers.last.add_event(line)
            self.servers.last.stop()
        return self.servers

class Game(object):
    """Represent a game played. It should have big list of actions that happened in the Game
    """
    # list of tuples containing regex and corresponding method to call if match
    # [(regex, method), ...]
    GACTIONS = [
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' was slain by '
                    r'(?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' was shot by '
                    r'(?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' blew up'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' was blown up by '
                    r'(?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' suffocated in a wall'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' fell from a high place'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' burned to death'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' was burnt to a crisp whilst fighting '
                    r'(?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' drowned'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' tried to swim in lava'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' tried to swim in lava to escape '
                    r'(?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'), 'death'),
        (re.compile(r'\[INFO\] (?:§[0-9a-z]){0,1}(\w+)(?:§r){0,1}'
                    r' hit the ground too hard'), 'death'),
        (re.compile(r'\[INFO\] Shrinking world border to (\d+.\d) blocks wide '
                    r'\(down from (\d+.\d) blocks\) over (\d+) seconds'), 'game_start'),
        (re.compile(r"(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] \[\w+: Set (\w+)'s"
                    r" game mode to (\w+) Mode\]"), 'player_mode'),
        (re.compile(r'(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] \[(\w+): Set own '
                    r'game mode to (\w+) Mode\]'), 'player_mode'),
        (re.compile(r"(\d+-\d+-\d+ \d+:\d+:\d+) \[INFO\] Set (\w+)'s "
                    r"game mode to (\w+) Mode"), 'player_mode'),]
    def __init__(self, server):
        self._actions = server._actions
        self.server = server
        self._players = server.get_players()
        self._game_start = 0
        self.game_stopped = False
        self.log = Logger('Game')
        self.team_size = 0
        self.winning_team = None

    def run(self):
        """ Parse the game data for actions that are important to the game (scoring etc) """
        for event in self.server.get_events():
            if not self.game_stopped:
                for action in self.GACTIONS:
                    #try all registered actions
                    match = action[0].search(event)
                    if match:
                        #if it is a match, call the method defined
                        getattr(self, action[1])(match.groups())

    def count(self):
        """ Count the number of actions"""
        return len(self._actions)

    def player_mode(self, data):
        """ Call when a player gets the survival mode setting on him (start and revivals) """
        action = {'action':'player_mode',
                  'time': data[0],
                  'player': data[1],
                  'player_mode': data[2]}

        self._actions.append(action)

    def death(self, data):
        """ Someone died and probably killed by some(one/thing)"""
        if len(data) > 1:
            action = {'action': 'kill',
                      'died': data[0],
                      'by':data[1],
                      'player': self.is_player(data[1])}
        else:
            action = {'action': 'death', 'died': data[0]}
        self._actions.append(action)

    def game_start(self, data):
        """ Game start, might happen a couple of times """
        action = {'action': 'game_start', 'blocks': data[0], 'start': data[1], 'time': data[2]}
        self._actions.append(action)
        self._game_start = len(self._actions) - 1

    def is_player(self, name):
        """ Returns true if the name is a player in the game, else false"""
        for player in self._players:
            if name == player:
                return True
        return False

    def validate(self):
        """ Validate that the game was complete and had a winner """
        if not self.check_for_winner():
            self.log.debug("Couldn't find a winner for the game")
            return False
        if self._game_start == 0:
            self.log.debug("Didn't find that the game started this round...")
            return False
        if self.team_size == 0:
            self.log.debug("The teams wasn't big enough for playing")
            return False
        if self.winning_team is None:
            self.log.debug("Couldn't determine winner for {srv}".format(srv=self.server))
            return False

        return True

    def check_for_winner(self):
        """ Determine if we have winner yet"""
        alive = []
        dead = []
        if len(self._players) > 0:
            counts = {}
            for player in self._players.items():
                counts[player[1]['team']] = counts.get(player[1]['team'], 0) + 1
                #append the nick of all players playing
                alive.append(player[0])
            #get the largest team size of active players so we know how many winners we can have
            self.team_size = max(counts.items(), key=operator.itemgetter(1))[1]
        else:
            self.team_size = 0
        #print(alive)
        for index, action in enumerate(self._actions[self._game_start:]):
            #print(action)
            typ = action.get('action')
            if typ == 'kill':
                dead.append(action['died'])
            elif typ == 'death':
                dead.append(action['died'])
            elif typ == 'player_mode':
                if action['player_mode'] == 'Survival':
                    if action['player'] in dead:
                        dead.remove(action['player'])

            size = len(alive) - len(dead)
            if size <= self.team_size:
                #we can have a winner if all players is on the same team
                tmp_players = set(alive) - set(dead)
                def check_team(tmp_players, players):
                    """ Why would a local def need a doc string?"""
                    team = None
                    for player in tmp_players:
                        if team is None:
                            team = players[player]['team']
                        elif team != players[player]['team']:
                            return False
                    return team
                team = check_team(tmp_players, self._players)
                if team is not False:
                    self.winning_team = team
                    self._actions = self._actions[:index+self._game_start]
                    self._actions.append({'action':'win',
                                          'team': team,
                                          'alive': [play for play in tmp_players],
                                          'details': self.server.get_team(team)})
                    print("TEAM WON!!!", team)
                    return True

            #print("died:", dead)
        return False

class Store(object):
    """ Base class for storage of items for the UHCParser"""
    def __init__(self):
        self._store = []

    def add(self, data):
        """ Add something to the store"""
        self._store.append(data)

    @property
    def last(self):
        """ Accessing the last added entity in the store"""
        return self._store[-1]

    @property
    def count(self):
        """Has the number of items in the store"""
        return len(self._store)

    def items(self):
        """ Returns all items in store as a generator"""
        for item in self._store:
            yield item

class ServerStore(Store):
    """ServerStore, subclasses Store and specialize for Server class stuff """
    log = Logger('ServerStore')
    def items(self):
        for server in self._store:
            if server.validate():
                yield server

    def add(self, server):
        """Overrides the Store class add
        Checks if the previous server quit before it was time and add the events together
        Discards the new server created by not storing it :)
        """
        if self.count == 0:
            return super(ServerStore, self).add(server)

        span = self._store[-1].stop_time - self._store[-1].start_time
        if span < timedelta(minutes=30):
            self.log.debug("Merged two servers: {server1} + {server2}"
                           .format(server2=server, server1=self._store[-1]))
            for event in server.get_events():
                self._store[-1].add_event(event)
            self._store[-1].restart()
        else:
            return super(ServerStore, self).add(server)

def sort_members(data):
    """ Simple function to return players in team formatted correctly"""
    members = []
    for nick in data[1].split():
        nick = nick.strip(',')
        if nick == 'and':
            continue
        members.append(nick)
    return {'action': 'team', 'team': data[0], data[0]: {'members': members}}

#Big list of regexes and the function we want to apply to it for formatting the data back
ACTIONS = [(re.compile(r'UUID of player (?P<player>.*) is (?P<uuid>.*)'),
            lambda data: {'action':'player', 'nick':data[0], data[0]: {'uuid': data[1]}}),
           (re.compile(r'\[INFO\] (?P<player>.*)\[/(?P<ip>.*):\d+\] logged in'),
            lambda data: {'action':'player', 'nick':data[0], data[0]: {'ipaddress': data[1]}}),
           (re.compile(r'\[INFO\] Set option color for team (?P<team>\w+) to (?P<color>\w+)'),
            lambda data: {'action':'team', 'team': data[0], data[0]: {'color': data[1]}}),
           (re.compile(r'\[INFO\] Added \d player\(s\) to team (?P<team>\w+): (?P<members>.*)'),
            sort_members),
           (re.compile(r'\[INFO\] Could not add \d player\(s\) '
                       r'to team (?P<team>\w+): (?P<members>.*)'),
            sort_members),]
class Server(object):
    """Represents the lifespan of a UHC Server, altough multiple restarts can be in the same server
    if they are deemed to belong to each other for game restarts and stuff"""
    def __init__(self, line):
        self._events = [line]
        self._actions = []
        self.sid = line[0:16]
        self.log = Logger('Server {date}'.format(date=self.sid))
        self.start_time = get_datetime(line)
        self.stop_time = None
        self._players = {}
        self._teams = {}

    def __repr__(self):
        return "<Server {server}>".format(server=self.sid)

    def add_event(self, event):
        """Add an event to a server to be parsed for actions"""
        self._events.append(event)
        for item in ACTIONS:
            match = item[0].search(event)
            if match:
                action = item[1](match.groups())
                self._actions.append(action)
                # check what kind of action it is
                if action['action'] == 'player':
                    #player, get player from the store
                    player = self._players.get(action['nick'])
                    if player is not None:
                        #if it exits, combine the two dicts
                        player = {**player, **action[action['nick']]}
                    else:
                        #else overwrite player info
                        player = action[action['nick']]
                    self._players[action['nick']] = player
                elif action['action'] == 'team':
                    # first off, check if it's going to set team members
                    members = action[action['team']].get('members')
                    if members is not None:
                        #check if player already in another team
                        #then delete that player from that team. UGH...
                        for team in self._teams.items():
                            reg_memb = team[1].get('members')
                            if reg_memb is not None:
                                for player in members:
                                    if player in reg_memb:
                                        reg_memb.remove(player)
                                        self.log.debug("Deleting player {p} from {t}"
                                                       .format(p=player, t=team[0]))
                    #get the team from the store
                    team = self._teams.get(action['team'])
                    if team is not None:
                        #exists, combine
                        team = {**team, **action[action['team']]}
                    else:
                        team = action[action['team']]
                    self.log.debug("Added {p} to team {t}"
                                   .format(p=action[action['team']], t=action['team']))
                    self._teams[action['team']] = team

    def get_players(self):
        """Return the players that are partaking in the actual game
        Should remove fake team members and people only observing"""
        #This should return {'nickname':{'uuid': uuid, 'team': team}}
        players = {}
        for player in self._players.items():
            team = player[1].get('team')
            uuid = player[1].get('uuid')
            #a player needs to have both team and uuid (joined server)
            #for it to count
            if team is not None and uuid is not None:
                players[player[0]] = player[1]
            else:
                #todo: understand why they dont get have a team..
                self.log.debug("{p} was missing either uuid/team: {u}/{t}"
                               .format(p=player[0], u=uuid, t=team))

        return players
    def get_team(self, team):
        """ Return the team wanted """
        return self._teams.get(team)

    def stop(self, event=None):
        """ Stop the server, sets date and stuff"""
        self.log.debug("{server} stopping...".format(server=self))
        if not event:
            event = self._events[-1]
        self.stop_time = get_datetime(event)
        self.add_event(event)
        #Add team to player
        for player in self._players.items():
            for name, team in self._teams.items():
                members = team.get('members')
                if members is not None:
                    if player[0] in members:
                        player[1]['team'] = name

        #print("players ", self._players)
        #print("teams ", self._teams)

    def restart(self):
        """ A server that has been restarted should be fixed"""
        self.stop_time = None
        self.log.debug("{server} restarted".format(server=self))

    def get_events(self):
        """ A generator that will loop through all events and return them"""
        for event in self._events:
            yield event

    def validate(self):
        """Is this a valid game/server"""
        if self.stop_time is None:
            self.log.warn("{server} has no stop time.".format(server=self))
            return False

        span = self.stop_time - self.start_time
        if span < timedelta(minutes=30):
            self.log.debug("{server} only ran for {minutes}."
                           .format(server=self, minutes=str(span)))
            return False

        #not enough teams to compete...
        if len(self._teams) < 2:
            return False
        return True

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

    parser = UHCParser(file)
    servers = parser.run()
    games = Store()
    for server in servers.items():
        game = Game(server)
        game.run()
        #Sometimes people play with the server without there being a game
        #remove those, we only want real games.
        if game.validate():
            games.add(game)
        print(game.server.sid, game.count())

    print("Games:", games.count)
    #parsing file 1.0
    #servers = parse(file)
    #count
    #highscore_table = count_highscore(servers)
    #print(jsonpickle.encode(highscore_table))
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
