"""Connects to the server passed in through the command line arguments. For
windows make sure you pip install windows-curses
"""
import curses
import time
import logging
import typing
import argparse
import socket
import traceback
from optimax_rogue.utils.ticker import Ticker
import optimax_rogue.game.world as world
import optimax_rogue.game.state as state
import optimax_rogue.game.entities as entities
import optimax_rogue.server.pregame as pregame
import optimax_rogue.networking.shared as nshared
import optimax_rogue.logic.worldgen as worldgen
import optimax_rogue.networking.packets as packets
from optimax_rogue_cmdspec.map import TextMapView
from optimax_rogue.logic.updater import UpdateResult

def main(stdscr):
    """Invoked when this file is invoked"""
    parser = argparse.ArgumentParser(description='Spectate a game of OptiMAX Rogue')
    parser.add_argument('ip', type=str, help='the ip to connect to')
    parser.add_argument('port', type=int, help='the port to connect on')
    args = parser.parse_args()
    logger = logging.Logger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler('log.txt', 'w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    logger.addHandler(fh)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((args.ip, args.port))
    sock.setblocking(False)

    conn = nshared.Connection(sock, args.ip)
    game_state = init_empty_map()

    stdscr.clear()
    stdscr.nodelay(True)

    view = TextMapView()

    view.update(stdscr, game_state, logger)

    curses.curs_set(0) # pylint: disable=no-member

    ticker = Ticker(0.016)
    need_update = False
    in_update = False
    try:
        while True:
            ticker()
            if need_update:
                view.update(stdscr, game_state, logger)
                need_update = False
                stdscr.refresh()

            try:
                ch = stdscr.getch()
                if ch != -1:
                    finish, refresh = handle_char(game_state, view, logger, ch)
                    if finish:
                        break
                    need_update = need_update or refresh
            except curses.error: # pylint: disable=no-member
                pass

            conn.update()
            pack = conn.read()
            if not pack:
                if conn.disconnected():
                    logger.info('connection ended abruptly')
                    break
                continue
            need_update = True
            if not in_update:
                if isinstance(pack, packets.SyncPacket):
                    pack: packets.SyncPacket
                    game_state = pack.game_state
                    game_state.on_tick()
                    need_update = True
                    continue
                if not isinstance(pack, packets.TickStartPacket):
                    sock.shutdown(socket.SHUT_RDWR)
                    raise ValueError(f'bad packet: {pack} (type={type(pack)}) (expected TickStartPacket)')
                in_update = True
                continue
            if isinstance(pack, packets.TickEndPacket):
                pack: packets.TickEndPacket
                if pack.result != UpdateResult.InProgress:
                    sock.shutdown(socket.SHUT_RDWR)
                    logger.info('game ended with result %s', str(pack.result))
                    break
                in_update = False
                game_state.on_tick()
                if view.prompt and view.prompt[0].startswith('Selected'):
                    if view.highlighted_id not in game_state.iden_lookup:
                        view.highlighted_id = None
                    else:
                        ent = game_state.iden_lookup[view.highlighted_id]
                        view.dungeon = ent.depth
                        set_entity_prompt(game_state, view, logger)
                        need_update = True
                continue
            if isinstance(pack, packets.SyncPacket):
                pack: packets.SyncPacket
                game_state = pack.game_state
                game_state.on_tick()
                continue
            game_state = handle_packet(game_state, pack)
            if game_state is None:
                logger.info('game ended irregularly')
                sock.shutdown(socket.SHUT_RDWR)
                break
    except:
        logger.error('Fatal error', exc_info=1)
        raise


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
    if isinstance(pack, pregame.LobbyChangePacket):
        return
    raise ValueError(f'unknown packet: {pack} (type={type(pack)})')


def init_empty_map() -> state.GameState:
    dung: world.Dungeon = worldgen.EmptyDungeonGenerator(80, 24).spawn_dungeon(0)

    p1x, p1y = dung.get_random_unblocked()
    p2x, p2y = dung.get_random_unblocked()
    while (p2x, p2y) == (p1x, p1y):
        p2x, p2y = dung.get_random_unblocked()

    ent1 = entities.Entity(1, 0, p1x, p1y, 10, 10, 2, 1, [], dict())
    ent2 = entities.Entity(2, 0, p2x, p2y, 10, 10, 2, 1, [], dict())

    game_state = state.GameState(True, 1, 2, world.World({0: dung}), [ent1, ent2])
    game_state.on_tick()
    return game_state

def set_help_prompt(game_state: state.GameState, view: TextMapView, logger: logging.Logger):
    """Sets the prompt to the help prompt"""
    view.prompt = (
        '1  go to the dungeon that has player 1 and highlight player 1',
        '2  go to the dungeon that has player 2 and highlight player 2',
        'o  print player 1 info and highlight player 1',
        'x  print player 2 info and highlight player 2',
        'e  print enemy info on screen (repeat to iterate, selected is highlighted)',
        'c  clear selection / highlight',
        'q  quit',
        'h  print this help',
    )
    view.prompt_y = 0

def set_entity_prompt(game_state: state.GameState, view: TextMapView, logger: logging.Logger):
    """Sets the prompt for the view to match the highlighted entity"""
    ent: entities.Entity = game_state.iden_lookup[view.highlighted_id]
    prompt = []
    prompt.append(f'Selected ID {view.highlighted_id}')
    prompt.append(f'Location: ({ent.x}, {ent.y}) @ depth {ent.depth}')
    prompt.append(f'Health: {ent.health}/{ent.max_health.value}')
    prompt.append(f'Damage: {ent.damage.value}')
    prompt.append(f'Armor: {ent.armor.value}')
    prompt.append('Items:')
    for item in ent.items:
        prompt.append(f'  {item.name} x{item.stack_size}')
    prompt.append('Modifiers:')
    for mod in ent.modifiers:
        prompt.append(f'  {mod.name}: {mod.description}')
    view.prompt_y = 0
    view.prompt = prompt

def handle_char(game_state: state.GameState, view: TextMapView, logger: logging.Logger,
                ch: int) -> typing.Tuple[bool, bool]:
    """Handles the given input character ordinal"""
    logger.debug('got char %s (int: %s)', ch, int(ch))

    need_update = False
    if ch == ord('1'):
        view.highlighted_id = game_state.player_1_iden
        depth = game_state.iden_lookup[view.highlighted_id].depth
        view.dungeon = depth
        logger.debug('moved to depth %s', depth)
        set_entity_prompt(game_state, view, logger)
        need_update = True
    elif ch == ord('2'):
        view.highlighted_id = game_state.player_2_iden
        depth = game_state.iden_lookup[view.highlighted_id].depth
        view.dungeon = depth
        logger.debug('moved to depth %s', depth)
        set_entity_prompt(game_state, view, logger)
        need_update = True
    elif ch == ord('o'):
        view.highlighted_id = game_state.player_1_iden
        set_entity_prompt(game_state, view, logger)
        need_update = True
    elif ch == ord('x'):
        view.highlighted_id = game_state.player_2_iden
        set_entity_prompt(game_state, view, logger)
        need_update = True
    elif ch == ord('c'):
        view.highlighted_id = None
        view.prompt_y = 0
        view.prompt = ['Cleared!']
        need_update = True
    elif ch == curses.KEY_DOWN:
        view.prompt_y += 1
        logger.debug('key down detected')
        need_update = True
    elif ch == curses.KEY_UP:
        view.prompt_y -= 1
        need_update = True
    elif ch == ord('h'):
        set_help_prompt(game_state, view, logger)
        need_update = True
    elif ch == ord('q'):
        return True, False
    return False, need_update

if __name__ == '__main__':
    curses.wrapper(main)
