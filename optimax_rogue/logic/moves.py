"""This module defines resolves all the possible actions / moves that agents
can make"""

import enum

class Move(enum.IntEnum):
    """Describes a particular action that an entity can take"""
    Up = 1
    Right = 2
    Down = 3
    Left = 4
    Stay = 5
