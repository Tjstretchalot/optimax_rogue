"""Server networking and updating logic
"""
import socket
import typing
import time
from contextlib import suppress

import optimax_rogue.networking.packets as packets
from optimax_rogue.logic.updater import Updater, UpdateResult
import optimax_rogue.logic.updates as updates
from optimax_rogue.game.state import GameState
from optimax_rogue.networking.shared import Connection
import optimax_rogue.networking.serializer as ser

class PlayerConnection(Connection):
    """Describes a connection to the server by someone who is actually
    in the game

    Attributes:
        entity_iden (int): the identifier for the entity this player controls
        move (optional, int): the move that this player has chosen for the current turn
    """

    def __init__(self, connection: socket.socket, address: str, entity_iden: int) -> None:
        super().__init__(connection, address)
        self.entity_iden = entity_iden
        self.move = None

    @classmethod
    def copy_from(cls, other: Connection, iden: int):
        """Turns the generic connection into a player connection by associating with the
        given iden"""
        res = cls(other.connection, other.address, iden)
        res.send_queue = other.send_queue
        res.rec_queue = other.rec_queue
        res.curr_send_packet = other.curr_send_packet
        res.curr_rec = other.curr_rec
        return res

class SpectatorConnection(Connection):
    """Describes a connection to the server by someone who is watching the game"""

    @classmethod
    def copy_from(cls, other: Connection):
        """Turns the generic connection into a spectator connection"""
        res = cls(other.connection, other.address)
        res.send_queue = other.send_queue
        res.rec_queue = other.rec_queue
        res.curr_send_packet = other.curr_send_packet
        res.curr_rec = other.curr_rec
        return res

