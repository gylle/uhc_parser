""" The models used for UHC parsing """
import re
from datetime import timedelta
from uuid import uuid4

from logbook import Logger

from .helpers import get_datetime

#TODO: restructure this to use subclassing and register with a parser class for all actions
class Server(object):
    """Represents the server and the time it's running. This is the main container for everything
    game related."""
    log = Logger('Server')
    regex = [('new_player', re.compile(r'UUID of player (?P<player>.*) is (?P<uuid>.*)')),
             ('set_player_ip', re.compile(r'\[INFO\] (?P<player>.*)\[/(?P<ip>.*):\d+\] logged in')),
             ('set_team_color',
              re.compile(r'\[INFO\] Set option color for team (?P<team>\w+) to (?P<color>\w+)')),
             ('set_player_team',
              re.compile(r'\[INFO\] Added \d player\(s\) to team (?P<team>\w+): (?P<members>.*)')),
             ('killing', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} was slain by (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1}')),
             ('killing', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} was shot by (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1}')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} blew up')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} was blown up by')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} suffocated in a wall')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} fell from a high place')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} burned to death')),
             ('accident',
              re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} was burnt to a crisp whilst fighting')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} drowned')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} tried to swim in lava')),
             ('accident', re.compile(r'\[INFO\] (?:§{0,1}\?{0,1}[0-9a-z]){0,1}(\w+)(?:§{0,1}\?{0,1}[0-9a-z]){0,1} hit the ground too hard')),
             ('new_game', re.compile(r'\[INFO\] Shrinking world border to (\d+.\d) blocks wide \(down from (\d+.\d) blocks\) over (\d+) seconds')),
            ]

    def _action(self, action, data):
        if action == 'new_player':
            player = self.players.get(data[0])
            if not player:
                self.players[data[0]] = Player(data[0], data[1])
                self.log.debug("Player {name} joined server {server}"
                               .format(name=data[0], server=str(self)))
            else:
                self.log.info("Player {name} already joined server {server}"
                              .format(name=player.nickname, server=str(self)))
        elif action == 'set_player_ip':
            #set the players ip in the store.
            self.players[data[0]].set_ip(data[1])
        elif action == 'set_team_color':
            team = self.teams.get(data[0])
            if not team:
                team = Team(data[0])
                team.set_color(data[1])
                self.teams[data[0]] = team
            else:
                team.set_color(data[1])
        elif action == 'set_player_team':
            for nick in data[1].split():
                nick = nick.strip(',')
                if nick == 'and':
                    continue
                self.delete_player_from_teams(nick)
                team = self.teams.get(data[0])
                if not team:
                    team = Team(data[0])
                    team.add_player(nick)
                    self.teams[data[0]] = team
                else:
                    team.add_player(nick)
        elif action == 'killing':
            if len(self.games) == 0:
                #no game started yet?
                self.log.info("On {server} {player} died by {killer} before a game had started!"
                              .format(server=str(self), player=data[0], killer=data[1]))
                return False
            self.games[-1].death(data[0], data[1])
            #do we have a winner?
            self.check_for_winners()
        elif action == 'accident':
            if len(self.games) == 0:
                self.log.info("On {server} {player} died before a game had started!"
                              .format(server=str(self), player=data[0]))
                return False
            self.games[-1].death(data[0])
            #do we have a winner?
            self.check_for_winners()
        elif action == 'new_game':
            #Looks like we started a new game on the server
            game = Game()
            game.set_properties(data)
            #get all teams
            for team in self.teams.items():
                #and the players in each team
                for nick in team[1].players:
                    #make sure they have joined the server
                    playah = self.players.get(nick)
                    if not playah:
                        #if not, go to next player
                        continue
                    #Add them to the game, these people are fighting!
                    game.add_player(nick)
            self.games.append(game)
        else:
            self.log.warn("Got regex match but have no action to take!")
        return True

    def delete_player_from_teams(self, player):
        """check if players are in another team, then delete them from that team"""
        for item in self.teams.items():
            if player in item[1].players:
                item[1].delete_player(player)
                self.log.debug('On {s}: removed {p} from {t}'
                               .format(s=str(self), p=player, t=item[0]))

    def __init__(self, line):
        self.sid = line[0:19]
        self.lines = []
        #game state
        self.started = None
        self.stopped = None
        self.state = None
        self.verified = None
        self.winning_team = False
        self.not_valid = None
        #actual game info
        self.games = []
        self.teams = {}
        self.players = {}
        #init stuff
        self.start(line)
        self.lines.append(line)
        self.log.debug("Server {server} created".format(server=str(self)))

    def __repr__(self):
        return '<Server {id}>'.format(id=self.sid)

    def add_line(self, line):
        """ Add and parse all log lines belonging to this server instance """
        if self.winning_team:
            return False
        self.lines.append(line)
        for item in self.regex:
            match = item[1].search(line)
            if match:
                self.log.debug("Matched {type} for {self}".format(type=item[0], self=str(self)))
                #We got a match for some actionable information
                self._action(item[0], match.groups())
                return True
        return False
    def check_for_winners(self):
        """Do we have our winners? Check True, if we have false if not."""
        if self.winning_team:
            return False

        if len(self.games) < 1:
            return False

        players_left = len(self.games[-1].players)
        if players_left > 2:
            return False
        elif players_left == 2:
            for team in self.teams.items():
                if set(team[1].players) == set(self.games[-1].players):
                    self.winning_team = team[1]
                    return True
            return False
        elif players_left == 1:
            for team in self.teams.items():
                if self.games[-1].players[0] in team[1].players:
                    self.winning_team = team[1]
                    return True
            self.log.error("IMPOSSIBLE! One player left but not in a team?!")
        return False

    def start(self, line):
        """ Call this when the server starts """
        self.lines.append(line)
        self.started = get_datetime(line)

    def stop(self, line, state="OK"):
        """ Call this when the server has stopped"""
        self.lines.append(line)
        self.stopped = get_datetime(line)
        self.state = state
        self.log.debug("stopped server {server} at time {stop}"
                       .format(server=str(self), stop=str(self.stopped)))

    def validate(self):
        """ Run this after everything is added, it will try to verify
         everything and see if the server/game was a complete set.
         Sets the verified flag to true if everything is OK
        """
        if len(self.games) < 1:
            self.not_valid = "no_games"
            return False

        if len(self.players) < 2:
            self.not_valid = "not_enough_players"
            return False

        #Check if it was long enough.
        timespan = self.stopped - self.started
        if timespan < timedelta(minutes=30):
            self.not_valid = "timespan"
            return False

        if len(self.teams) < 2:
            self.not_valid = "not_enough_teams"
            return False

        #do we have a winner?
        if not self.winning_team:
            self.not_valid = "no_winner"
            print(self)
            return False
        self.not_valid = False
        return True

