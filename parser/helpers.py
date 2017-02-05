""" Simple helpers for the parser to use """
from datetime import datetime 

def get_datetime(line):
    return datetime.strptime(line[0:19], "%Y-%m-%d %X")
