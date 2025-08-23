from enum import Enum

# Contains useful definitions for interfacing with the NTL Axon board.

# Packet type enum
class PcktType(Enum):
    DATA = 0
    INIT = 1
    PADDING = 2
    DEBUG = 3
    INFO = 4
    WARNING = 5
    ERR = 6
    FATAL = 7