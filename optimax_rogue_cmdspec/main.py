"""Connects to the server passed in through the command line arguments. For
windows make sure you pip install windows-curses
"""
import curses
import time
import logging
import typing
from optimax_rogue.utils.ticker import Ticker
import optimax_rogue.game.world as world
from optimax_rogue.logic.worldgen import EmptyDungeonGenerator
import optimax_rogue.game.state as state
import optimax_rogue.game.entities as entities
from optimax_rogue_cmdspec.map import TextMapView

def main(stdscr):
    """Invoked when this file is invoked"""
    logger = logging.Logger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler('log.txt', 'w')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    logger.addHandler(fh)


    stdscr.clear()
    stdscr.nodelay(True)

    dung: world.Dungeon = EmptyDungeonGenerator(124, 24).spawn_dungeon(0)

    p1x, p1y = dung.get_random_unblocked()
    p2x, p2y = dung.get_random_unblocked()
    while (p2x, p2y) == (p1x, p1y):
        p2x, p2y = dung.get_random_unblocked()

    ent1 = entities.Entity(1, 0, p1x, p1y, 10, 10, 2, 1, [], dict())
    ent2 = entities.Entity(2, 0, p2x, p2y, 10, 10, 2, 1, [], dict())

    game_state = state.GameState(True, 1, 2, world.World({0: dung}), [ent1, ent2])
    game_state.on_tick()
    view = TextMapView()

    view.update(stdscr, game_state)

    curses.curs_set(0) # pylint: disable=no-member

    now = time.time()
    ticker = Ticker(0.016)
    need_update = False
    while True:
        ticker()
        if need_update:
            view.update(stdscr, game_state)
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
    if ch == ord('o'):
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
