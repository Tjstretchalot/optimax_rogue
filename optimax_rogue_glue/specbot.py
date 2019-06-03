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
    args = parser.parse_args()

    secret1 = secrets.token_hex()
    secret2 = secrets.token_hex()

    subprocess.Popen(
        ['python', '-m', 'optimax_rogue.server.main', secret1, secret2, '--port', str(args.port),
         '--log', 'server_log.txt'],
        creationflags=subprocess.CREATE_NEW_CONSOLE)

    time.sleep(2)

    subprocess.Popen(
        ['python', '-m', 'optimax_rogue_bots.main', 'localhost', str(args.port), args.bot1, secret1,
         '--log', 'bot1_log.txt'],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    subprocess.Popen(
        ['python', '-m', 'optimax_rogue_bots.main', 'localhost', str(args.port), args.bot2, secret2,
         '--log', 'bot2_log.txt'],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    time.sleep(0.2)

    subprocess.Popen(
        ['python', '-m', 'optimax_rogue_cmdspec.main', 'localhost', str(args.port)],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

if __name__ == '__main__':
    main()