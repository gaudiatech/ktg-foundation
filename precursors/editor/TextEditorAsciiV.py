import katagames_sdk as katasdk
import sharedstuff


kengi = katasdk.kengi
pygame = kengi.pygame
EngineEvTypes = kengi.event.EngineEvTypes


# - constants
SHOW_ICON_DURAT = 2  # sec

# here so we can implement a crude syntax coloring (use a different color for these words)
PY_KEYWORDS = (
    # types
    'bool', 'list', 'tuple', 'str', 'int', 'float',
    # flow control
    'if', 'else', 'elif', 'for', 'while',
    # built-in functions
    'len', 'not', 'in', 'enumerate', 'range'
    # literals
                                     'None', 'True', 'False',
    # misc
    'def', 'return', 'class', 'self'
)


ascii_canvas = kengi.ascii


class TextEditorAsciiV(kengi.event.EventReceiver):
    def __init__(self, ref_mod, maxfps):
        super().__init__()
        self.locked_file = False

        self._mod = ref_mod
        self._maxfps = maxfps
        self.latest_t = None  # pr disposer pt de repere, combien de temps afficher save icon

        # style & positioning
        self.blinking_freq = 7  # nb frames before blink
        self.colorpal = kengi.pal.c64
        pal2 = kengi.pal.punk
        self._editor_bgcolor = pal2['darkblue']
        self._code_bgcolor = pal2['darkblue']
        self.color_textcode = self.colorpal['lightblue']

        self.codespace_ij_pos = (5, 1)
        self.codestart_ij_pos = (5, 1)

        # * WARNING webctx editor will crash if this isnt properly set *
        char_sz = 12
        self.codespace_nbcolumns = int(kengi.defs.STD_SCR_SIZE[0] / char_sz) - 6  # instead of 80 (960/12)
        self.codespace_nbrows = int(kengi.defs.STD_SCR_SIZE[1] / char_sz) - 2 - 1  # instead of 60 (720/12)
        # -2 due to border
        # -1 so we can display the info status msg AS WELL

        kengi.ascii.set_char_size(char_sz)

        # -------
        # hackin the ol' model so we can use it without changes, but with the ASCIIkind of view
        # -------
        self._mod.yline_start_offset = char_sz * self.codestart_ij_pos[
            1]  # bc it adds an offset for y coords on the screen
        self._mod.letter_size_X = char_sz  # TODO should use a parameter instead of hacking, like this
        self._mod.letter_size_Y = char_sz
        self._mod.line_gap = char_sz
        self._mod.xline_start_offset = self.codestart_ij_pos[0] * char_sz
        self._mod.editor_offset_X = 0
        self._mod.showable_line_numbers_in_editor = self.codespace_nbrows
        self._mod.reset_cursor()

        # for faster display, let's pre-compute some stuff
        bg_left, bg_top = ascii_canvas.cpos_to_screen(self.codespace_ij_pos)
        bg_width, bg_height = self.codespace_nbcolumns, self.codespace_nbrows
        bg_width *= char_sz
        bg_height *= char_sz
        self._code_rect = (bg_left, bg_top, bg_width, bg_height)

        # other
        self.flag_show_carret = True
        self.curr_cycle = 0

        # extra
        self.icosurf = pygame.image.load('myassets/saveicon.png')
        saveicon_size = self.icosurf.get_size()
        scr_size = kengi.get_surface().get_size()
        self.icosurf_pos = ((scr_size[0] - saveicon_size[0]) // 2, (scr_size[1] - saveicon_size[1]) // 2)

    # --------------------------------------
    #  handle events
    # --------------------------------------
    def proc_event(self, ev, source):
        if ev.type == pygame.KEYDOWN:
            self._proc_keystroke(ev)

        elif ev.type == pygame.QUIT:
            TextEditorAsciiV._exit_sig()

        elif ev.type == EngineEvTypes.LOGICUPDATE:
            self.latest_t = ev.curr_t
            self.curr_cycle = (self.curr_cycle + 1) % self.blinking_freq
            if not self.curr_cycle:
                self.flag_show_carret = not self.flag_show_carret

        elif ev.type == EngineEvTypes.PAINT:
            # ev.screen.fill((0,0,0))
            ascii_canvas.reset()

            ev.screen.fill(self._editor_bgcolor)
            self._render_leftbox(ev.screen)  # TODO make box disappear if editor no-show-line toggled
            self._render_line_num(ev.screen)

            # render the txt msg
            _, bsupy = kengi.ascii.get_bounds()
            for k, car in enumerate('{ '+self._mod.status_info_msg+' }'):
                ascii_canvas.put_char(car, [7 + k, bsupy-1], kengi.pal.c64['lightgreen'])

            self._render_codeblock(ev.screen)

            if self.flag_show_carret:
                self._render_carret()

            ascii_canvas.flush()  # commit chages to ASCIIcanvas, as its a buffered mechanism

            # render save icon, if useful
            if sharedstuff.disp_save_ico is not None:
                ev.screen.blit(self.icosurf, self.icosurf_pos)
                if (self.latest_t is not None) and self.latest_t > sharedstuff.disp_save_ico:
                    sharedstuff.disp_save_ico = None

            # ! the kengi.flip op will be handled in the game_update func

    @staticmethod
    def _exit_sig():
        sharedstuff.kartridge_output = [2, 'niobepolis']

    def _try_save_file(self, target_kart_id):
        if (target_kart_id is None) or self.locked_file:
            print('BLOCK: not allowed to write')
        else:
            print('SAVE FILE: ', )
            # show save icon:
            sharedstuff.disp_save_ico = self.latest_t + SHOW_ICON_DURAT

            sharedstuff.dump_content = self._mod.get_text_as_string()

    def _proc_keystroke(self, ev_obj):
        ve = pygame.key.get_pressed()
        uholding_ctrl = ve[pygame.K_LCTRL] or ve[pygame.K_RCTRL]

        # - special keys: enter, escape, backspace, delete
        if ev_obj.key == pygame.K_RETURN or ev_obj.key == pygame.K_KP_ENTER:
            if not self.locked_file:
                self._mod.handle_keyboard_return()
        elif ev_obj.key == pygame.K_ESCAPE:
            TextEditorAsciiV._exit_sig()
        elif ev_obj.unicode == '\x08':  # backspace
            if not self.locked_file:
                self._mod.handle_keyboard_backspace()
                self._mod.reset_text_area_to_caret()
        elif ev_obj.unicode == '\x7f':  # del
            if not self.locked_file:
                self._mod.handle_keyboard_delete()
                self._mod.reset_text_area_to_caret()

        # - ctrl + key (a, x, c, v, s, z)
        elif uholding_ctrl and ev_obj.key == pygame.K_a:
            self._mod.highlight_all()
        elif uholding_ctrl and ev_obj.key == pygame.K_x:
            print('sig cut')
            if not self.locked_file:
                self._mod.handle_highlight_and_cut()
        elif uholding_ctrl and ev_obj.key == pygame.K_c:
            print('sig copy')
            self._mod.handle_highlight_and_copy()
        elif uholding_ctrl and ev_obj.key == pygame.K_v:
            print('sig paste')
            if not self.locked_file:
                self._mod.handle_highlight_and_paste()
        elif uholding_ctrl and ev_obj.key == pygame.K_s:
            # ds tous les cas faut refresh
            if katasdk.vmstate:  # RUN WITHOUT a vm
                self._try_save_file(katasdk.vmstate.cedit_arg)
            else:
                # TODO need to refresh so we re-split if the user has entered a new comment in the form # >>>myfile.py
                pass

        elif uholding_ctrl and ev_obj.key == pygame.K_d:  # charge contenu de thing.py
            self._mod.switch_file()

        elif uholding_ctrl and ev_obj.key == pygame.K_z:
            print('undo not implemented yet!')  # TODO

        # - arrow keys
        elif ev_obj.key == pygame.K_UP:
            self._mod.handle_keyboard_arrow_up()
        elif ev_obj.key == pygame.K_DOWN:
            self._mod.handle_keyboard_arrow_down()
        elif ev_obj.key == pygame.K_RIGHT:
            self._mod.handle_keyboard_arrow_right()
        elif ev_obj.key == pygame.K_LEFT:
            self._mod.handle_keyboard_arrow_left()

        # - input text
        elif not self.locked_file:
            if ev_obj.unicode in (' ', '_'):
                self._mod.insert_unicode(ev_obj.unicode)
            elif len(pygame.key.name(ev_obj.key)) == 1:  # normal keys
                self._mod.insert_unicode(ev_obj.unicode)

    def get_single_color_dicts(self, chosencolor):
        rendering_list = []
        for line in self._mod.line_string_list:
            # appends a single-item list
            rendering_list.append([{'chars': line, 'type': 'normal', 'color': chosencolor}])
        return rendering_list

    def _render_leftbox(self, scr):
        bsupx, bsupy = kengi.ascii.get_bounds()
        bsupy -= 1
        limite_boitex = self.codespace_ij_pos[0]
        _ac = ascii_canvas
        col = self.color_textcode
        # ordre:
        # barre horz haut, ligne vert, barre horz bas, ligne vert remontant sens des aiguilles
        for i in range(1, limite_boitex - 1):
            _ac.put_char(_ac.CODE_LINE_HORZ, [i, 0], col)
        for j in range(1, bsupy - 1):
            _ac.put_char(_ac.CODE_LINE_VERT, [-1 + limite_boitex, j], col)
        for i in range(1, limite_boitex - 1):
            _ac.put_char(_ac.CODE_LINE_HORZ, [i, bsupy - 1], col)
        for j in range(1, bsupy - 1):
            _ac.put_char(_ac.CODE_LINE_VERT, [0, j], col)
        # add edges, clockwise, starting topleft
        _ac.put_char(_ac.CODE_LINE_NW, [0, 0], col)
        _ac.put_char(_ac.CODE_LINE_NE, [limite_boitex - 1, 0], col)
        _ac.put_char(_ac.CODE_LINE_SE, [limite_boitex - 1, bsupy - 1], col)
        _ac.put_char(_ac.CODE_LINE_SW, [0, bsupy - 1], col)

        for i in range(0, bsupx):
            _ac.put_char(_ac.CODE_FILL, [i, bsupy], kengi.pal.punk[4])

    def _render_line_num(self, scr):
        if self._mod.displayLineNumbers:
            # redraw at each frame, for convenience (simple algo)
            # if self._mod.rerenderLineNumbers:
            self._mod.rerenderLineNumbers = False
            ybaseline = self.codestart_ij_pos[1]

            lastnum = self._mod.showStartLine + self.codespace_nbrows
            if lastnum > self._mod.get_card_lines():
                lastnum = self._mod.get_card_lines()
            cpt = 0
            for num in range(self._mod.showStartLine, lastnum+1):
                if cpt > 0:
                    nb_str_form = list('{: 3}'.format(num))
                    for i, single_ch in enumerate(nb_str_form):
                        ascii_canvas.put_char(
                            single_ch, [1+i, cpt],
                            kengi.pal.c64['lightgreen']
                        )
                cpt += 1

    def _render_codeblock(self, scr):
        # - background for the codeblock (fill the background of the editor with one color)
        pygame.draw.rect(scr, self._code_bgcolor, self._code_rect)

        # - render content
        list_of_dicts = self.get_single_color_dicts(self.color_textcode)
        # Actual line rendering based on dict-keys

        # - prep properly the display range
        first_line = self._mod.showStartLine
        ultimate_line_rank = self._mod.get_card_lines()
        last_line = first_line + self.codespace_nbrows
        if last_line > ultimate_line_rank:
            last_line = ultimate_line_rank

        basecolumn = self.codestart_ij_pos[0]
        self.yline = self.codestart_ij_pos[1]
        for line_list in list_of_dicts[first_line:last_line]:
            # - new code by tom (ascii console)
            for a_dict in line_list:
                for k, letter in enumerate(a_dict['chars']):
                    # signature: putchar(identifier, canvas pos, fg_col, bg_col)
                    ascii_canvas.put_char(letter, [basecolumn + k, self.yline], a_dict['color'])
            self.yline += 1

    def _render_carret(self):
        # test can we use these variables instead of cursorX, cursorY
        cpos = [self._mod.chosen_LetterIndex, self._mod.chosen_LineIndex]
        cpos[0] += self.codestart_ij_pos[0]
        cpos[1] += self.codestart_ij_pos[1]
        # ij = self._mod.let
        # cpos = ascii_canvas.screen_to_cpos((self._mod.cursor_X, self._mod.cursor_Y))
        ascii_canvas.put_char(kengi.ascii.CODE_FILL, (cpos[0],cpos[1]-self._mod.showStartLine), self.colorpal['white'])
# ----------------------------
#  end editor view
# ----------------------------
