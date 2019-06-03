"""Describes packets that can be sent between the server and the client.
Most of the core logic from the server to the client is handled in
logic.updates. This completes those for handshaking behaviors"""
import enum
import typing
import optimax_rogue.networking.serializer as ser
from optimax_rogue.logic.moves import Move
from optimax_rogue.game.state import GameState
from optimax_rogue.logic.updates import GameStateUpdate
from optimax_rogue.logic.updater import UpdateResult

class ClientType(enum.IntEnum):
    """The type of clients that can be connected to the server
    """
    Player = 1
    Spectator = 2

PACKET_TYPES = set()
def register_packet(typ):
    """Registers the specified packet for serialization/deserialization"""
    ser.register(typ)
    PACKET_TYPES.add(typ.identifier())

class Packet(ser.Serializable):
    """Describes a basic packet
    """
    pass

class SyncPacket(Packet):
    """Describes a full game state sync packet, which is required at the
    start of the game

    Attributes:
        game_state (GameState): the state of the game
        player_iden (optional, int): either the id for the player (if the client is Player) or None
    """

    def __init__(self, game_state: GameState, player_iden: typing.Optional[int]) -> None:
        if not isinstance(game_state, GameState):
            raise ValueError(f'expected game_state is GameState, '
                             + f'got {game_state} (type={type(game_state)})')
        if player_iden is not None and not isinstance(player_iden, int):
            raise ValueError(f'expected player_iden is Optional[int], '
                             + f'got {player_iden} (type={type(player_iden)})')

        self.game_state = game_state
        self.player_iden = player_iden

    def to_prims(self):
        return {
            'game_state': ser.serialize_embeddable(self.game_state),
            'player_iden': self.player_iden
        }

    @classmethod
    def from_prims(cls, prims) -> 'SyncPacket':
        if ser.peek_type_embeddable(prims['game_state']) != GameState:
            raise ValueError('game_state bad type')

        return cls(
            ser.deserialize_embeddable(prims['game_state']),
            prims['player_iden']
        )

register_packet(SyncPacket)

class MovePacket(Packet):
    """This packet is sent from players to the server to indicate that they
    have decided on a move for this turn

    Attributes:
        entity_iden (int): the entity they are controlling
        move (Move): the move they are making
    """
    def __init__(self, entity_iden: int, move: Move):
        if not isinstance(entity_iden, int):
            raise ValueError(f'expected entity_iden is int, got {entity_iden} '
                             + f'(type={type(entity_iden)})')
        if not isinstance(move, Move):
            raise ValueError(f'expected move is Move, got {move} (type={type(move)})')
        self.entity_iden = entity_iden
        self.move = move

    def to_prims(self):
        return {'entity_iden': self.entity_iden, 'move': int(self.move)}

    @classmethod
    def from_prims(cls, prims) -> 'MovePacket':
        return cls(prims['entity_iden'], Move(prims['move']))

register_packet(MovePacket)

class UpdatePacket(Packet):
    """Describes a packet associated with a game state update

    Attributes:
        update (GameStateUpdate): the update
    """
    def __init__(self, update: GameStateUpdate) -> None:
        if not isinstance(update, GameStateUpdate):
            raise ValueError(f'expected update is GameStateUpdate, got {update} (type={type(update)})')

        self.update = update

    def to_prims(self):
        return {'update': ser.serialize_embeddable(self.update)}

    @classmethod
    def from_prims(cls, prims) -> 'UpdatePacket':
        return cls(ser.deserialize_embeddable(prims['update']))

register_packet(UpdatePacket)

class TickStartPacket(Packet):
    """Describes a packet associated with a tick starting"""
    pass

register_packet(TickStartPacket)

class TickEndPacket(Packet):
    """Describes a packet associated with the tick ending (now opening it
    up to player moves)

    Attributes:
        result (UpdateResult): the result of the tick
    """
    def __init__(self, result: UpdateResult):
        if not isinstance(result, UpdateResult):
            raise ValueError(f'expected result is UpdateResult, got {result} (type={type(result)})')
        self.result = result

    def to_prims(self):
        return {'result': int(self.result)}

    @classmethod
    def from_prims(cls, prims) -> 'TickEndPacket':
        return cls(UpdateResult(prims['result']))

register_packet(TickEndPacket)
