"""
Warning: this is the precursor so it needs to stay in one single file,
if you need to tinker with stuff, the recommanded procedure is:
 - First re-use/update other files,
 - then test and fine tune
 - then update the current file
"""
import math
import re
import katagames_sdk as katasdk


katasdk.bootstrap()
FOLDER_CART = 'cartridges'


class Sharedstuff:
    def __init__(self):
        self.disp_save_ico = None  # contains info 'bout time when it needs display
        self.dump_content = None
        self.kartridge_output = None
        self.screen = None
        self.file_label = None  # for showing what is being edited


# - gl. variables
kengi = katasdk.kengi
ascii_canvas = kengi.ascii
EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame
glclock = pygame.time.Clock()
ticker = None
editor_text_content = ''
formatedtxt_obj = None
sharedstuff = Sharedstuff()

# - constants
MFPS = 50
SAVE_ICO_LIFEDUR = 1.33  # sec

# constant to have smth just like "lorem ipsum" text, if needed
DUMMY_PYCODE = """# Define the cloud object by extending pygame.sprite.Sprite
# Use an image for a better-looking sprite
class Cloud(pygame.sprite.Sprite):
    def __init__(self):
        super(Cloud, self).__init__()
        self.surf = pygame.image.load("cloud.png").convert()
        self.surf.set_colorkey((0, 0, 0), RLEACCEL)
        # The starting position is randomly generated
        self.rect = self.surf.get_rect(
            center=(
                random.randint(SCREEN_WIDTH + 20, SCREEN_WIDTH + 100),
                random.randint(0, SCREEN_HEIGHT),
            )
        )
    # Move the cloud based on a constant speed
    # Remove the cloud when it passes the left edge of the screen
    def update(self):
        self.rect.move_ip(-5, 0)
        if self.rect.right < 0:
            self.kill()
# >>>megaman.py
for i in range(3, 112):
    for j in range(9, 88):
        print('..', i*j, end='')
# this is a random comment
print('hi mom')
# >>>kappa.py
x = input('hi bro, name? ')
# this is crazy!
print(f"homie {x}")
# >>>alpha.py
print('hello')
"""

# ----------------------------------
#  start editor view
# ---------------------
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

kengi = katasdk.kengi
pygame = kengi.pygame
EngineEvTypes = kengi.event.EngineEvTypes


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


