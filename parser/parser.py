"""Parser module for uhc parser, this is where the magic happens?"""
from datetime import timedelta
from logbook import Logger
from .models import Server
from .helpers import get_datetime

#conf the log
log = Logger('parser')

def parse(logfile):
    """Main parser function to start everything"""
    current_server = None
    server_store = {}
    log.debug("Opening logfile: {file} for parsing".format(file=str(logfile)))
    with open(logfile, 'r') as file:
        for line in file:
            #check each line if it is starting
            if "Starting minecraft server version" in line[27:]:
                if current_server:
                    #Combine the old and the new game if it crashed
                    if current_server.state == 'CRASH':
                        timespan = current_server.stopped - get_datetime(line)
                        if timespan < timedelta(minutes=10):
                            current_server.add_line(line)
                            continue

                    if not current_server.stopped:
                        current_server.stop(line, "UNCLEAN_SHUTDOWN")
                        log.debug("Server instance {game} had problems, marked it"
                                  .format(game=str(current_server)))

                current_server = Server(line)
                server_store[current_server.sid] = current_server
            #or stopping
            elif "Stopping the server" in line[27:]:
                current_server.stop(line)
            #if not, it belongs to a server instance
            elif "Successfully found the block at" in line[27:]:
                #ignore this line.
                continue
            elif "This crash report has been saved to:" in line[28:]:
                #ignore this line.
                current_server.stop(line, "CRASH")
            else:
                current_server.add_line(line)
        #stop the last game
        current_server.stop(line)
        log.debug("Done parsing: {file} for server creations".format(file=str(logfile)))

    log.debug("Closed logfile: {file}".format(file=str(logfile)))
    return server_store
