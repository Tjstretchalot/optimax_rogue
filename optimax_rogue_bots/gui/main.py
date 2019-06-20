"""Entry point for bots that are connecting through the GUI instead of directly to
the server. Note that this isn't the GUI itself.
"""
import argparse
import sys
import importlib
import traceback
import socket
import datetime

from optimax_rogue_bots.gui.state_action_bot import StateActionBot
from optimax_rogue.logic.updater import UpdateResult
import optimax_rogue.networking.shared as nshared
import optimax_rogue_bots.gui.packets as gpackets
import optimax_rogue.game.state as state
import optimax_rogue.networking.packets as packets
from optimax_rogue.utils.ticker import Ticker

def main() -> None:
    """The main entry to connecting a particular implementation of state action bot to
    the GUI which will then connect to the server.
    """
    parser = argparse.ArgumentParser(description='Connect a bot to a GUI')
    parser.add_argument('ip', type=str, help='the ip to connect to')
    parser.add_argument('port', type=int, help='the port to connect on')
    parser.add_argument('bot', metavar='B', type=str, help='module + class for the bot')
    parser.add_argument('-l', '--log', type=str,
                        help='if specified, rerout stdout and stderr to this file')
    parser.add_argument('-tr', '--tickrate', type=float, default=0.25,
                        help='the maximum number of seconds before we try to respond to the GUI')
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
    bot_typ: type = getattr(bot_mod, bot_spl[-1])

    if not isinstance(bot_typ, type):
        bot_typ = bot_typ(None)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.ip, args.port))
    sock.setblocking(False)

    conn = nshared.Connection(sock, args.ip)

    conn.send(gpackets.SetBotPitchPacket(*bot_typ.pitch()))
    conn.send(gpackets.SetHighlightStylePacket(gpackets.HighlightStyle.StateAction))
    conn.send(bot_typ.scale_style())
    conn.send(gpackets.SetSupportedMovesPacket(bot_typ.supported_moves()))
    conn.send(gpackets.FinishConfigurationPacket())

    game_state: state.GameState = None
    player_id: int = None
    entity_id: int = None
    bot: StateActionBot = None

    in_update: bool = False

    ticker = Ticker(0.01)
    while True:
        ticker()

        conn.update()

        pack: packets.Packet = conn.read()
        if not pack:
            if conn.disconnected():
                print('[optimax_rogue_bots.gui.main] connection closed unexpectedly')
                break
            continue

        if isinstance(pack, packets.SyncPacket):
            pack: packets.SyncPacket
            game_state = pack.game_state
            player_id = pack.player_iden
            if player_id == 1:
                entity_id = game_state.player_1_iden
            else:
                entity_id = game_state.player_2_iden
            if not bot:
                bot = bot_typ(entity_id)
                ticker = Ticker(0.01, args.tickrate, bot.think)
            continue

        if isinstance(pack, packets.TickStartPacket):
            pack: packets.TickStartPacket
            if in_update:
                sock.shutdown(socket.SHUT_RDWR)
                print('[optimax_rogue_bots.gui.main] received TickStartPacket while in a tick')
                break
            in_update = True
            continue

        if isinstance(pack, packets.TickEndPacket):
            pack: packets.TickEndPacket
            if not in_update:
                sock.shutdown(socket.SHUT_RDWR)
                print('[optimax_rogue_bots.gui.main] received TickEndPacket while not in a tick')
                break
            if pack.result != UpdateResult.InProgress:
                sock.shutdown(socket.SHUT_RDWR)
                bot.finished(game_state, pack.result)
                print(f'[optimax_rogue_bots.gui.main] game ended with result {pack.result}')
                break
            in_update = False
            game_state.tick += 1
            game_state.on_tick()
            continue

        if isinstance(pack, packets.UpdatePacket):
            if not in_update:
                sock.shutdown(socket.SHUT_RDWR)
                print('[optimax_rogue_bots.gui.main] received UpdatePacket while not in tick')
                break
            pack: packets.UpdatePacket
            pack.update.apply(game_state)
            continue

        if isinstance(pack, gpackets.MoveSuggestionRequestPacket):
            if in_update:
                sock.shutdown(socket.SHUT_RDWR)
                print('[optimax_rogue_bots.gui.main] received MoveSuggestionRequestPacket while in tick')
                break
            pack: gpackets.MoveSuggestionRequestPacket
            move = bot.move(game_state)
            conn.send(gpackets.MoveSuggestionResultPacket(move))
            continue

        if isinstance(pack, gpackets.StateActionValuesRequestPacket):
            if in_update:
                sock.shutdown(socket.SHUT_RDWR)
                print('[optimax_rogue_bots.gui.main] received StateActionValuesRequestPacket while in tick')
                break
            pack: gpackets.StateActionValuesRequestPacket

            values = dict((move, bot.evaluate(game_state, move)) for move in bot.supported_moves())
            conn.send(gpackets.StateActionValuesResultPacket(values))
            continue

        if isinstance(pack, gpackets.MoveSelectedPacket):
            if in_update:
                sock.shutdown(socket.SHUT_RDWR)
                print('[optimax_rogue_bots.gui.main] received MoveSelectedPacket while in tick')
                break
            pack: gpackets.MoveSelectedPacket

            bot.on_move(game_state, pack.move)
            continue

        raise ValueError(f'unknown packet: {pack} (type={type(pack)})')

    print(f'shutting down as of {datetime.datetime.now()}')

if __name__ == '__main__':
    main()
