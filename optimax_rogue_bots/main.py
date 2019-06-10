"""This is the typical entry point into this module. You pass it
an ip, a port, and a bot to use and it connects and plays until
the game ends"""
import argparse
import importlib
import socket
import sys
import traceback

import optimax_rogue.networking.packets as packets
import optimax_rogue.networking.shared as nshared
import optimax_rogue.server.pregame as pregame
import optimax_rogue.game.state as state
import optimax_rogue.logic.updates # pylint: disable=unused-import

from optimax_rogue.logic.updater import UpdateResult
from optimax_rogue.utils.ticker import Ticker
from optimax_rogue_bots.bot import Bot

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Connect a bot which plays OptiMAX Rogue')
    parser.add_argument('ip', type=str, help='the ip to connect to')
    parser.add_argument('port', type=int, help='the port to connect on')
    parser.add_argument('bot', metavar='B', type=str, help='module + class for the bot')
    parser.add_argument('secret', metavar='S', type=str, help='the secret to identify with')
    parser.add_argument('-l', '--log', type=str,
                        help='if specified, rerout stdout and stderr to this file')
    parser.add_argument('-tr', '--tickrate', type=float, default=0.25,
                        help='the maximum number of seconds before we try to respond to the server')
    args = parser.parse_args()

    if args.log:
        with open(args.log, 'w') as fh:
            sys.stdout = fh
            sys.stderr = fh
            try:
                _run(args)
            except:
                traceback.print_exc(file=fh)
                raise
    else:
        _run(args)

def _run(args):
    bot_spl = args.bot.split('.')
    bot_mod = importlib.import_module('.'.join(bot_spl[:-1]))

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.ip, args.port))
    sock.setblocking(False)

    conn = nshared.Connection(sock, args.ip)

    conn.send(pregame.IdentifyPacket(args.secret.encode('ASCII', 'strict')))
    ticker = Ticker(0.02)
    playid = None
    while True:
        ticker()
        conn.update()
        succ_pack = conn.read()
        if succ_pack:
            if not isinstance(succ_pack, pregame.IdentifyResultPacket):
                sock.shutdown(socket.SHUT_RDWR)
                raise ValueError(f'expected identify result, got {succ_pack} (type={type(succ_pack)})')
            succ_pack: pregame.IdentifyResultPacket
            if not succ_pack.player_id:
                sock.shutdown(socket.SHUT_RDWR)
                raise ValueError(f'expected successful identify, but failed')
            playid = succ_pack.player_id
            print(f'Successfully identified and received player id {playid}')
            break
        elif conn.disconnected():
            raise ValueError('server shutdown prematurely (in pregame phase)')

    game_state = None
    while True:
        ticker()
        conn.update()
        pack = conn.read()
        if not pack:
            if conn.disconnected():
                raise ValueError('server shutdown prematurely')
            continue
        if isinstance(pack, pregame.LobbyChangePacket):
            pack: pregame.LobbyChangePacket
            if pack.result == pregame.PregameUpdateResult.SetupFailed:
                sock.shutdown(socket.SHUT_RDWR)
                raise ValueError('lobby setup failed')
        elif isinstance(pack, packets.SyncPacket):
            pack: packets.SyncPacket
            game_state = pack.game_state
            playid = pack.player_iden
            print(f'received sync packet; game is starting')
            break
        else:
            print(f'ignoring unexpected packet {pack} (type={type(pack)})')

    def get_ent():
        iden = game_state.player_1_iden if playid == 1 else game_state.player_2_iden
        return game_state.iden_lookup[iden]

    bot: Bot = getattr(bot_mod, bot_spl[-1])(get_ent().iden)
    need_move = True
    in_update = False
    ticker.secondary_target_secs = args.tickrate
    ticker.time_killer = bot.think
    while True:
        ticker()
        conn.update()
        if need_move and not in_update:
            move = bot.move(game_state)
            bot.on_move(game_state, move)
            conn.send(packets.MovePacket(get_ent().iden, move, game_state.tick))
            need_move = False

        pack = conn.read()
        if not pack:
            if conn.disconnected():
                print('[optimax_rogue_bots.main] connection ended abruptly')
                break
            continue
        if not in_update:
            if not isinstance(pack, packets.TickStartPacket):
                sock.shutdown(socket.SHUT_RDWR)
                raise ValueError(f'bad packet: {pack} (type={type(pack)}) (expected TickStartPacket)')
            in_update = True
            continue
        if isinstance(pack, packets.TickEndPacket):
            pack: packets.TickEndPacket
            if pack.result != UpdateResult.InProgress:
                sock.shutdown(socket.SHUT_RDWR)
                bot.finished(game_state, pack.result)
                print(f'game ended with result {pack.result}')
                break
            game_state.tick += 1
            in_update = False
            need_move = True
            game_state.on_tick()
            continue
        game_state = handle_packet(game_state, pack)
        if game_state is None:
            print('game ended irregularly')
            sock.shutdown(socket.SHUT_RDWR)
            break

def handle_packet(game_state: state.GameState, pack: packets.Packet) -> state.GameState:
    """Handles the given packet and returns the new state, or none if the game ended"""
    if isinstance(pack, packets.SyncPacket):
        pack: packets.SyncPacket
        return pack.game_state
    if isinstance(pack, packets.UpdatePacket):
        pack: packets.UpdatePacket
        pack.update.apply(game_state)
        return game_state
    raise ValueError(f'unknown packet: {pack} (type={type(pack)})')

if __name__ == '__main__':
    main()