# ----------------------------------
#  start editor
# ----------------------
class TextEditor:
    """
    A priori cette classe est un modèle, mais ça reste assez sale,
    faudrait nettoyer et retirer tt ce qui concerne la vue/controle
    """

    def __init__(self, fileslayout, offset_x, offset_y, text_area_width, text_area_height, line_numbers_flag=False):
        # kengi+sdk flavored font obj
        # TODO passer en param letter size Y
        # self.currentfont = kengi.gui.ImgBasedFont('xxxxassets_editor_myassetsgibson1_font.xxx', (87, 77, 11))
        # self.letter_size_Y = self.currentfont.get_linesize()
        self.letter_size_Y = 12

        # VISUALS
        self.txt_antialiasing = 0
        self.editor_offset_X = offset_x
        self.editor_offset_Y = offset_y
        self.textAreaWidth = text_area_width
        self.textAreaHeight = text_area_height
        self.conclusionBarHeight = 18

        # TODO passer en param lteter size X
        # letter_width = self.currentfont.render(" ", self.txt_antialiasing, (0, 0, 0)).get_width()
        # self.letter_size_X = letter_width
        self.letter_size_X = 12

        # LINES
        self.MaxLinecounter = 0
        self.line_string_list = []  # LOGIC: Array of actual Strings
        self.lineHeight = self.letter_size_Y

        # self.maxLines is the variable keeping count how many lines we currently have -
        # in the beginning we fill the entire editor with empty lines.
        self.maxLines = 20  # int(math.floor(self.textAreaHeight / self.lineHeight))
        self.showStartLine = 0  # first line (shown at the top of the editor) <- must be zero during init!

        linespacing = 2
        self.line_gap = self.letter_size_Y + linespacing
        # how many lines to show
        self.showable_line_numbers_in_editor = int(math.floor(self.textAreaHeight / self.line_gap)) - 1

        for i in range(self.maxLines):  # from 0 to maxLines:
            self.line_string_list.append("")  # Add a line

        # SCROLLBAR
        self.scrollBarWidth = 8  # must be an even number
        self.scrollbar: pygame.Rect = None
        self.scroll_start_y: int = 0
        self.scroll_dragging: bool = False

        # LINE NUMBERS
        self.displayLineNumbers = line_numbers_flag
        if self.displayLineNumbers:
            self.lineNumberWidth = 35  # line number background width and also offset for text!
        else:
            self.lineNumberWidth = 0
        self.line_numbers_Y = self.editor_offset_Y

        # TEXT COORDINATES
        self.chosen_LineIndex = 0
        self.chosen_LetterIndex = 0
        self.yline_start = self.editor_offset_Y + 1  # +1 is here so we can align line numbers & txtcontent surfaces

        # self.yline = self.editor_offset_Y
        self.xline_start_offset = 28

        # CURSOR - coordinates for displaying the caret while typing
        self.cursor_Y = self.cursor_X = None
        self.xline = self.xline_start = None
        self.reset_cursor()

        # relates to dragging operation
        self.drag_chosen_LineIndex_start = 0
        self.drag_chosen_LetterIndex_start = 0
        # coordinates used to identify end-point of drag
        self.drag_chosen_LineIndex_end = 0
        self.drag_chosen_LetterIndex_end = 0

        self.lexer = None  # PythonLexer()
        self.formatter = None  # ColorFormatter()
        # there's only dark scheme
        # self.set_colorscheme(style)

        # Key input variables+
        self.key_initial_delay = 300
        self.key_continued_intervall = 30
        pygame.key.set_repeat(self.key_initial_delay, self.key_continued_intervall)

        # flag to tell that line number need to be re-drawn
        self.rerenderLineNumbers = True

        # - update data
        # status info= whats displayed on the very last line editor
        self.status_info_msg = ''

        self.emu_paperclip = ''
        self.fake_layout = fileslayout  # stores an object, instance of FakeProjectLayout
        self.curr_vfile_idx = -1
        self.switch_file()  # so we target 'main.py'

    # -------------- activates when pressed ctrl+d in the TextEditorV -------------
    def switch_file(self):
        self.curr_vfile_idx = (self.curr_vfile_idx + 1) % self.fake_layout.size
        vfilename = self.fake_layout.file_order[self.curr_vfile_idx]
        self.set_text_from_list(self.fake_layout[vfilename])
        self.status_info_msg = f"Editing {vfilename}"

    def reset_cursor(self):
        if self.displayLineNumbers:
            self.xline_start = self.editor_offset_X + self.xline_start_offset
            self.xline = self.editor_offset_X + self.xline_start_offset
        else:
            self.xline_start = self.editor_offset_X
            self.xline = self.editor_offset_X
        self.cursor_Y = self.editor_offset_Y
        self.cursor_X = self.xline_start

    # ++++++++++ Scroll functionality
    def scrollbar_up(self) -> None:
        self.showStartLine -= 1
        self.cursor_Y += self.line_gap
        self.rerenderLineNumbers = True

    def scrollbar_down(self) -> None:
        self.showStartLine += 1
        self.cursor_Y -= self.line_gap
        self.rerenderLineNumbers = True

    # ++++++++++++++++++ editor getters
    def get_line_index(self, mouse_y) -> int:
        """
        Returns possible line-position of mouse -> does not take into account
        how many lines there actually are!
        """
        return int(((mouse_y - self.editor_offset_Y) / self.line_gap) + self.showStartLine)

    def get_letter_index(self, mouse_x) -> int:
        """
        Returns possible letter-position of mouse.

        The function is independent from any specific line, so we could possible return a letter_index which
        is bigger than the letters in the line.
        Returns at least 0 to make sure it is possibly a valid index.
        """
        letter = int((mouse_x - self.xline_start) / self.letter_size_X)
        letter = 0 if letter < 0 else letter
        return letter

    # ++++++++++++++++++++++ Letter operation
    def delete_letter_to_end(self, line, letter) -> None:
        """
        Deletes within a line from a letter by index to the end of the line.
        """
        self.line_string_list[line] = self.line_string_list[line][:letter]

    def delete_start_to_letter(self, line, letter) -> None:
        """
        Deletes within a line from the start of the line to a letter by index..
        """
        self.line_string_list[line] = self.line_string_list[line][letter:]

    def delete_letter_to_letter(self, line, letter_start, letter_end) -> None:
        """
        Deletes within a line from a letter to a letter by index..
        """
        a, b = self.line_string_list[line][:letter_start], self.line_string_list[line][letter_end:]
        self.line_string_list[line] = a + b

    def delete_entire_line(self, line) -> None:
        """
        Deletes an entire line
        """
        self.line_string_list.pop(line)
        self.maxLines -= 1

    def get_entire_line(self, line_index) -> str:
        return self.line_string_list[line_index]

    def get_line_from_start_to_char(self, line_index, char_index) -> str:
        return self.line_string_list[line_index][0:char_index]

    def get_line_from_char_to_end(self, line_index, char_index) -> str:
        return self.line_string_list[line_index][char_index:]

    def get_line_from_char_to_char(self, line_index, char1, char2) -> str:
        if char1 < char2:
            return self.line_string_list[line_index][char1:char2]
        else:
            return self.line_string_list[line_index][char2:char1]

    # ++++++++++++++++++ ??

    def jump_to_start(self, line_start, line_end, letter_start, letter_end) -> None:
        """
        Chosen LineIndex set to start of highlighted area
        """
        if line_start <= line_end:
            # downward highlight or the same line
            self.chosen_LineIndex = line_start
            self.chosen_LetterIndex = letter_start
        else:  # upward highlight
            self.chosen_LineIndex = line_end
            self.chosen_LetterIndex = letter_end

    def jump_to_end(self, line_start, line_end, letter_start, letter_end) -> None:
        """
        Chosen LineIndex set to end of highlighted area
        """
        if line_start <= line_end:
            # downward highlight or the same line
            self.chosen_LineIndex = line_end
            self.chosen_LetterIndex = letter_end
        else:  # upward highlight
            self.chosen_LineIndex = line_start
            self.chosen_LetterIndex = letter_start

    def reset_after_highlight(self) -> None:
        """
        Reset caret, clickdown_cycles and dragged booleans.
        """
        self.dragged_active = False  # deactivate highlight
        self.dragged_finished = True  # highlight is finished
        self.last_clickdown_cycle = 0  # reset drag-cycle
        self.last_clickup_cycle = -1

        self.update_caret_position()  # update caret position to chosen_Index (Line+Letter)
        self.rerenderLineNumbers = True

        if len(self.line_string_list) <= self.showable_line_numbers_in_editor:
            self.showStartLine = 0  # update first showable line

    def get_number_of_letters_in_line_by_mouse(self, mouse_y) -> int:
        line_index = self.get_line_index(mouse_y)
        return self.get_number_of_letters_in_line_by_index(line_index)

    def get_number_of_letters_in_line_by_index(self, index) -> int:
        return len(self.line_string_list[index])

    def get_showable_lines(self) -> int:
        """
        Return the number of lines which are shown. Less than maximum if less lines are in the array.
        """
        if self.showable_line_numbers_in_editor + self.showStartLine < self.maxLines:
            return self.showable_line_numbers_in_editor + self.showStartLine
        else:
            return self.maxLines

    def line_is_visible(self, line) -> bool:
        """
        Calculate whether the line is being shown in the editor
        """
        return self.showStartLine <= line < self.showStartLine + self.showable_line_numbers_in_editor

    # files for customization of the editor:
    # from ._customization import set_colorscheme

    def mouse_within_texteditor(self, mouse_x, mouse_y) -> bool:
        """
        Returns True if the given coordinates are within the text-editor area of the pygame window, otherwise False.
        """
        a = self.editor_offset_X + self.lineNumberWidth < mouse_x < \
            (self.editor_offset_X + self.textAreaWidth - self.scrollBarWidth)
        b = self.editor_offset_Y < mouse_y < \
            (self.textAreaHeight + self.editor_offset_Y - self.conclusionBarHeight)
        return a and b

    def mouse_within_existing_lines(self, mouse_y):
        """
        Returns True if the given Y-coordinate is within the height of the text-editor's existing lines.
        Returns False if the coordinate is below existing lines or outside of the editor.
        """
        return self.editor_offset_Y < mouse_y < self.editor_offset_Y + (self.lineHeight * self.maxLines)

    # +++++++++++++++++++ caret
    def set_drag_start_by_mouse(self, mouse_x, mouse_y) -> None:
        # get line
        # print('in drag ', mouse_x, mouse_y)
        self.drag_chosen_LineIndex_start = self.get_line_index(mouse_y)

        # end of line
        if self.get_number_of_letters_in_line_by_mouse(mouse_y) < self.get_letter_index(mouse_x):
            self.drag_chosen_LetterIndex_start = len(self.line_string_list[self.drag_chosen_LineIndex_start])

        else:  # within existing line
            self.drag_chosen_LetterIndex_start = self.get_letter_index(mouse_x)

    def set_drag_end_by_mouse(self, mouse_x, mouse_y) -> None:
        """
        Compact method to set both line and letter of drag_end based on mouse coordinates.
        """
        # set line
        self.set_drag_end_line_by_mouse(mouse_y)
        # set letter
        self.set_drag_end_letter_by_mouse(mouse_x)

    def set_drag_end_line_by_mouse(self, mouse_y) -> None:
        """
        Sets self.drag_chosen_LineIndex_end by mouse_y.
        """
        self.drag_chosen_LineIndex_end = self.get_line_index(mouse_y)

    def set_drag_end_letter_by_mouse(self, mouse_x) -> None:
        """
        Sets self.drag_chosen_LetterIndex_end by mouse_x.
        Dependent on self.drag_chosen_LineIndex_end.
        """
        # end of line
        if self.get_letter_index(mouse_x) > self.get_number_of_letters_in_line_by_index(self.drag_chosen_LineIndex_end):
            self.drag_chosen_LetterIndex_end = len(self.line_string_list[self.drag_chosen_LineIndex_end])
        else:  # within existing line
            self.drag_chosen_LetterIndex_end = self.get_letter_index(mouse_x)

    def set_drag_start_after_last_line(self) -> None:
        # select last line
        self.drag_chosen_LineIndex_start = self.maxLines - 1
        # select last letter of the line
        self.drag_chosen_LetterIndex_start = len(self.line_string_list[self.drag_chosen_LineIndex_start])

    def set_drag_start_before_first_line(self) -> None:
        self.drag_chosen_LineIndex_start = 0
        self.drag_chosen_LetterIndex_start = 0

    def set_drag_end_after_last_line(self) -> None:
        # select last line
        self.drag_chosen_LineIndex_end = self.maxLines - 1
        # select last letter of the line
        self.drag_chosen_LetterIndex_end = len(self.line_string_list[self.drag_chosen_LineIndex_end])

    def update_caret_position_by_drag_start(self) -> None:
        """
        # Updates cursor_X and cursor_Y positions based on the start position of a dragging operation.
        """
        print('update by drag start', self.cursor_X, self.cursor_Y)
        # X Position
        self.cursor_X = self.xline_start + (self.drag_chosen_LetterIndex_start * self.letter_size_X)
        # Y Position
        self.cursor_Y = self.editor_offset_Y
        self.cursor_Y += self.drag_chosen_LineIndex_start * self.line_gap
        self.cursor_Y -= self.showStartLine * self.lineHeight
        print(self.cursor_X, self.cursor_Y)

    def update_caret_position_by_drag_end(self) -> None:
        """
        # Updates cursor_X and cursor_Y positions based on the end position of a dragging operation.
        """
        # X Position
        self.cursor_X = self.xline_start + (self.drag_chosen_LetterIndex_end * self.letter_size_X)
        # Y Position
        self.cursor_Y = self.editor_offset_Y
        self.cursor_Y += (self.drag_chosen_LineIndex_end * self.line_gap)
        self.cursor_Y -= (self.showStartLine * self.lineHeight)

    def update_caret_position(self) -> None:
        """
        # Updates cursor_X and cursor_Y positions based on current position by line and letter indices
        """
        self.cursor_X = self.xline_start + (self.chosen_LetterIndex * self.letter_size_X)
        self.cursor_Y = self.editor_offset_Y
        self.cursor_Y += (self.chosen_LineIndex * self.line_gap)
        self.cursor_Y -= self.showStartLine * self.lineHeight

    # letter operations (delete, get)
    # rendering (basic, highlighting, syntax coloring)
    # from ._rendering import render_line_contents_by_dicts, \
    #     render_caret, render_background_coloring, render_line_numbers
    # from ._rendering_highlighting import render_highlight

    def set_line_numbers(self, b) -> None:
        """
        Activates/deactivates showing the line numbers in the editor
        """
        self.displayLineNumbers = b
        if self.displayLineNumbers:
            self.lineNumberWidth = 35  # line number background width and also offset for text!
            self.xline_start = self.editor_offset_X + self.xline_start_offset
            self.xline = self.editor_offset_X + self.xline_start_offset
        else:
            self.lineNumberWidth = 0
            self.xline_start = self.editor_offset_X
            self.xline = self.editor_offset_X

    # 2 method aliases: ALLOWS one to bind keyboard scrolling to pre-existing scrollbar controls...
    def scroll_up(self):
        self.scrollbar_up()

    def scroll_down(self):
        self.scrollbar_down()

    def get_card_lines(self):
        return len(self.line_string_list)

    def highlight_lines(self, line_start, letter_start, line_end, letter_end) -> None:
        """
        Highlights multiple lines based on indizies of starting & ending lines and letters.
        """
        if line_start == line_end:  # single-line highlight
            self.highlight_from_letter_to_letter(line_start, letter_start, letter_end)
        else:  # multi-line highlighting
            if line_start > line_end:  # swap variables based on up/downward highlight to make code more readable
                line_start, line_end = line_end, line_start
                letter_start, letter_end = letter_end, letter_start

            for i, line_number in enumerate(range(line_start, line_end + 1)):  # for each line
                if i == 0:  # first line
                    self.highlight_from_letter_to_end(line_number, letter_start)  # right leaning highlight
                elif i < len(range(line_start, line_end)):  # middle line
                    self.highlight_entire_line(line_number)
                else:  # last line
                    self.highlight_from_start_to_letter(line_number, letter_end)  # left leaning highlight

    def highlight_from_letter_to_end(self, line, letter) -> None:
        """
        Highlight from a specific letter by index to the end of a line.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, letter)
            x2, y2 = self.get_rect_coord_from_indizes(line, len(self.line_string_list[line]))
            pygame.draw.rect(kengi.get_surface(), (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def highlight_from_start_to_letter(self, line, letter) -> None:
        """
        Highlight from the beginning of a line to a specific letter by index.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, 0)
            x2, y2 = self.get_rect_coord_from_indizes(line, letter)
            pygame.draw.rect(kengi.get_surface(), (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def highlight_entire_line(self, line) -> None:
        """
        Full highlight of the entire line - first until last letter.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, 0)
            x2, y2 = self.get_rect_coord_from_indizes(line, len(self.line_string_list[line]))
            pygame.draw.rect(kengi.get_surface(), (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def highlight_from_letter_to_letter(self, line, letter_start, letter_end) -> None:
        """
        Highlights within a single line from letter to letter by indizes.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, letter_start)
            x2, y2 = self.get_rect_coord_from_indizes(line, letter_end)
            pygame.draw.rect(kengi.get_surface(), (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def caret_within_texteditor(self) -> bool:
        """
        Tests whether the caret's coordinates are within the visible text area.
        If the caret can possibly be in a line which is not currently displayed after using the mouse wheel for
        scrolling. Test for 'self.editor_offset_Y <= self.cursor_Y' as the caret can have the exact same Y-coordinate
        as the offset if the caret is in the first line.
        """
        ox, oy = self.editor_offset_X, self.editor_offset_Y
        cond1 = ox + self.lineNumberWidth < self.cursor_X < (ox + self.textAreaWidth - self.scrollBarWidth - 2)
        cond2 = oy <= self.cursor_Y < (self.textAreaHeight + oy - self.conclusionBarHeight)
        return cond1 and cond2

    def get_rect_coord_from_mouse(self, mouse_x, mouse_y) -> (int, int):
        """
        Return x and y pixel-coordinates for the position of the mouse.
        """
        line = self.get_line_index(mouse_y)
        letter = self.get_letter_index(mouse_x)
        return self.get_rect_coord_from_indizes(line, letter)

    def get_rect_coord_from_indizes(self, line, letter) -> (int, int):
        """
        Return x and y pixel-coordinates for line and letter by index.
        """
        line_coord = self.editor_offset_Y + (self.line_gap * (line - self.showStartLine))
        letter_coord = self.xline_start + (letter * self.letter_size_X)
        return letter_coord, line_coord

    def reset_text_area_to_caret(self) -> None:
        """
        Reset visual area to include the line of caret if it is currently not visible. This function ensures
        that whenever we type, the line in which the caret resides becomes visible, even after scrolling.
        """
        if self.chosen_LineIndex < self.showStartLine:  # above visible area
            self.showStartLine = self.chosen_LineIndex
            self.rerenderLineNumbers = True
            self.update_caret_position()
        elif self.chosen_LineIndex > (
                self.showStartLine + self.showable_line_numbers_in_editor - 1):  # below visible area
            self.showStartLine = self.chosen_LineIndex - self.showable_line_numbers_in_editor + 1
            self.rerenderLineNumbers = True
            self.update_caret_position()
        # next possible enhancement: set cursor coordinates

    # ++++++++++++++++++++++ usage, N.B. this should be in a model class
    def get_text_as_string(self) -> str:
        """
        Returns the entire text of the editor as a single string.
        Linebreak characters are used to differentiate between lines.
        :param self:  Texteditor-Class
        :return: String
        """
        return "\n".join(self.line_string_list)

    def get_text_as_list(self):  # -> List
        """
        Returns the text in it's logical form as a list of lines.
        :param self:  Texteditor-Class
        :return: List of lines containing the text. Lines cane be empty Strings.
        """
        return self.line_string_list

    def clear_text(self):
        """
        Clears the textarea.
        :param self: Texteditor-Class
        :return: None
        """
        self.line_string_list = []  # LOGIC: List of actual Strings for each line
        self.maxLines = int(math.floor(self.textAreaHeight / self.lineHeight))
        self.showStartLine = 0
        for i in range(self.maxLines):  # from 0 to maxLines:
            self.line_string_list.append("")  # Add a line

        # reset caret
        self.firstiteration_boolean = True  # redraws background
        self.rerenderLineNumbers = True
        self.chosen_LineIndex = 0
        self.chosen_LetterIndex = 0
        self.dragged_active = False
        self.dragged_finished = True
        self.scroll_dragging = False
        self.drag_chosen_LineIndex_start = 0
        self.drag_chosen_LetterIndex_start = 0
        self.drag_chosen_LineIndex_end = 0
        self.drag_chosen_LetterIndex_end = 0
        self.last_clickdown_cycle = 0
        self.last_clickup_cycle = 0
        self.cycleCounter = 0
        self.update_caret_position()
        self.cycleCounter = 0

    def set_text_from_list(self, text_list):
        """
        Sets the text of the editor based on a list of strings. Each item in the list represents one line.
        """
        self.clear_text()
        self.line_string_list = text_list
        self.maxLines = len(self.line_string_list)
        self.rerenderLineNumbers = True

    def set_text_from_string(self, string):
        """
        Sets the text of the editor based on a string. Linebreak characters are parsed.
        """
        self.clear_text()
        self.line_string_list = string.splitlines()
        self.maxLines = len(self.line_string_list)
        self.rerenderLineNumbers = True

    def insert_unicode(self, unicode) -> None:
        nl = self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]
        nl += unicode
        nl += self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        self.line_string_list[self.chosen_LineIndex] = nl

        self.chosen_LetterIndex += 1
        self.cursor_X += self.letter_size_X

    def handle_keyboard_backspace(self) -> None:
        if self.chosen_LetterIndex == 0 and self.chosen_LineIndex == 0:
            # First position and in the first Line -> nothing happens
            pass
        elif self.chosen_LetterIndex == 0 and self.chosen_LineIndex > 0:
            # One Line back if at X-Position 0 and not in the first Line

            # set letter and line index to newly current line
            self.chosen_LineIndex -= 1
            self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
            # set visual cursor one line above and at the end of the line
            self.cursor_Y -= self.line_gap
            self.cursor_X = self.xline_start + (len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X)

            # take the rest of the former line into the current line
            x = self.line_string_list[self.chosen_LineIndex] + self.line_string_list[self.chosen_LineIndex + 1]
            self.line_string_list[self.chosen_LineIndex] = x

            # delete the former line
            # LOGICAL lines
            self.remove_subsequent_lines()

            if self.chosen_LineIndex == (self.showStartLine - 1):
                # Im in the first rendered line (but NOT  the "0" line) and at the beginning of the line.
                # => move one upward, change showstartLine & cursor placement.
                self.showStartLine -= 1
                self.cursor_Y += self.line_gap

        elif self.chosen_LetterIndex > 0:
            # mid-line or end of the line -> Delete a letter
            a = self.line_string_list[self.chosen_LineIndex][:(self.chosen_LetterIndex - 1)]
            b = self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
            self.line_string_list[self.chosen_LineIndex] = a + b

            self.cursor_X -= self.letter_size_X
            self.chosen_LetterIndex -= 1
        else:
            raise ValueError("INVALID CONSTRUCT: handle_keyboard_backspace. \
                             \nLine:" + str(self.chosen_LineIndex) + "\nLetter: " + str(self.chosen_LetterIndex))

    def remove_subsequent_lines(self):
        # prev line: delete the Strings-line to move the following lines one upwards
        self.line_string_list.pop(self.chosen_LineIndex + 1)
        self.maxLines -= 1
        # VISUAL lines
        self.rerenderLineNumbers = True

        # Handling of the resulting scrolling functionality of removing one line
        if self.showStartLine > 0:
            if (self.showStartLine + self.showable_line_numbers_in_editor) > self.maxLines:
                # The scrollbar is all the way down. We delete a line,
                # so we have to "pull everything one visual line down"
                self.showStartLine -= 1  # "pull one visual line down" (array-based)
                self.cursor_Y += self.line_gap  # move the curser one down.  (visually based)

    def handle_keyboard_delete(self) -> None:
        if self.chosen_LetterIndex < (len(self.line_string_list[self.chosen_LineIndex])):
            # start of the line or mid-line (Cursor stays on point), cut one letter out
            a = self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]
            b = self.line_string_list[self.chosen_LineIndex][(self.chosen_LetterIndex + 1):]
            self.line_string_list[self.chosen_LineIndex] = a + b

        elif self.chosen_LetterIndex == len(self.line_string_list[self.chosen_LineIndex]):
            # End of a line  (choose next line)
            if self.chosen_LineIndex != (
                    self.maxLines - 1):  # NOT in the last line &(prev) at the end of the line, I cannot delete anything
                self.line_string_list[self.chosen_LineIndex] += self.line_string_list[
                    self.chosen_LineIndex + 1]  # add the contents of the next line to the current one

                self.remove_subsequent_lines()
        else:
            raise ValueError(" INVALID CONSTRUCT: handle_keyboard_delete. \
                             \nLine:" + str(self.chosen_LineIndex) + "\nLetter: " + str(self.chosen_LetterIndex))

    def handle_keyboard_arrow_left(self) -> None:
        if self.chosen_LetterIndex > 0:  # mid-line or end of line
            self.chosen_LetterIndex -= 1
            self.cursor_X -= self.letter_size_X
        elif self.chosen_LetterIndex == 0 and self.chosen_LineIndex == 0:
            # first line, first position, nothing happens
            pass
        # Move over into previous Line (if there is any)
        elif self.chosen_LetterIndex == 0 and self.chosen_LineIndex > 0:
            self.chosen_LineIndex -= 1
            self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])  # end of previous line
            self.cursor_X = self.xline_start + (len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X)
            self.cursor_Y -= self.line_gap
            if self.chosen_LineIndex < self.showStartLine:
                # handling scroll functionality if necessary (moved above shown lines)
                self.showStartLine -= 1
                self.cursor_Y += self.line_gap
                self.rerenderLineNumbers = True

    def handle_keyboard_arrow_right(self) -> None:
        if self.chosen_LetterIndex < (len(self.line_string_list[self.chosen_LineIndex])):
            # mid-line or start of the line
            self.chosen_LetterIndex += 1
            self.cursor_X += self.letter_size_X
        elif self.chosen_LetterIndex == len(self.line_string_list[self.chosen_LineIndex]) and \
                not (self.chosen_LineIndex == (self.maxLines - 1)):
            # end of line => move over into the start of the next line

            self.chosen_LetterIndex = 0
            self.chosen_LineIndex += 1
            self.cursor_X = self.xline_start
            self.cursor_Y += self.line_gap
            if self.chosen_LineIndex > (self.showStartLine + self.showable_line_numbers_in_editor - 1):
                # handling scroll functionality if necessary (moved below showed lines)
                self.showStartLine += 1
                self.cursor_Y -= self.line_gap
                self.rerenderLineNumbers = True

    def handle_keyboard_arrow_down(self) -> None:
        if self.chosen_LineIndex < (self.maxLines - 1):
            # Not in the last line, downward movement possible
            self.chosen_LineIndex += 1
            self.cursor_Y += self.line_gap

            if len(self.line_string_list[self.chosen_LineIndex]) < self.chosen_LetterIndex:
                # reset letter-index to the end
                self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
                self.cursor_X = (len(
                    self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X) + self.xline_start

            if self.chosen_LineIndex > (self.showStartLine + self.showable_line_numbers_in_editor - 1):
                # handle scrolling functionality if necessary (moved below shown lines)
                self.scroll_down()

        elif self.chosen_LineIndex == (self.maxLines - 1):  # im in the last line and want to jump to its end.
            self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])  # end of the line
            self.cursor_X = self.xline_start + (
                    len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X)

    def handle_keyboard_arrow_up(self) -> None:
        if self.chosen_LineIndex == 0:
            # first line, cannot go upwards, so we go to the first position
            self.chosen_LetterIndex = 0
            self.cursor_X = self.xline_start

        elif self.chosen_LineIndex > 0:
            # subsequent lines, upwards movement possible
            self.chosen_LineIndex -= 1
            self.cursor_Y -= self.line_gap

            if len(self.line_string_list[self.chosen_LineIndex]) < self.chosen_LetterIndex:
                # less letters in this line, reset toward the end of the line (to the left)
                self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
                self.cursor_X = (len(
                    self.line_string_list[self.chosen_LineIndex])) * self.letter_size_X + self.xline_start

            if self.chosen_LineIndex < self.showStartLine:  # scroll up one line
                self.scroll_up()

    def handle_keyboard_tab(self) -> None:
        for x in range(0, 4):  # insert 4 spaces
            self.handle_keyboard_space()

    def handle_keyboard_space(self) -> None:
        # insert 1 space
        self.line_string_list[self.chosen_LineIndex] = \
            self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex] + " " + \
            self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]

        self.cursor_X += self.letter_size_X
        self.chosen_LetterIndex += 1

    def handle_keyboard_return(self) -> None:
        # Get "transfer letters" behind cursor up to the end of the line to next line
        # If the cursor is at the end of the line, transferString is an empty String ("")
        transfer_string = self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]

        # Remove transfer letters from the current line
        self.line_string_list[self.chosen_LineIndex] = \
            self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]

        # set logical cursor indizes and add a new line
        self.chosen_LineIndex += 1
        self.chosen_LetterIndex = 0
        self.maxLines += 1
        self.cursor_X = self.xline_start  # reset cursor to start of the line

        # insert empty line
        self.line_string_list.insert(self.chosen_LineIndex, "")  # logical line

        # Edit the new line -> append transfer letters
        self.line_string_list[self.chosen_LineIndex] = self.line_string_list[self.chosen_LineIndex] + transfer_string
        self.rerenderLineNumbers = True

        # handle scrolling functionality
        if self.chosen_LineIndex > (
                self.showable_line_numbers_in_editor - 1):  # Last row, visual representation moves down
            self.showStartLine += 1
        else:  # not in last row, put courser one line down without changing the shown line numbers
            self.cursor_Y += self.line_gap

    # -------------------------------------------------------
    #  ( highligthed) manage keyb
    # -------------------------------------------------------
    def handle_input_with_highlight(self, input_event) -> None:
        """
        Handles key-downs after a drag operation was finished and the highlighted area (drag) is still active.
        For arrow keys we merely jump to the destination.
        For other character-keys we remove the highlighted area and replace it (also over multiple lines)
        with the chosen letter.
        """
        # for readability & maintainability we use shorter variable names
        line_start = self.drag_chosen_LineIndex_start
        line_end = self.drag_chosen_LineIndex_end
        letter_start = self.drag_chosen_LetterIndex_start
        letter_end = self.drag_chosen_LetterIndex_end
        print(line_start, line_end, letter_start, letter_end)

        if self.dragged_finished and self.dragged_active:
            if input_event.key in (pygame.K_DOWN, pygame.K_UP, pygame.K_RIGHT, pygame.K_LEFT):
                # deselect highlight
                if input_event.key == pygame.K_DOWN:
                    self.jump_to_end(line_start, line_end, letter_start, letter_end)
                elif input_event.key == pygame.K_UP:
                    self.jump_to_start(line_start, line_end, letter_start, letter_end)
                elif input_event.key == pygame.K_RIGHT:
                    self.jump_to_end(line_start, line_end, letter_start, letter_end)
                elif input_event.key == pygame.K_LEFT:
                    self.jump_to_start(line_start, line_end, letter_start, letter_end)
                self.reset_after_highlight()

            elif input_event.key in (
                    pygame.K_RSHIFT, pygame.K_LSHIFT, pygame.K_CAPSLOCK, pygame.K_RCTRL, pygame.K_LCTRL, pygame.K_ESCAPE
            ):
                pass  # nothing happens, we wait for the second key with which it is being used in combination

            else:  # other key -> delete highlighted area and insert key (if not esc/delete)
                if line_start == line_end:  # delete in single line
                    if letter_start > letter_end:  # swap variables based on left/right highlight to mk code readable
                        letter_start, letter_end = letter_end, letter_start
                    self.delete_letter_to_letter(line_start, letter_start, letter_end)

                else:  # multi-line delete
                    if line_start > line_end:  # swap variables based on up/downward highlight to mk code readable
                        line_start, line_end = line_end, line_start
                        letter_start, letter_end = letter_end, letter_start

                    for i, line_number in enumerate(range(line_start, line_end + 1)):
                        if i == 0:  # first line
                            self.delete_letter_to_end(line_start, letter_start)  # delete right side from start
                        elif i < (line_end - line_start):
                            self.delete_entire_line(
                                line_start + 1)  # stays at line_start +1 as we delete on the fly (!)
                        else:  # last line
                            self.delete_start_to_letter(line_start + 1, letter_end)  # delete left side of new last line

                    # join rest of start/end lines into new line in multiline delete
                    xx = self.line_string_list[line_start] + self.line_string_list[line_start + 1]
                    self.line_string_list[line_start] = xx
                    self.delete_entire_line(line_start + 1)  # after copying contents, we need to delete the other line

                # set caret and rerender line_numbers
                self.chosen_LineIndex = line_start if line_start <= line_end else line_end  # start for single_line
                self.chosen_LetterIndex = letter_start if line_start <= line_end else letter_end
                self.rerenderLineNumbers = True
                self.reset_after_highlight()

                # insert key unless delete/backspace
                if input_event.key not in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    self.insert_unicode(input_event.unicode)

    def handle_highlight_and_paste(self):
        """
        Paste clipboard into cursor position.
        Replace highlighted area if highlight, else normal insert.
        """

        # DELETE highlighted section if something is highlighted
        if self.dragged_finished and self.dragged_active:
            delete_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE)  # create artifical delete event
            self.handle_input_with_highlight(delete_event)

        # PASTE from clipboard
        paste_string = self.emu_paperclip
        line_split = paste_string.split("\r\n")  # split into lines
        if len(line_split) == 1:  # no linebreaks
            self.line_string_list[self.chosen_LineIndex] = \
                self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex] \
                + line_split[0] + \
                self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]

            self.chosen_LetterIndex = self.chosen_LetterIndex + len(line_split[0])

        else:
            rest_of_line = self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]  # store for later
            for i, line in enumerate(line_split):
                if i == 0:  # first line to insert
                    self.line_string_list[self.chosen_LineIndex] = \
                        self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex] + line
                elif i < len(line_split) - 1:  # middle line -> insert new line!
                    self.line_string_list[self.chosen_LineIndex + i: self.chosen_LineIndex + i] = [line]
                    self.maxLines += 1
                else:  # last line
                    self.line_string_list[self.chosen_LineIndex + i: self.chosen_LineIndex + i] = [line + rest_of_line]
                    self.maxLines += 1

                    self.chosen_LetterIndex = len(line)
                    self.chosen_LineIndex = self.chosen_LineIndex + i

        self.update_caret_position()
        self.rerenderLineNumbers = True

    def handle_highlight_and_copy(self):
        """
        Copy highlighted String into clipboard if anything is highlighted, else no action.
        """
        copy_string = self.get_highlighted_characters()
        self.emu_paperclip = str(copy_string)

    def handle_highlight_and_cut(self):
        """
        Copy highlighted String into clipboard if anything is highlighted, else no action.
        Delete highlighted part of the text.
        """
        # Copy functionality
        copy_string = self.get_highlighted_characters()  # copy characters
        self.emu_paperclip = str(copy_string)

        # Cut / delete functionality
        delete_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE)  # create artifical event
        self.handle_input_with_highlight(delete_event)

        self.update_caret_position()

    def highlight_all(self):
        """
        Highlight entire text.
        """
        # set artifical drag and cursor position
        self.set_drag_start_before_first_line()
        self.set_drag_end_after_last_line()
        self.update_caret_position_by_drag_end()
        # activate highlight
        self.dragged_finished = True
        self.dragged_active = True

    def get_highlighted_characters(self) -> str:
        """
        Returns the highlighted characters (single- and multiple-line) from the editor (self.line_string_list)
        """
        if self.dragged_finished and self.dragged_active:
            line_start = self.drag_chosen_LineIndex_start
            line_end = self.drag_chosen_LineIndex_end
            letter_start = self.drag_chosen_LetterIndex_start
            letter_end = self.drag_chosen_LetterIndex_end

            if self.drag_chosen_LineIndex_start == self.drag_chosen_LineIndex_end:
                # single-line highlight
                return self.get_line_from_char_to_char(self.drag_chosen_LineIndex_start,
                                                       self.drag_chosen_LetterIndex_start,
                                                       self.drag_chosen_LetterIndex_end)

            else:  # multi-line highlight
                if line_start > line_end:  # swap variables based on up/downward highlight to make code more readable
                    line_start, line_end = line_end, line_start
                    letter_start, letter_end = letter_end, letter_start

                # loop through highlighted lines
                copied_chars = ""
                for i, line_index in enumerate(range(line_start, line_end + 1)):
                    if i == 0:  # first line
                        copied_chars = self.get_line_from_char_to_end(line_index, letter_start)
                    elif i < len(range(line_start, line_end)):  # middle line
                        copied_chars = copied_chars + "\r\n" + self.get_entire_line(line_index)
                    else:  # last line
                        copied_chars = copied_chars + "\r\n" + self.get_line_from_start_to_char(line_index, letter_end)

                return copied_chars
        else:
            return ""