class Game(object):
    """Contains everything related to a specific game started on the server"""
    log = Logger('Game')
    def __init__(self):
        self.uuid = str(uuid4())
        self.players = []
        self.killed = {}
        self.properties = {}

        self.log.debug("Created new game {game}".format(game=str(self)))

    def __repr__(self):
        return '<Game {id}>'.format(id=self.uuid)

    def add_player(self, player):
        """Add a player to the game"""
        self.players.append(player)
        self.log.debug("Added player {nick} to game {game}".format(nick=player, game=str(self)))

    def death(self, player, killer=None):
        """ Mark player as killed by killer"""
        #Ignore if someone died and not in players
        if player not in self.players:
            return False

        self.killed[player] = killer
        self.players.remove(player)
        self.log.debug("Removed player {nick} from game {game}".format(nick=player, game=str(self)))
        return True

    def set_properties(self, data):
        """Set the game properties for blocks and it shrinking"""
        self.properties['end_blocks'] = data[0]
        self.properties['start_blocks'] = data[1]
        self.properties['block_time'] = data[2]
        self.log.debug("Set the properties for game {game}".format(game=str(self)))

    def players_left(self):
        """Check if there are two players left"""
        return self.players


class Player(object):
    """Represents a player and what we know of it, belongs to the server"""
    log = Logger('Player')
    def __init__(self, nickname, uuid=None):
        self.nickname = nickname
        self.uuid = uuid
        self.ip_adress = None
        self.log.debug('Created new player with nick {name}'.format(name=self.nickname))

    def __repr__(self):
        return '<Player {nick}>'.format(nick=self.nickname)

    def set_ip(self, ip_adress):
        """Sets the players ip adress"""
        self.ip_adress = ip_adress
        self.log.debug('Set ip {ip} to player {name}'.format(ip=self.ip_adress, name=self.nickname))

class Team(object):
    """Represents a team on the server"""
    log = Logger('Team')
    def __init__(self, name):
        self.team_name = name
        self.players = []
        self._color = None
        self.log.debug('Created new team {team}'.format(team=name))

    def __repr__(self):
        return '<Team {name}>'.format(name=self.team_name)

    def set_color(self, color):
        """ sets the teams color """
        self._color = color
        self.log.debug('Set team {team} color to {color}'
                       .format(team=self.team_name, color=self._color))

    def add_player(self, nick):
        """ Adds a player to the team"""
        if not nick in self.players:
            self.players.append(nick)
            self.log.debug('Added player {nick} to team {team}'
                           .format(nick=nick, team=self.team_name))
            return True
        return False

    def player_in_team(self, nick):
        """Check if the player is in the team"""
        if nick in self.players:
            return True
        return False

    def delete_player(self, nick):
        """Delete a player from the team"""
        if nick in self.players:
            self.players.remove(nick)
            self.log.debug('Removed player {nick} from team {team}'
                           .format(nick=nick, team=self.team_name))
            return True
        return False
