#!/bin/env - python
""" Main file for uhc parser, run this from the commandline """
#Copyright 2017 Tobias Gustavsson <tobias at rackrymd.se>
#License - See LICENSE file
from sys import stdout
import json
import jsonpickle
import click
from logbook import Logger, StreamHandler
from parser import parse, score_count

#TODO: Games restarts where team is not set and player modes changes is not counted
#Example: 2015-05-19 21:28:01

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

    games = parse(file)

    log.info("Games:", games.count)
    if save:
        log.debug('Saving data to json files')
        l_game = []
        for game in games.items():
            name = game.sid.strftime("%Y-%m-%d_%H%M%S")
            l_game.append(name)
            filename = save+name+".json"
            with open(filename, 'w') as file:
                file.write(jsonpickle.encode(game))
                log.debug("wrote game info to {file}".format(file=filename))
            filename = save+'hs2017.json'
        highscore = score_count(games)
        data = {'games': l_game, 'highscore': highscore}
        with open(filename, 'w') as file:
            log.debug("wrote highscore info to {file}".format(file=filename))
            file.write(json.dumps(data))

    log.debug('End of program...')


if __name__ == "__main__":
    #for kaka in Action.__subclasses__():
    #    print(kaka.regex)
    start_parse(None, None, None)