# ----------------------------------------------
#   end of editor
# ----------------------------------------------
lu_event = paint_ev = None
e_manager = None


class FakeProjectLayout:
    """
    can use several files, by default its only main.py
    """
    def __init__(self, mashup_code):
        # lets distinguish virtual .py files
        self.files_to_content = dict()
        self.file_order = None
        self._disting_files(mashup_code)

    @property
    def size(self):
        return len(self.file_order)

    def _disting_files(self, rawcode):
        all_lines = rawcode.splitlines()
        #  on généralise pour qu'on puisse gérer plusieurs fichiers et pas que 2,
        #  et que l'on puisse choisir son nom xxx.py au lieu d'avoir choisi thing.py en dur!
        groups = re.findall(r"# >>>(\b[a-z]+\b\.py)", rawcode)

        # find starts
        starts = dict()
        order = list()
        if len(groups):
            for vfilename in groups:
                for k, li in enumerate(all_lines):
                    teststr = f"# >>>{vfilename}"
                    if li == teststr:
                        starts[vfilename] = k+1
                        order.append(vfilename)

        # find stops
        stops = dict()
        order.insert(0, 'main.py')
        if len(order):
            kk = 1
            while kk < len(order):
                nxt = order[kk]
                stops[order[kk-1]] = starts[nxt]-2
                kk += 1
            stops[order[kk - 1]] = len(all_lines)-1
        else:
            order.append('main.py')
            stops['main.py'] = len(all_lines)-1
        starts['main.py'] = 0
        print('starts:\n', starts)
        print('stops:\n', stops)

        for e in order:
            self.files_to_content[e] = all_lines[starts[e]:stops[e]+1]
        order.remove('main.py')
        order.sort()
        self.file_order = ['main.py'] + order

    def __getitem__(self, item):  # item should be main.py for example
        return self.files_to_content[item]


