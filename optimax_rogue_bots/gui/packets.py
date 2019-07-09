"""Additional packets sent between the GUI and the bot. If you want to add a completely
custom GUI you will almost certainly want to do something like this as well."""

import optimax_rogue.networking.packets as packets
import optimax_rogue.logic.moves as moves
import enum
import typing

class SetBotPitchPacket(packets.Packet):
    """When the bot connects to the GUI it's nice to know a little bit about which bot is making
    suggestions and how it works. Since the protocol is otherwise agnostic to the implementation,
    this is the bots chance to give its "pitch"

    Attributes:
        name (str): A short name for the bot
        desc (str): The description for the bot
    """
    def __init__(self, name: str, desc: str) -> None:
        self.name = name
        self.desc = desc

packets.register_packet(SetBotPitchPacket)

class HighlightStyle(enum.IntEnum):
    """Describes the way that the bot presents its suggestions / intuition / calculations
    to the user through the interface.

    Values:
        StateAction: The bot is capable of encoding values for state-action tuples. The value for
            the state action is assumed to be proportional to the cumulative discounted reward
            for first performing the specified action in the specified state and then following
            the current policy until the end of the game.
        Action: The bot is capable of encoding values for states. It is assumed that the value
            of a particular state is proportional to the cumulative discounted reward for following
            the current policy at the given state until the end of the game.
    """

    StateAction = 1
    State = 2

class SetHighlightStylePacket(packets.Packet):
    """This packet configures the highlighting style that the GUI requests from the
    bot. See HighlightStyles for details. This packet is sent from the bot to the GUI.

    Attributes:
        style (HighlightStyle): the highlight style for the GUI
    """
    def __init__(self, style: HighlightStyle) -> None:
        self.style = style

    def to_prims(self) -> dict:
        return {'style': int(self.style)}

    @classmethod
    def from_prims(cls, prims) -> 'SetHighlightStylePacket':
        return cls(HighlightStyle(prims['style']))

packets.register_packet(SetHighlightStylePacket)

class ScaleStyle(enum.IntEnum):
    """The potential ways that the values from the state actions can be scaled.

    Attributes:
        Clip: assume that the values are largely correct for the -1 to 1 scale, and
            simple clip values outside of this range to that range (i.e., -1.5 goes to -1).

        SoftArgMax: Smoothly approximate the maximum argument for the functions, where the
            maximum values index tends to 1 and all other values tend toward 0. In order to go from
            -1 to 1, after the normal soft arg max with base e, the values are then linearly
            rescaled to be from -1 to 1

        TemperatureSoftArgMax: Similar to SoftArgMax except with an added "temperature" parameter.
            This function is often used in reinforcement learning to convert expected cumulative
            discounted rewards into action probabilities. Temperature is always positive.
            This is equivalent to SoftArgMax when temperature is 1. As temperature increases,
            this tends towards the constant uniform function with value 1/(number of actions).
            As this value tends towards 0, this approaches a hard arg max. Just as in the
            SoftArgMax case, values are linearly rescaled from -1 to 1 after the normal soft arg
            max function.
    """
    Clip = 1
    SoftArgMax = 2
    TemperatureSoftArgMax = 3

class SetScaleStylePacket(packets.Packet):
    """This packet configures the scale of the results from the state action values or
    action values. Set ScaleStyle for details. This is sent from the bot to the GUI

    Attributes:
        style (ScaleStyle): the scale style for the GUI
        parameter (float, optional): the parameter associated with this style, if this
            style has a paramter
    """
    def __init__(self, style: ScaleStyle, parameter: float = None) -> None:
        self.style = style
        self.parameter = parameter

    def to_prims(self) -> dict:
        return {'style': int(self.style), 'parameter': self.parameter}

    @classmethod
    def from_prims(cls, prims) -> 'SetScaleStylePacket':
        return cls(ScaleStyle(prims['style']), prims['parameter'])

packets.register_packet(SetScaleStylePacket)

class SetSupportedMovesPacket(packets.Packet):
    """This packet configures the list of moves that the bot is capable of encoding.
    This is sent from the bot to the GUI.

    Attributes:
        sup_moves (list[Move]): the moves that the bot can handle
    """
    def __init__(self, sup_moves: typing.List[moves.Move]) -> None:
        self.sup_moves = sup_moves

    def to_prims(self) -> dict:
        return {'sup_moves': list(int(move) for move in self.sup_moves)}

    @classmethod
    def from_prims(cls, prims) -> 'SetSupportedMovesPacket':
        return cls(list(moves.Move(move) for move in prims['sup_moves']))

packets.register_packet(SetSupportedMovesPacket)

class FinishConfigurationPacket(packets.Packet):
    """This packet marks the completion of the initial configuration packets, implying that the
    GUI can now start rendering and making requests from the bot (at least as soon as game states
    are available)
    """
    pass

packets.register_packet(FinishConfigurationPacket)

class StateActionValuesRequestPacket(packets.Packet):
    """This packet is sent from the GUI to the bot, requesting the state action values for the
    current game state. The result is a StateActionValuesResultPacket. Recall that the current
    game state is available to the bot since those packets are passed through.
    """
    pass

packets.register_packet(StateActionValuesRequestPacket)

class StateActionValuesResultPacket(packets.Packet):
    """This packet is sent from the bot to the GUI as a result for a request for state action values
    for the current state.

    Attributes:
        tick (int): the tick this is for
        values (dict[Move, float]): the value for the state-action corresponding with the current
            state and the specified action.
    """
    def __init__(self, values: typing.Dict[moves.Move, float], tick: int):
        self.values = values
        self.tick = tick

    def to_prims(self) -> dict:
        return {'tick': self.tick,
                'values': dict((str(int(move)), value) for move, value in self.values.items())}

    @classmethod
    def from_prims(cls, prims) -> 'StateActionValuesResultPacket':
        return cls(dict((moves.Move(int(move)), value) for move, value in prims['values']),
                   prims['tick'])

packets.register_packet(StateActionValuesResultPacket)

class MoveSelectedPacket(packets.Packet):
    """This packet is sent from the GUI to the bot to inform it that the specified move has been
    made

    Attributes:
        move (Move): the move that we made
    """
    def __init__(self, move: moves.Move) -> None:
        self.move = move

    def to_prims(self):
        return {'move': int(self.move)}

    @classmethod
    def from_prims(cls, prims) -> 'MoveSelectedPacket':
        return cls(moves.Move(prims['move']))

packets.register_packet(MoveSelectedPacket)

class MoveSuggestionRequestPacket(packets.Packet):
    """This packet is sent from the GUI to the bot to request just the bots suggestion for the
    current move.
    """
    pass

packets.register_packet(MoveSuggestionRequestPacket)

class MoveSuggestionResultPacket(packets.Packet):
    """The response to a MoveSuggestionRequestPacket. This is sent from the bot to the GUI

    Attributes:
        move (Move): the move that is suggested
        tick (int): the tick this suggestion is for
    """
    def __init__(self, move: moves.Move, tick: int) -> None:
        self.move = move
        self.tick = tick

    def to_prims(self):
        return {'move': int(self.move), 'tick': self.tick}

    @classmethod
    def from_prims(cls, prims) -> 'MoveSuggestionResultPacket':
        return cls(moves.Move(prims['move']), prims['tick'])

packets.register_packet(MoveSuggestionResultPacket)
