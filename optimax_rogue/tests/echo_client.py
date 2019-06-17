"""Echo client that sends many different packets and other objects to the echo
server and verifies they match"""

import optimax_rogue.networking.server # pylint: disable=unused-import

import optimax_rogue.networking.shared as nshared
import optimax_rogue.networking.packets as packets
import optimax_rogue.networking.serializer as ser
import optimax_rogue.game.state as state
import optimax_rogue.game.world as world
import optimax_rogue.logic.worldgen as worldgen
import optimax_rogue.game.entities as entities
from optimax_rogue.utils.ticker import Ticker
from contextlib import suppress
import socket

from optimax_rogue.tests.echo_server import EchoPacket

def _create_packets():
    """Returns [Serializable,...]"""
    dung: world.Dungeon = worldgen.EmptyDungeonGenerator(20, 20).spawn_dungeon(0)
    p1x, p1y = dung.get_random_unblocked()
    p2x, p2y = dung.get_random_unblocked()
    while (p2x, p2y) == (p1x, p1y):
        p2x, p2y = dung.get_random_unblocked()

    ent1 = entities.Entity(1, 0, p1x, p1y, 10, 10, 2, 1, [], dict())
    ent2 = entities.Entity(2, 0, p2x, p2y, 10, 10, 2, 1, [], dict())

    game_state = state.GameState(True, 1, 1, 2, world.World({0: dung}), [ent1, ent2])
    return [
        ent1,
        ent2,
        dung,
        game_state
    ]

def main():
    """Connects to echo server"""
    packets.register_packet(EchoPacket)
    host = '10.18.163.215'
    port = 1769
    ticker = Ticker(0.01)

    print(f'connecting to {host} at port {port}')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.setblocking(False)

    conn = nshared.Connection(sock, host)

    to_send = _create_packets()
    current_send = to_send.pop(0)
    current_is_sent = False

    while current_send or to_send:
        ticker()

        if not current_is_sent:
            print(f'sending {current_send}')
            conn.send(EchoPacket(current_send))
            current_is_sent = True

        conn.update()

        if conn.disconnected():
            print('connection closed abruptly')
            return

        inc = conn.read()
        if inc:
            if not isinstance(inc, EchoPacket):
                raise ValueError(f'expected echo packet got {inc} (type={type(inc)})')
            if inc.thing != current_send:
                raise ValueError(f'mismatch: expected {current_send}, got {inc.thing}')
            print(f'received {inc.thing}')
            if to_send:
                current_send = to_send.pop(0)
                current_is_sent = False
            else:
                current_send = None

    print('Successfully echod everything')
    sock.close()


if __name__ == '__main__':
    main()