class Server:
    """Handles the glue that allows the game to update while informing all clients

    Attributes:
        game_state (GameState): contains the entire state of the game
        updater (Updater): the thing that moves time along

        tickrate (float): minimum seconds between ticks

        listen_sock (socket.socket): the socket that spectators can connect to

        player1_conn (PlayerConnection): the connection from player 1
        player2_conn (PlayerConnection): the connection from player 2

        spectators (SpectatorConnection): all the spectators

        _last_tick (float): last time.time() we ticked
    """

    def __init__(self, game_state: GameState, updater: Updater, tickrate: float,
                 listen_sock: socket.socket,
                 player1_conn: PlayerConnection, player2_conn: PlayerConnection,
                 spectators: typing.List[SpectatorConnection]):
        if not game_state.is_authoritative:
            raise ValueError('server must have authoritative game state')
        if not isinstance(player1_conn, PlayerConnection):
            raise ValueError(f'expected player1_conn is PlayerConnection, got {player1_conn} (type={type(player1_conn)})')
        if not isinstance(player2_conn, PlayerConnection):
            raise ValueError(f'expected player2_conn is PlayerConnection, got {player2_conn} (type={type(player2_conn)})')
        self.game_state = game_state
        self.updater = updater
        self.tickrate = tickrate
        self.listen_sock = listen_sock
        self.player1_conn = player1_conn
        self.player2_conn = player2_conn
        self.spectators = spectators
        self._last_tick = time.time()

    def update(self) -> UpdateResult:
        """Handles moving the world along and scanning for new / disconnected spectators
        """
        self.player1_conn.update()
        self.player2_conn.update()
        for spec in self.spectators:
            spec.update()

        if self.player1_conn.disconnected() and self.player2_conn.disconnected():
            print('[server] both players disconnected -> tie')
            return UpdateResult.Tie

        if self.player1_conn.disconnected():
            print('[server] game ended by player 1 disconnecting')
            return UpdateResult.Player2Win

        if self.player2_conn.disconnected():
            print('[server] game ended by player 2 disconnecting')
            return UpdateResult.Player1Win

        for i in range(len(self.spectators) - 1, -1, -1):
            if self.spectators[i].disconnected():
                print('[server] a spectator disconnected')
                self.spectators.pop(i)

        self._handle_player(self.player1_conn)
        self._handle_player(self.player2_conn)

        if (self.player1_conn.move is not None and self.player2_conn.move is not None
                and time.time() >= self._last_tick + self.tickrate):
            self._last_tick = time.time()

            self._broadcast_packet(packets.TickStartPacket())
            result, upds = self.updater.update(self.game_state, self.player1_conn.move,
                                               self.player2_conn.move)

            for upd in upds:
                self._broadcast_update(upd)
            self._broadcast_packet(packets.TickEndPacket(result))

            if result != UpdateResult.InProgress:
                print(f'[server] game ended normally with result {result}')

            return result

        self._check_new_spectators()

        return UpdateResult.InProgress

    def _check_new_spectators(self):
        with suppress(BlockingIOError):
            conn, addr = self.listen_sock.accept()
            print(f'[server] got new connection from {addr}')
            conn.setblocking(0)
            spec = SpectatorConnection(conn, addr)
            spec.send(packets.SyncPacket(self.game_state.view_spec(), None))
            self.spectators.append(spec)

    def _broadcast_update(self, update: updates.GameStateUpdate):
        p1_handled = False
        p2_handled = False
        if isinstance(update, updates.EntityPositionUpdate) and update.depth_changed:
            update: updates.EntityPositionUpdate
            if update.entity_iden == self.player1_conn.entity_iden:
                self.player1_conn.send(
                    packets.SyncPacket(self.game_state.view_for(
                        self.game_state.player_1
                    ), self.player1_conn.entity_iden)
                )
                p1_handled = True
            elif update.entity_iden == self.player2_conn.entity_iden:
                self.player2_conn.send(
                    packets.SyncPacket(self.game_state.view_for(
                        self.game_state.player_2
                    ), self.player2_conn.entity_iden)
                )
                p2_handled = True

            if not p1_handled and update.depth == self.game_state.player_1.depth:
                self.player1_conn.send(
                    packets.UpdatePacket(updates.EntitySpawnUpdate(
                        self.updater.get_incr_upd_order(),
                        self.game_state.iden_lookup[update.entity_iden]
                    ))
                )
                p1_handled = True

            if not p2_handled and update.depth == self.game_state.player_2.depth:
                self.player2_conn.send(
                    packets.UpdatePacket(updates.EntitySpawnUpdate(
                        self.updater.get_incr_upd_order(),
                        self.game_state.iden_lookup[update.entity_iden]
                    ))
                )
                p1_handled = True


        if not isinstance(update, updates.DungeonCreatedUpdate):
            if not p1_handled and update.relevant_for(
                    self.game_state,
                    self.game_state.iden_lookup[self.player1_conn.entity_iden].depth):
                self.player1_conn.send(packets.UpdatePacket(update))

            if not p2_handled and update.relevant_for(
                    self.game_state,
                    self.game_state.iden_lookup[self.player2_conn.entity_iden].depth):
                self.player2_conn.send(packets.UpdatePacket(update))

        for spec in self.spectators:
            spec.send(packets.UpdatePacket(update))

    def _broadcast_packet(self, packet: packets.Packet):
        serd = ser.serialize(packet)
        self.player1_conn.send_serd(serd)
        self.player2_conn.send_serd(serd)
        for spec in self.spectators:
            spec.send_serd(serd)

    def _handle_player(self, player: PlayerConnection) -> None:
        while True:
            packet = player.read()
            if packet is None:
                return
            if isinstance(packet, packets.MovePacket):
                if player.entity_iden != packet.entity_iden:
                    print('[server] player move packet has bad ent id')
                    self._disconnect_player(player)
                    return

                player.move = packet.move
            else:
                print(f'[server] player sent bad packet type {packet} (type={type(packet)})')
                self._disconnect_player(player)
                return

    def _disconnect_player(self, player: PlayerConnection) -> None:
        if player == self.player1_conn:
            print('[server] forcibly disconnecting player 1')
        elif player == self.player2_conn:
            print('[server] forcibly disconnecting player 2')
        else:
            print('[server] forcibly disconnecting a player')

        player.connection.shutdown(socket.SHUT_RDWR)
        player.connection = None
