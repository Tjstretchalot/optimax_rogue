"""This is the entry point for the server. It is passed a secret for each player
that allows them to identify themself.
"""
import enum
import typing
import socket
from contextlib import suppress

import optimax_rogue.networking.serializer as ser
import optimax_rogue.networking.packets as packets
import optimax_rogue.game.state as state
import optimax_rogue.game.world as world
import optimax_rogue.game.entities as entities
from optimax_rogue.logic.updater import Updater
from optimax_rogue.networking.shared import Connection
from optimax_rogue.logic.worldgen import DungeonGenerator
from optimax_rogue.networking.server import Server, PlayerConnection, SpectatorConnection

class PregameUpdateResult(enum.IntEnum):
    """The update results from the pregame stage"""
    InProgress = 1  # we need more time!
    SetupFailed = 2 # not everyone connected
    Ready = 3       # we're ready to start the match

class IdentifyPacket(packets.Packet):
    """Sent by a spectator in the lobby to identify themself

    Attributes:
        secret (bytes): the secret identification
    """
    def __init__(self, secret: bytes):
        self.secret = secret

    @classmethod
    def has_custom_serializer(cls):
        return True

    def to_prims(self):
        return self.secret

    @classmethod
    def from_prims(cls, prims) -> 'IdentifyPacket':
        return cls(prims)

packets.register_packet(IdentifyPacket)

class IdentifyResultPacket(packets.Packet):
    """Sent from the server back to a spectator to tell them about the result of
    their IdentifyPacket

    Attributes:
        player_id (int, optional): if specified, the id that the spectator
            successfully identified as. Either 1 or 2
    """
    def __init__(self, player_id: typing.Optional[int]):
        self.player_id = player_id

packets.register_packet(IdentifyResultPacket)

class LobbyChangePacket(packets.Packet):
    """Correspons to the pregame lobby closing either due to failure or
    because the real server is spawning

    Attributes:
        result (PregameUpdateResult): the result of the lobby
    """
    def __init__(self, result: PregameUpdateResult):
        self.result = result

    def to_prims(self):
        return {'result': int(self.result)}

    @classmethod
    def from_prims(cls, prims):
        return cls(PregameUpdateResult(prims['result']))

packets.register_packet(LobbyChangePacket)

