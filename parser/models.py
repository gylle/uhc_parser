""" All the class models for the objects we need to represent the games """
from enum import Enum, auto
from logbook import Logger
from . helpers import get_datetime

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
