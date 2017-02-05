#!/bin/env - python
#Copyright 2017 Tobias Gustavsson <tobias at rackrymd.se>
#License - See LICENSE file
from sys import stdout
import jsonpickle

import click
from logbook import Logger, StreamHandler

from parser import parse
from counter import count_highscore

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
    #parsing file
    servers = parse(file)
    #count
    highscore_table = count_highscore(servers)

    if save:
        log.debug('Saving data to json files')
        for key, server in servers.items():
            check = server.validate()
            filename = None
            if not check:
                filename = save+server.not_valid+"."+server.started.strftime("%Y-%m-%d_%H%M%S")
                filename = filename+".json"
            else:
                filename = save+server.started.strftime("%Y-%m-%d_%H%M%S")+".json"

            with open(filename, 'w') as file:
                file.write(jsonpickle.encode(server))
                log.debug("wrote game info to {file}".format(file=filename))

    log.debug('End of program...')
if __name__ == "__main__":
    start_parse(None, None, None)
