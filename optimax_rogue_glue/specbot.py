"""Launches a game with two bots and watches them with a command spectator
"""
import argparse
import subprocess
import secrets
import time

def main():
    """Main entry"""
    parser = argparse.ArgumentParser(description='Watch two bots play OptiMAX Rogue')
    parser.add_argument('bot1', metavar='B1', type=str, help='module + class for first bot')
    parser.add_argument('bot2', metavar='B2', type=str, help='module + class for second bot')
    parser.add_argument('--port', type=int, default=1769, help='port to use')
    parser.add_argument('--tickrate', type=float, default=1.0, help='seconds per tick for server')
    parser.add_argument('--headless', action='store_true', help='Use headless mode')
    parser.add_argument('--repeat', action='store_true', help='Keeps respawning server until stopped')
    args = parser.parse_args()

    _run(args)
    if args.repeat:
        while True:
            _run(args)


def _run(args):
    secret1 = secrets.token_hex()
    secret2 = secrets.token_hex()

    create_flags = 0 if args.headless else subprocess.CREATE_NEW_CONSOLE

    procs = []
    procs.append(subprocess.Popen(
        ['python', '-m', 'optimax_rogue.server.main', secret1, secret2, '--port', str(args.port),
         '--log', 'server_log.txt', '--tickrate', str(args.tickrate)],
        creationflags=create_flags
    ))

    time.sleep(2)

    procs.append(subprocess.Popen(
        ['python', '-m', 'optimax_rogue_bots.main', 'localhost', str(args.port), args.bot1, secret1,
         '--log', 'bot1_log.txt'],
        creationflags=create_flags
    ))

    procs.append(subprocess.Popen(
        ['python', '-m', 'optimax_rogue_bots.main', 'localhost', str(args.port), args.bot2, secret2,
         '--log', 'bot2_log.txt'],
        creationflags=create_flags
    ))

    time.sleep(0.2)

    if not args.headless:
        procs.append(subprocess.Popen(
            ['python', '-m', 'optimax_rogue_cmdspec.main', 'localhost', str(args.port)],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        ))

    for proc in procs:
        proc.wait()
        print('[specbot] process finished')

    print('[specbot] all processes finished')

if __name__ == '__main__':
    main()