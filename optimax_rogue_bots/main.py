"""This is the typical entry point into this module. You pass it
an ip, a port, and a bot to use and it connects and plays until
the game ends"""
import argparse
import importlib
import socket

import optimax_rogue.networking.packets as packets
import optimax_rogue.networking.shared as nshared
import optimax_rogue.server.pregame as pregame
import optimax_rogue.game.state as state

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
    args = parser.parse_args()


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
                sock.shutdown()
                raise ValueError(f'expected identify result, got {succ_pack} (type={type(succ_pack)})')
            succ_pack: pregame.IdentifyResultPacket
            if not succ_pack.player_id:
                sock.shutdown()
                raise ValueError(f'expected successful identify, but failed')
            playid = succ_pack.player_id
            print(f'Successfully identified and received player id {playid}')
            break

    game_state = None
    while True:
        ticker()
        conn.update()
        pack = conn.read()
        if not pack:
            continue
        if isinstance(pack, pregame.LobbyChangePacket):
            pack: pregame.LobbyChangePacket
            if pack.result == pregame.PregameUpdateResult.SetupFailed:
                sock.shutdown()
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
    while True:
        ticker()
        conn.update()
        if need_move and not in_update:
            move = bot.move(game_state)
            print(f'chose move {move}')
            conn.send(packets.MovePacket(get_ent().iden, move))
            need_move = False

        pack = conn.read()
        if not pack:
            continue
        if not in_update:
            if not isinstance(pack, packets.TickStartPacket):
                sock.shutdown()
                raise ValueError(f'bad packet: {pack} (type={type(pack)}) (expected TickStartPacket)')
            in_update = True
            continue
        if isinstance(pack, packets.TickEndPacket):
            pack: packets.TickEndPacket
            if pack.result != UpdateResult.InProgress:
                sock.shutdown()
                print(f'game ended with result {pack.result}')
                break
            in_update = False
            need_move = True
            continue
        game_state = handle_packet(game_state, pack)
        if game_state is None:
            print('game ended irregularly')
            sock.shutdown()
            break

def handle_packet(game_state: state.GameState, pack: packets.Packet) -> state.GameState:
    """Handles the given packet and returns the new state, or none if the game ended"""
    if isinstance(pack, packets.SyncPacket):
        pack: packets.SyncPacket
        return pack.game_state
    if isinstance(pack, packets.MovePacket):
        pack: packets.MovePacket
        ent = game_state.iden_lookup[pack.entity_iden]
        game_state.move_entity(ent, pack.newdepth, pack.newx, pack.newy)
        return game_state
    if isinstance(pack, packets.UpdatePacket):
        pack: packets.UpdatePacket
        pack.update.apply(game_state)
        return game_state
    raise ValueError(f'unknown packet: {pack} (type={type(pack)})')

if __name__ == '__main__':
    main()