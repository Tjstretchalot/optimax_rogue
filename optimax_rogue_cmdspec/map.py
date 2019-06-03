"""Module for printing the map using curses
"""
import curses
import enum
import optimax_rogue.game.world as world
import optimax_rogue.game.state as state

class EntityDisplayStyle(enum.IntEnum):
    """Simple enum that classifies entity display styles"""
    Player1 = 1
    Player2 = 2
    NPC = 3

TILES = {
    world.Tile.Ground: ('.', curses.A_DIM),
    world.Tile.Wall: ('#',),
    world.Tile.StaircaseDown: ('\\',),
}

ENTITIES = {
    EntityDisplayStyle.Player1: (('o', curses.A_NORMAL), ('O', curses.A_STANDOUT)),
    EntityDisplayStyle.Player2: (('x', curses.A_NORMAL), ('X', curses.A_STANDOUT)),
    EntityDisplayStyle.NPC: (('e', curses.A_NORMAL), ('E', curses.A_STANDOUT))
}

class TextMapView:
    """Describes something that is capable of providing a view of the
    map

    Attributes:
        dungeon (int, optional): the id of the dungeon this is looking at
        highlighted_id (int, optional): the id of the entity which is highlighted

        prompt_y (int): the starting y for the prompt
        prompt (list[str]): the text that is displayed at the bottom of the screen,
            where each str is one line
    """

    def __init__(self):
        self.dungeon = None
        self.highlighted_id = None

        self.prompt_y = 0
        self.prompt = ['Press h for help']

    def update(self, stdscr, game_state: state.GameState, logger):
        """Draws this view onto the screen starting at the top-left row/column
        """
        if self.dungeon is None or self.dungeon not in game_state.world.dungeons:
            self.dungeon = list(game_state.world.dungeons.keys())[0]

        maxrow, maxcol = stdscr.getmaxyx()

        dung: world.Dungeon = game_state.world.dungeons[self.dungeon]

        for col in range(min(dung.tiles.shape[0], maxcol)):
            for row in range(min(dung.tiles.shape[1], maxrow)):
                stdscr.addstr(row, col, *TILES[dung.tiles[col, row]])

        if maxcol > dung.tiles.shape[0] - 1:
            spacing = ' ' * (maxcol - dung.tiles.shape[0] - 1)
            for row in range(min(dung.tiles.shape[1], maxrow)):
                try:
                    stdscr.addstr(row, dung.tiles.shape[0], spacing)
                except:
                    logger.error('spacing=%s, row=%s, maxrow=%s, maxcol=%s, reals=%s',
                                 len(spacing), row, maxrow, maxcol, dung.tiles.shape, exc_info=1)
                    raise

        for ent in game_state.entities:
            if ent.depth != self.dungeon:
                continue
            if ent.x >= maxcol or ent.y >= maxrow:
                continue

            disp_style = 1 if ent.iden == self.highlighted_id else 0
            if ent.iden == game_state.player_1_iden:
                ent_style = EntityDisplayStyle.Player1
            elif ent.iden == game_state.player_2_iden:
                ent_style = EntityDisplayStyle.Player2
            else:
                ent_style = EntityDisplayStyle.NPC

            stdscr.addstr(ent.y, ent.x, *ENTITIES[ent_style][disp_style])

        empty_line = ' ' * (maxcol - 1)
        prompt_line = self.prompt_y
        for row in range(dung.tiles.shape[1], maxrow):
            stdscr.addstr(row, 0, empty_line)
            if prompt_line >= 0 and prompt_line < len(self.prompt):
                stdscr.addstr(row, 0, self.prompt[prompt_line][:maxcol])
            prompt_line += 1