# - functions for the web -
def game_enter(vmstate):
    global ticker, lu_event, paint_ev, e_manager
    katasdk.set_mode(1)
    ascii_canvas.init(1)  # pass the level of upscaling
    lu_event = kengi.event.CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_ev = kengi.event.CgmEvent(EngineEvTypes.PAINT, screen=None)
    paint_ev.screen = kengi.get_surface()
    e_manager = kengi.event.EventManager.instance()

    offset_x = 0  # offset from the left border of the pygame window
    offset_y = 0  # offset from the top border of the pygame window
    existing_file = False

    # set text content for the editor
    if vmstate is None:
        py_code = FakeProjectLayout(DUMMY_PYCODE)  # just a sample, like just like a LoremIpsum.py ...
        dummy_file = True
    else:
        dummy_file = False
        if vmstate.cedit_arg is None:
            # on peut pogner l'editeur pour montrer son code
            fileinfo = 'editor'
        else:
            fileinfo = vmstate.cedit_arg

        # - fetch code for editing
        if vmstate.has_game(fileinfo):
            existing_file = True
            curr_edition_info = '(editing an existing file {})'.format(fileinfo)
            # AJOUT mercredi 20/04/22 ca peut que marcher en local cela!
            with open(f'{FOLDER_CART}/{fileinfo}.py', 'r') as ff:
                py_code = FakeProjectLayout(ff.read())

        else:  # game creation
            curr_edition_info = '(creating the new file {})'.format(fileinfo)
            py_code = vmstate.blankfile_template
        print(curr_edition_info)

    # another way to do it --------------
    # ajout dimanche 10.04
    # f = open(PATH_SRC_FILE, 'r')
    # editor_text_content = f.read()
    # f.close()
    # formatedtxt_obj = SFText(screen, editor_text_content,
    # run precursor alone
    #    font_path='editor0/fonts/')
    # xxx -> 'editor/**assets/gibson0_font.xxx'
    # if vmstate:
    #    print('***** editing file ******* {}'.format(vmstate.cedit_arg))
    #    ft = kengi.gui.ImgBasedFont(xxx, (0, 0, 250))
    #    tt = ft.render('bidule: ' + vmstate.cedit_arg, False, (0, 250, 0))
    # ------------

    scr_size = paint_ev.screen.get_size()
    editor_blob = TextEditor(
        py_code,
        offset_x, offset_y,  # offset_y is 0
        scr_size[0], scr_size[1] - offset_y, line_numbers_flag=True
    )
    sharedstuff.file_label = None  # editor_blob.currentfont.render(f'opened file= {fileinfo}', False, (0, 250, 0))
    editor_blob.set_text_from_list(py_code['main.py'])

    editor_view = TextEditorAsciiV(editor_blob, MFPS)
    editor_view.turn_on()

    if not dummy_file:
        if existing_file:
            if vmstate.has_ro_flag(fileinfo):
                editor_view.locked_file = True


def game_update(t_info=None):
    global lu_event, paint_ev, gameover, e_manager
    lu_event.curr_t = t_info
    e_manager.post(lu_event)

    e_manager.post(paint_ev)

    e_manager.update()
    kengi.flip()

    if sharedstuff.kartridge_output:
        gameover = True
        return sharedstuff.kartridge_output


def game_exit(vmstate):
    if vmstate:
        if vmstate.cedit_arg is not None and sharedstuff.dump_content is not None:
            # has to be shared with the VM, too
            # let's hack the .cedit_arg attribute, use it as a return value container
            vmstate.cedit_arg = katasdk.mt_a + vmstate.cedit_arg + katasdk.mt_b + sharedstuff.dump_content
            print('.cedit_arg hacked!')

    print('Editor, over')
    kengi.quit()


# --------------------------------------------
#  Entry pt, local ctx
# --------------------------------------------
if __name__ == '__main__':
    import time

    game_enter(katasdk.vmstate)
    gameover = False
    while not gameover:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(katasdk.vmstate)
