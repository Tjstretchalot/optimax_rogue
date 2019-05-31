"""This module generates the world, entities on the world, and items"""

from optimax_rogue.game.world import Tile, Dungeon
import numpy as np

class DungeonGenerator:
    """The interface for things that spawn dungeons

    Attributes:
        width (int): the width of the dungeons
        height (int): the height of the dungeons
    """
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def spawn_dungeon(self, depth: int) -> Dungeon:
        """Creates a dungeon at the specified depth

        Args:
            depth (int): the depth of the dungeon to spawn
        """
        raise NotImplementedError

class EmptyDungeonGenerator(DungeonGenerator):
    """A simple dungeon generator that just spawns empty dungeons surrounded
    by walls with the staircase randomly located
    """

    def spawn_dungeon(self, depth: int) -> Dungeon:
        tiles = np.zeros((self.width, self.height), 'int32')
        tiles[:, :] = Tile.Ground.value
        tiles[[0, -1], :] = Tile.Wall.value
        tiles[:, [0, -1]] = Tile.Wall.value

        rx = np.random.randint(1, self.width - 2)
        ry = np.random.randint(1, self.height - 2)

        tiles[rx, ry] = Tile.StaircaseDown
        return Dungeon(tiles)
