import katagames_sdk as katasdk
import sharedstuff


kengi = katasdk.kengi
pygame = kengi.pygame
EngineEvTypes = kengi.event.EngineEvTypes


class TextEditorAsciiV(kengi.event.EventReceiver):
    def __init__(self, ref_mod, maxfps):
        super().__init__()
        self._mod = ref_mod
        self._maxfps = maxfps

        # style & positioning
        self.blinking_freq = 11  # eleven frames before blink
        self.colorpal = kengi.palettes.c64
        self._editor_bgcolor = self.colorpal['lightblue']
        self._code_bgcolor = self.colorpal['blue']
        kengi.ascii.set_char_size(10)
        self.codespace_ij_pos = (3, 0)
        self.codestart_ij_pos = (3, 0)

        # * WARNING webctx editor will crash if this isnt properly set *
        char_sz = 12
        self.codespace_nbcolumns = int(kengi.defs.STD_SCR_SIZE[0]/char_sz) - 1  # instead of 80 (960/12)
        self.codespace_nbrows = int(kengi.defs.STD_SCR_SIZE[1]/char_sz) - 1  # instead of 60 (720/12)

        self.flag_show_carret = True
        self.curr_cycle = 0
        self._ascii_canvas = kengi.ascii.Acanvas()

    # --------------------------------------
    #  handle events
    # --------------------------------------
    def proc_event(self, ev, source):
        if ev.type == pygame.QUIT:
            sharedstuff.kartridge_output = [2, 'niobepolis']

        elif ev.type == EngineEvTypes.LOGICUPDATE:
            self.curr_cycle += 1
            if self.curr_cycle > self.blinking_freq:
                self.curr_cycle = 0
                self.flag_show_carret = not self.flag_show_carret

        elif ev.type == EngineEvTypes.PAINT:
            self._render_line_num(ev.screen)
            self._render_codeblock(ev.screen)
            self._render_carret()
            kengi.flip()

        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
                self._mod.handle_keyboard_return()

            # backspace or delete
            elif ev.unicode == '\x08':
                self._mod.handle_keyboard_backspace()
                self._mod.reset_text_area_to_caret()
            elif ev.unicode == '\x7f':
                self._mod.handle_keyboard_delete()
                self._mod.reset_text_area_to_caret()

            elif ev.key == pygame.K_UP:
                self._mod.handle_keyboard_arrow_up()
            elif ev.key == pygame.K_DOWN:
                self._mod.handle_keyboard_arrow_down()
            elif ev.key == pygame.K_RIGHT:
                self._mod.handle_keyboard_arrow_right()
            elif ev.key == pygame.K_LEFT:
                self._mod.handle_keyboard_arrow_left()

            elif ev.unicode in (' ', '_'):
                self._mod.insert_unicode(ev.unicode)
            elif len(pygame.key.name(ev.key)) == 1:  # normal keys
                self._mod.insert_unicode(ev.unicode)

    def get_single_color_dicts(self, chosencolor):
        rendering_list = []
        for line in self._mod.line_string_list:
            # appends a single-item list
            rendering_list.append([{'chars': line, 'type': 'normal', 'color': chosencolor}])
        return rendering_list

    def _render_codeblock(self, scr):
        # - background for the codeblock (fill the background of the editor with one color)
        # bg_left = self._mod.editor_offset_X + self._mod.lineNumberWidth
        # bg_top = self._mod.editor_offset_Y
        bg_left, bg_top = self._ascii_canvas.cpos_to_screen(self.codespace_ij_pos)
        bg_width, bg_height = self.codespace_nbcolumns, self.codespace_nbrows
        bg_width *= kengi.ascii.get_char_size()
        bg_height *= kengi.ascii.get_char_size()
        # bg_width = self._mod.textAreaWidth - self._mod.lineNumberWidth
        # bg_height = self._mod.textAreaHeight
        pygame.draw.rect(scr, self._code_bgcolor, (bg_left, bg_top, bg_width, bg_height))

        # - render content
        list_of_dicts = self.get_single_color_dicts(self.colorpal['lightblue'])
        # Actual line rendering based on dict-keys

        # - prep properly the display range
        first_line = self._mod.showStartLine
        ultimate_line_rank = self._mod.get_card_lines()
        last_line = first_line + self.codespace_nbrows
        if last_line > ultimate_line_rank:
            last_line = ultimate_line_rank

        # old:
        # self.yline = 0
        # new:
        basecolumn = self.codestart_ij_pos[0]
        self.yline = self.codestart_ij_pos[1]
        for line_list in list_of_dicts[first_line:last_line]:
            # - old code:
            # xcoord = self._mod.xline_start
            # for a_dict in line_list:
            #     surface = self._mod.currentfont.render(
            #         a_dict['chars'], self._mod.txt_antialiasing, a_dict['color']
            #     )
            #     scr.blit(surface, (xcoord, self.yline))
            #     xcoord = xcoord + (len(a_dict['chars']) * self._mod.letter_size_X)  # next line-part prep
            # self.yline += self._mod.line_gap  # next line prep

            # - new code by tom (ascii console)
            for a_dict in line_list:
                for k, letter in enumerate(a_dict['chars']):
                    # signature: putchar(identifier, canvas pos, fg_col, bg_col)
                    self._ascii_canvas.put_char(letter, [basecolumn + k, self.yline], a_dict['color'])
            self.yline += 1

    def _render_line_num(self, scr):
        if self._mod.displayLineNumbers:
            if self._mod.rerenderLineNumbers:
                scr.fill(self._editor_bgcolor)
                self._mod.rerenderLineNumbers = False
                ybaseline = self.codestart_ij_pos[1]

                lastnum = self._mod.showStartLine + self.codespace_nbrows
                if lastnum > self._mod.get_card_lines():
                    lastnum = self._mod.get_card_lines()

                cpt = 0
                for num in range(self._mod.showStartLine+1, 1+lastnum+self._mod.showStartLine):
                    nb_str_form = list('{: 3}'.format(num))
                    for i, single_ch in enumerate(nb_str_form):
                        self._ascii_canvas.put_char(single_ch, [1+i, cpt], kengi.palettes.c64['blue'])
                    cpt += 1
        else:
            scr.fill(self._editor_bgcolor)

    def _render_carret(self):
        if self.flag_show_carret:
            cpos = self._ascii_canvas.screen_to_cpos((8+self._mod.cursor_X, self._mod.cursor_Y))

            self._ascii_canvas.put_char(kengi.ascii.CODE_FILL, cpos, self.colorpal['white'])
