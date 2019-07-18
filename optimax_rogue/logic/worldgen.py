"""This module generates the world, entities on the world, and items"""

from optimax_rogue.game.world import Tile, Dungeon, World
from optimax_rogue.game.state import GameState
from optimax_rogue.game.entities import Entity
import optimax_rogue.networking.serializer as ser
import numpy as np

class DungeonGenerator(ser.Serializable):
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

ser.register(EmptyDungeonGenerator)

class GameStartGenerator(ser.Serializable):
    """The interface for things that are capable of setting up the initial
    state of the game. Should assume player 1 gets entity 1 and player 2
    gets entity 2.
    """
    def setup_game(self) -> GameState:
        """Creates the initial game state. May involve randomness.

        Returns:
            state (GameState): the initial state of the game.
        """
        raise NotImplementedError

class TogetherGameStartGenerator(GameStartGenerator):
    """Starts the game with both mice on the first dungeon depth, randomly
    positioned.

    Attributes:
        dgen (DungeonGenerator): the generator for the first depth
    """
    def __init__(self, dgen: DungeonGenerator = EmptyDungeonGenerator(60, 10)):
        self.dgen = dgen

    def to_prims(self):
        return {'dgen': ser.serialize_embeddable(self.dgen)}

    @classmethod
    def from_prims(cls, prims) -> 'TogetherGameStartGenerator':
        return cls(ser.deserialize_embeddable(prims['dgen']))

    def setup_game(self) -> GameState:
        dung: Dungeon = self.dgen.spawn_dungeon(0)

        p1x, p1y = dung.get_random_unblocked()
        p2x, p2y = dung.get_random_unblocked()
        while (p2x, p2y) == (p1x, p1y):
            p2x, p2y = dung.get_random_unblocked()

        ent1 = Entity(1, 0, p1x, p1y, 10, 10, 2, 1, [], dict())
        ent2 = Entity(2, 0, p2x, p2y, 10, 10, 2, 1, [], dict())
        return GameState(True, 1, 1, 2, World({0: dung}), [ent1, ent2])

ser.register(TogetherGameStartGenerator)

class SeparatedGameStartGenerator(GameStartGenerator):
    """Spawns the two players on separate levels, each randomly positioned
    within the level.

    Attributes:
        dgen (DungeonGenerator): the dungeon generator
        p1_depth (int): the depth for player 1 to start at
        p2_depth (int): the depth for player 2 to start at
    """
    def __init__(self, dgen: DungeonGenerator = EmptyDungeonGenerator(60, 10),
                 p1_depth: int = 0, p2_depth: int = 1000):
        if p1_depth == p2_depth:
            raise ValueError('cannot use SeparatedGameStartGenerator for '
                             + f'p1_depth=p2_depth={p1_depth}')
        self.dgen = dgen
        self.p1_depth = p1_depth
        self.p2_depth = p2_depth

    def to_prims(self):
        return {
            'dgen': ser.serialize_embeddable(self.dgen),
            'p1_depth': self.p1_depth,
            'p2_depth': self.p2_depth
        }

    @classmethod
    def from_prims(cls, prims) -> 'SeparatedGameStartGenerator':
        return cls(
            ser.deserialize_embeddable(prims['dgen']),
            prims['p1_depth'],
            prims['p2_depth']
        )

    def setup_game(self) -> GameState:
        p1_dung: Dungeon = self.dgen.spawn_dungeon(self.p1_depth)
        p2_dung: Dungeon = self.dgen.spawn_dungeon(self.p2_depth)

        p1x, p1y = p1_dung.get_random_unblocked()
        p2x, p2y = p2_dung.get_random_unblocked()

        ent1 = Entity(1, self.p1_depth, p1x, p1y, 10, 10, 2, 1, [], dict())
        ent2 = Entity(2, self.p2_depth, p2x, p2y, 10, 10, 2, 1, [], dict())
        return GameState(True, 1, 1, 2,
                         World({self.p1_depth: p1_dung, self.p2_depth: p2_dung}),
                         [ent1, ent2])

ser.register(SeparatedGameStartGenerator)
