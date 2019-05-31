"""Main entry into spawning a server. This is passed the secrets for players 1 and 2
(so they can identify themselves), and optionally the port to listen on"""

import argparse
import socket
from optimax_rogue.logic.worldgen import EmptyDungeonGenerator
from optimax_rogue.server.pregame import ServerPregame, PregameUpdateResult
from optimax_rogue.logic.updater import UpdateResult
from optimax_rogue.networking.server import Server
from optimax_rogue.utils.ticker import Ticker

def main():
    """Main entry function"""
    parser = argparse.ArgumentParser(description='Launch an OptiMAX Rogue Server')
    parser.add_argument('secret1', metavar='S1', type=str, help='player 1 secret')
    parser.add_argument('secret2', metavar='S2', type=str, help='player 2 secret')
    parser.add_argument('-hn', '--host', '--hostname', type=str, help='specify the host to use')
    parser.add_argument('-p', '--port', type=int, help='specify port to listen on')
    args = parser.parse_args()

    secret1 = args.secret1.encode('ASCII', 'strict')
    secret2 = args.secret2.encode('ASCII', 'strict')
    if secret1 == secret2:
        print('secret1 cannot be the same as secret2')
        parser.print_help()
        return

    host = args.host or 'localhost'
    port = args.port or 0

    dgen = EmptyDungeonGenerator(22, 12)
    ticker = Ticker(0.016)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listen_sock:
        listen_sock.bind((host, port))
        listen_sock.setblocking(0)
        listen_sock.listen()
        host, port = listen_sock.getsockname()
        print(f'[main] bound on host {host}, port {port}')

        pregame = ServerPregame(listen_sock, secret1, secret2, dgen)
        result = PregameUpdateResult.InProgress
        server = None
        while result == PregameUpdateResult.InProgress:
            result, server = pregame.update()
            ticker()

        if result != PregameUpdateResult.Ready:
            print('[main] ending due to non-ready pregame result')
            return

        result = UpdateResult.InProgress
        while result == UpdateResult.InProgress:
            result = server.update()
            ticker()

        print(f'[main] game ended with result {result}')


if __name__ == '__main__':
    main()