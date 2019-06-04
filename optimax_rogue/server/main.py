"""Main entry into spawning a server. This is passed the secrets for players 1 and 2
(so they can identify themselves), and optionally the port to listen on"""

import argparse
import socket
import sys
import traceback
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
    parser.add_argument('-l', '--log', type=str, help='if specified, rerout stdout and stderr to this file')
    parser.add_argument('-t', '--tickrate', type=float, help='minimum seconds between ticks', default=1.0)
    parser.add_argument('--width', type=int, help='width of map', default=60)
    parser.add_argument('--height', type=int, help='height of map', default=10)
    args = parser.parse_args()

    if args.log:
        with open(args.log, 'w') as fh:
            sys.stdout = fh
            sys.stderr = fh
            try:
                _run(args)
            except:
                traceback.print_exc(file=fh)
                fh.flush()
                raise
            fh.flush()
    else:
        _run(args)


def _run(args):
    secret1 = args.secret1.encode('ASCII', 'strict')
    secret2 = args.secret2.encode('ASCII', 'strict')
    tickrate = args.tickrate
    if secret1 == secret2:
        print('secret1 cannot be the same as secret2')
        return

    host = args.host or 'localhost'
    port = args.port or 0

    dgen = EmptyDungeonGenerator(args.width, args.height)
    ticker = Ticker(0.016)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listen_sock:
        listen_sock.bind((host, port))
        listen_sock.setblocking(0)
        listen_sock.listen()
        host, port = listen_sock.getsockname()
        print(f'[main] bound on host {host}, port {port}')

        pregame = ServerPregame(listen_sock, secret1, secret2, dgen, tickrate)
        result = PregameUpdateResult.InProgress
        server = None
        while result == PregameUpdateResult.InProgress:
            result, server = pregame.update()
            ticker()

        if result != PregameUpdateResult.Ready:
            print(f'[main] ending due to non-ready pregame result {result}')
            return

        result = UpdateResult.InProgress
        while result == UpdateResult.InProgress:
            server.game_state.on_tick()
            result = server.update()
            ticker()

        while server.has_pending():
            server.update_queues()
            ticker()

        print(f'[main] game ended with result {result}')



if __name__ == '__main__':
    main()