class ServerPregame:
    """This controls the server prior to the game starting; it spawns the first dungeon,
    sets up initial modifiers and spawns the initial players. Once all players are
    connected this is ready to convert to a Server

    Attributes:
        listen_sock (socket.socket): the socket we are listening to connections on
        player1_conn (Connection, optional): if the first player is connected, this is
            their connection
        player1_secret (bytes): the bytes that player1 identifies themself with
        player2_conn (Connection, optional): if the second player is connected, this is
            their connection
        player2_secret (bytes): the bytes that player2 identifies themself with

        spectators [list[Connection]]: a list of people who want to spectate the game once
            it starts

        dgen (DungeonGenerator): used to create the initial world and pass to the updater
        tickrate (float): the tickrate, passed to the server
    """
    def __init__(self, listen_sock: socket.socket, player1_secret: bytes, player2_secret: bytes,
                 dgen: DungeonGenerator, tickrate: float):
        self.listen_sock = listen_sock
        self.player1_conn: Connection = None
        self.player2_conn: Connection = None
        self.player1_secret = player1_secret
        self.player2_secret = player2_secret
        self.spectators: typing.List[Connection] = []
        self.dgen = dgen
        self.tickrate = float(tickrate)

    def update(self) -> typing.Tuple[PregameUpdateResult,
                                     typing.Optional[Server]]:
        """Manages checking for new connections and keeping current connections alive

        Returns:
            result (PregameUpateResult): the current state of the lobby
            server (optional, Server): if the result is Ready, this is the server that
                should be updated instead of us
        """
        if self.player1_conn:
            self.player1_conn.update()
        if self.player2_conn:
            self.player2_conn.update()


        if (self.player1_conn and self.player1_conn.disconnected() or
                self.player2_conn and self.player2_conn.disconnected()):
            print('[pregame] lobby ended due to disconnect')
            self.broadcast_packet(LobbyChangePacket(
                PregameUpdateResult.SetupFailed
            ))
            self.shutdown_if_alive(self.player1_conn)
            self.shutdown_if_alive(self.player2_conn)
            for spec in self.spectators:
                self.shutdown_if_alive(spec)
            return PregameUpdateResult.SetupFailed, None

        for spec in self.spectators:
            spec: Connection
            spec.update()

        for ind in range(len(self.spectators) - 1, -1, -1):
            spec: Connection = self.spectators[ind]
            if spec.disconnected():
                self.spectators.pop(ind)
                continue

            packet = spec.read()
            if packet is not None:
                if isinstance(packet, IdentifyPacket):
                    if self.player1_conn is None and self.player1_secret == packet.secret:
                        print('[server_pregame] spectator successfully identified as player 1')
                        self.player1_conn = self.spectators.pop(ind)
                        self.player1_conn.send(IdentifyResultPacket(1))
                    elif self.player2_conn is None and self.player2_secret == packet.secret:
                        print('[server_pregame] spectator successfully identified as player 2')
                        self.player2_conn = self.spectators.pop(ind)
                        self.player2_conn.send(IdentifyResultPacket(2))
                    else:
                        print('[server_pregame] spectator unsuccessfully identified')
                        spec.send(IdentifyResultPacket(None))
                else:
                    print('[server_pregame] spectator sent bad packet')
                    self.shutdown_if_alive(spec)
                    self.spectators.pop(ind)

        if self.player1_conn is not None and self.player2_conn is not None:
            print('[server_pregame] starting game')
            server = self._start_game()
            return PregameUpdateResult.Ready, server

        self._check_connections()
        return PregameUpdateResult.InProgress, None

    def _check_connections(self):
        """Checks for incoming connections and adds them to the list of spectators
        """
        with suppress(BlockingIOError):
            conn, addr = self.listen_sock.accept()
            print(f'[server_pregame] got new connection from {addr}')
            conn.setblocking(0)
            spec = Connection(conn, addr)
            self.spectators.append(spec)

    def _start_game(self) -> Server:
        """Starts the game. Must have both player 1 and player 2 connected. Initializes
        the first dungeon, spawns both players in it, sends a sync update to everyone,
        then returns the Server that should manage this from now on"""

        dung: world.Dungeon = self.dgen.spawn_dungeon(0)
        p1x, p1y = dung.get_random_unblocked()
        p2x, p2y = dung.get_random_unblocked()
        while (p2x, p2y) == (p1x, p1y):
            p2x, p2y = dung.get_random_unblocked()

        ent1 = entities.Entity(1, 0, p1x, p1y, 10, 10, 2, 1, [], dict())
        ent2 = entities.Entity(2, 0, p2x, p2y, 10, 10, 2, 1, [], dict())

        game_state = state.GameState(True, 1, 2, world.World({0: dung}), [ent1, ent2])

        self.player1_conn.send(packets.SyncPacket(game_state.view_for(ent1), 1))
        self.player2_conn.send(packets.SyncPacket(game_state.view_for(ent2), 2))

        for spec in self.spectators:
            spec.send(packets.SyncPacket(game_state.view_spec(), None))

        updater = Updater(self.dgen)
        server = Server(game_state, updater, self.tickrate, self.listen_sock,
                        PlayerConnection.copy_from(self.player1_conn, 1),
                        PlayerConnection.copy_from(self.player2_conn, 2),
                        [SpectatorConnection.copy_from(s) for s in self.spectators])
        return server

    def shutdown_if_alive(self, conn: Connection) -> None:
        """Shuts down the specified connection if it is currently alive"""
        if conn is None or conn.disconnected():
            return

        conn.connection.shutdown(socket.SHUT_RDWR)
        conn.connection = None

    def broadcast_packet(self, packet: packets.Packet) -> None:
        """Broadcasts the specified packet to all connections"""
        serd = ser.serialize(packet)
        if self.player1_conn:
            self.player1_conn.send_serd(serd)
        if self.player2_conn:
            self.player2_conn.send_serd(serd)

        for spec in self.spectators:
            spec.send_serd(serd)
