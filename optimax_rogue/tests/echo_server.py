"""This server simply echos back serializable objects which is helpful for testing
that serialization is both working and can be networked
"""
import optimax_rogue.networking.server # pylint: disable=unused-import

import optimax_rogue.networking.shared as nshared
import optimax_rogue.networking.packets as packets
import optimax_rogue.networking.serializer as ser
from optimax_rogue.utils.ticker import Ticker
from contextlib import suppress
import socket

class EchoPacket(packets.Packet):
    """This packet is specific to the echo server

    Attributes:
        thing (serializable): the thing that should be echod back
    """
    def __init__(self, thing: ser.Serializable):
        self.thing = thing

    @classmethod
    def identifier(cls):
        return 'optimax_rogue.tests.echo_server.echo_packet'

    def to_prims(self):
        return {'thing': ser.serialize_embeddable(self.thing)}

    @classmethod
    def from_prims(cls, prims) -> 'MovePacket':
        return cls(ser.deserialize_embeddable(prims['thing']))

def main():
    """Runs the echo server"""
    packets.register_packet(EchoPacket)
    host = 'localhost'
    port = 1769

    ticker = Ticker(0.01)
    connections = []
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listen_sock:
        listen_sock.bind((host, port))
        listen_sock.setblocking(0)
        listen_sock.listen()
        while True:
            ticker()
            for conn in connections:
                conn: nshared.Connection
                conn.update()

                pack = conn.read()
                if pack:
                    print(f'echoing back {type(pack)}')
                    conn.send(pack)

            for i in range(len(connections) - 1, 0, -1):
                if connections[i].disconnected():
                    print(f'[echo_server] client from {connections[i].address} disconnected')
                    connections.pop(i)


            with suppress(BlockingIOError):
                rawconn, addr = listen_sock.accept()
                print(f'[echo_server] got new connection from {addr}')
                rawconn.setblocking(0)

                conn = nshared.Connection(rawconn, addr)
                connections.append(conn)



if __name__ == '__main__':
    main()
