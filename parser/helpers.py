""" Simple helpers for the parser to use """
from datetime import datetime

def get_datetime(line):
    """ Convert a logline to a datetime for the log entry """
    return datetime.strptime(line, "%Y-%m-%d %X")
