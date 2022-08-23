import math
import re
from abc import ABCMeta, abstractmethod
import os
import katagames_sdk as katasdk
from shared import EditorEvents


CogObj = katasdk.kengi.event.CogObj


# --------------------------------------
#  MODEL
class Sharedstuff:
    def __init__(self):
        self.disp_save_ico = None  # contains info 'bout time when it needs display
        self.dump_content = None
        self.kartridge_output = None
        self.screen = None
        self.file_label = None  # for showing what is being edited


class AbstractScProvider(metaclass=ABCMeta):
    @abstractmethod
    def get_source_code(self):
        raise NotImplementedError

    @abstractmethod
    def update_data_source(self, all_lines):
        raise NotImplementedError


class LocalSourceProvider(AbstractScProvider):
    def __init__(self, basecode):
        self.content = basecode

    def get_source_code(self):
        return self.content

    def update_data_source(self, all_lines):
        pass


# there are 4 (FOUR) possibilities:
# game-template x (DISK v Server) ; existing code x (DISK v Server)
class ScProviderFactory:
    # you can replace values manually if needed, before using the factory cls
    LOCAL_DATA_SRC = 'cartridges'

    REMOTE_DATA_SRC = ''

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

    def __init__(self):
        raise NotImplementedError

    @classmethod
    def build(cls, **kwargs):
        # depending on kwargs we'll use a game-template with target,
        if 'local_target' in kwargs:
            # test existence
            if os.path.exists(kwargs['local_target']):
                pass  # TODO
            else:
                return LocalSourceProvider(cls.DUMMY_PYCODE)

        elif 'remote_target' in kwargs:
            pass
        else:
            raise ValueError('cannot build ad-hoc ScProvider')


class VirtualFilesetBuffer:
    """
    can use several files, by default its only main.py
    its called a BUFFER because the user can modify whats inside, then push the new BUFFER content to update
    our current data source
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


class EditorModel(CogObj):
    """
    IMPORTANT:
    the model shouldnt bother with computation that uses pixel,
    e.g. it stores the position of the caret but it should store it in a (i,j) fashion

    Chosen structure:
    we need to store a raw text format (str) for each pseudo-file so the lexer can work properly,
    then we can view a pseudo-file as a list of lines, and each line has info about colors
    """

    def __init__(self, py_vfileset, offset_x, offset_y,  dimx, dimy, line_numbers_flag=False):
        """
        :param py_vfileset: not a str! its a vfileset
        :param offset_x:
        :param offset_y:
        :param dimx:
        :param dimy:
        :param line_numbers_flag: should we display line numbers?
        """
        super().__init__()

        # TT ca cest de la vue!
        self.max_nb_lines_shown = 11  # -->maybe can have a default val, then we set real val via the view
        self.text_area_dim = (dimx, dimy)
        self.editor_offset_X = offset_x
        self.editor_offset_Y = offset_y
        self.displayLineNumbers = line_numbers_flag  # accessed from outside /!\
        self.rerenderLineNumbers = True
        linespacing = 2
        self.letter_size_Y = 12  # size of letters
        self.line_gap = self.letter_size_Y + linespacing
        # this line is here so the text is not overriding column dedicated to  line number display...
        self.xline_start_offset = 25
        # not sure if the following block is super useful, ive added it only to support 4 arrows operations
        self.lineHeight = 20  # -------->view
        self.letter_size_X = 8  # -------->view
        self.lineNumberWidth = 24  # --------->view
        self.yline_start = offset_y  # cest pas dupe val?

        # --- genuine MODEL ok
        self.line_string_list = None  # contenu textuel ss forme d'une liste de lignes
        self.is_read_only = False

        self.maxLines = 0
        self.showStartLine = 0  # accessed from outside
        self.status_info_msg = ''  # acessed from the view
        # -- end

        # --- CURSOR/CARET management
        # we wanna display the caret while typing
        # TODO remove doublon
        self._caret_pos = [0, 0]  # in the i,j fashion
        # 2 vars accessed from the view as well, to render the carret
        self.chosen_LetterIndex = 0
        self.chosen_LineIndex = 0

        self.cursor_Y = self.cursor_X = None
        self.xline = self.xline_start = None
        self.reset_cursor()
        # -- end

        # --- virtual file management
        self.curr_vfile_idx = -1
        self.fake_layout = py_vfileset
        self.switch_file()  # load main.py
        # -- end

    @property
    def caret_pos(self):
        return tuple(self._caret_pos)

    def set_caret_pos(self, i, j):
        self._caret_pos[0] = i
        self._caret_pos[1] = j
        self.pev(EditorEvents.CaretMoves, new_pos=self.caret_pos)

    @property
    def caret_x(self):
        return self._caret_pos[0]

    @caret_x.setter
    def caret_x(self, v):
        self._caret_pos[0] = v
        self.pev(EditorEvents.CaretMoves, new_pos=self.caret_pos)

    @property
    def caret_y(self):
        return self._caret_pos[1]

    @caret_y.setter
    def caret_y(self, v):
        self._caret_pos[1] = v
        self.pev(EditorEvents.CaretMoves, new_pos=self.caret_pos)

    # ---> used by legacy view
    def get_showable_lines(self):
        return self.max_nb_lines_shown

    # --- used by legacy view
    def caret_within_texteditor(self):
        return True

    def switch_file(self):  # access next file in the VirtualFileset
        self.curr_vfile_idx = (self.curr_vfile_idx + 1) % self.fake_layout.size
        vfilename = self.fake_layout.file_order[self.curr_vfile_idx]
        self.set_text_from_list(self.fake_layout[vfilename])
        self.status_info_msg = f"Editing {vfilename}"

    def get_card_lines(self):  # returns nb of lines, total
        return self.maxLines

    def reset_cursor(self):
        if self.displayLineNumbers:
            self.xline_start = self.editor_offset_X + self.xline_start_offset
            self.xline = self.editor_offset_X + self.xline_start_offset
        else:
            self.xline_start = self.editor_offset_X
            self.xline = self.editor_offset_X
        self.cursor_Y = self.editor_offset_Y
        self.cursor_X = self.xline_start
        self._caret_pos = [0, 0]

    def update_caret_position(self):
        # update carret position!!!
        self.cursor_X = self.xline_start + (self.chosen_LetterIndex * self.letter_size_X)
        self.cursor_Y = self.editor_offset_Y
        self.cursor_Y += (self.chosen_LineIndex * self.line_gap)
        self.cursor_Y -= self.showStartLine * self.lineHeight

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
                self.showStartLine + self.max_nb_lines_shown - 1):  # below visible area
            self.showStartLine = self.chosen_LineIndex - self.max_nb_lines_shown + 1
            self.rerenderLineNumbers = True
            self.update_caret_position()
        # next possible enhancement: set cursor coordinates

    def _clear_text(self):
        self.line_string_list = list()  # model: list of actual Strings for each line
        th = self.text_area_dim[1]
        self.maxLines = int(math.floor(th / self.lineHeight))  # TODO dont mix with the view
        self.showStartLine = 0
        for i in range(self.maxLines):  # from 0 to maxLines:
            self.line_string_list.append("")  # Add a line

        # reset caret
        self.rerenderLineNumbers = True
        self.chosen_LineIndex = 0
        self.chosen_LetterIndex = 0
        self.update_caret_position()

    def handle_keyboard_tab(self):
        for x in range(0, 4):  # insert 4 spaces
            self.handle_keyboard_space()

    def handle_keyboard_space(self):
        # insert 1 space
        self.line_string_list[self.chosen_LineIndex] = \
            self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex] + " " + \
            self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        self.caret_x += 1
        self.cursor_X += self.letter_size_X
        self.chosen_LetterIndex += 1

    def handle_keyboard_delete(self):
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

    def handle_keyboard_return(self):
        # Get "transfer letters" behind cursor up to the end of the line to next line
        # If the cursor is at the end of the line, transferString is an empty String ("")
        transfer_string = self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        # Remove transfer letters from the current line
        self.line_string_list[self.chosen_LineIndex] = \
            self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]

        # add a new line
        self.maxLines += 1

        # set logical cursor indizes
        self.chosen_LineIndex += 1
        self.chosen_LetterIndex = 0
        futurej = self.caret_y + 1
        self.set_caret_pos(0, futurej)
        self.cursor_X = self.xline_start  # reset cursor to start of the line

        # insert empty line
        self.line_string_list.insert(self.chosen_LineIndex, "")  # logical line
        # Edit the new line -> append transfer letters
        self.line_string_list[self.chosen_LineIndex] = self.line_string_list[self.chosen_LineIndex] + transfer_string
        self.rerenderLineNumbers = True

        # handle scrolling functionality
        if self.chosen_LineIndex > (
                self.max_nb_lines_shown - 1):  # Last row, visual representation moves down
            self.showStartLine += 1
        else:  # not in last row, put courser one line down without changing the shown line numbers
            self.cursor_Y += self.line_gap

    def insert_unicode(self, unicode):
        nl = self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]
        nl += unicode
        nl += self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        self.line_string_list[self.chosen_LineIndex] = nl
        self.chosen_LetterIndex += 1
        self.caret_x += 1
        self.cursor_X += self.letter_size_X

    def set_text_from_list(self, text_list):
        """
        Sets the text of the editor based on a list of strings. Each item in the list represents one line.
        """
        self._clear_text()
        self.line_string_list = text_list
        self.maxLines = len(self.line_string_list)
        self.rerenderLineNumbers = True

    def set_text_from_string(self, string):
        """
        Sets the text of the editor based on a string. Linebreak characters are parsed.
        """
        self._clear_text()
        self.line_string_list = string.splitlines()
        self.maxLines = len(self.line_string_list)
        self.rerenderLineNumbers = True

    def scroll_up(self):
        pass

    def scroll_down(self):
        pass

    def remove_subsequent_lines(self):
        """
        delete the Strings-line to move the following lines one upwards
        :return:
        """
        self.line_string_list.pop(self.chosen_LineIndex + 1)
        self.maxLines -= 1

        # TODO use a kengi event for this
        # VISUAL lines
        self.rerenderLineNumbers = True

        # Handling of the resulting scrolling functionality of removing one line
        if self.showStartLine > 0:
            if (self.showStartLine + self.max_nb_lines_shown) > self.maxLines:
                # The scrollbar is all the way down. We delete a line,
                # so we have to "pull everything one visual line down"
                self.showStartLine -= 1  # "pull one visual line down" (array-based)
                self.cursor_Y += self.line_gap  # move the curser one down.  (visually based)

    def handle_keyboard_backspace(self):
        if not self.caret_pos[0] and not self.caret_pos[1]:
            return  # 1st position and in the first Line -> nothing happens
        if self.caret_x >= 1:
            self.caret_x -= 1

            # mid-line or end of the line -> Delete a letter
            a = self.line_string_list[self.chosen_LineIndex][:(self.chosen_LetterIndex - 1)]
            b = self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
            self.line_string_list[self.chosen_LineIndex] = a + b
            self.cursor_X -= self.letter_size_X
            self.chosen_LetterIndex -= 1
            return

        if self.chosen_LetterIndex == 0 and self.chosen_LineIndex > 0:
            # One Line back if at X-Position 0 and not in the first Line

            # set letter and line index to newly current line
            self.set_caret_pos(self.chosen_LineIndex - 1, len(self.line_string_list[self.chosen_LineIndex]))
            self.chosen_LineIndex, self.chosen_LetterIndex = self._caret_pos

            # set visual cursor one line above and at the end of the line
            self.cursor_Y -= self.line_gap
            self.cursor_X = self.xline_start + (len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X)

            # take the rest of the former line into the current line
            x = self.line_string_list[self.chosen_LineIndex] + self.line_string_list[self.chosen_LineIndex + 1]
            self.line_string_list[self.chosen_LineIndex] = x

            # delete the former line
            # LOGICAL lines
            self.remove_subsequent_lines()

            if self._caret_pos[1] == (self.showStartLine - 1):
                # Im in the first rendered line (but NOT  the "0" line) and at the beginning of the line.
                # => move one upward, change showstartLine & cursor placement.
                self.showStartLine -= 1
                self._caret_pos[1] += 1

            if self.chosen_LineIndex == (self.showStartLine - 1):
                # Im in the first rendered line (but NOT  the "0" line) and at the beginning of the line.
                # => move one upward, change showstartLine & cursor placement.
                self.showStartLine -= 1
                self.cursor_Y += self.line_gap

        else:
            raise ValueError("INVALID CONSTRUCT: handle_keyboard_backspace. \
                             \nLine:" + str(self.chosen_LineIndex) + "\nLetter: " + str(self.chosen_LetterIndex))

    # --- attempt to fix, cf next comment block with TODO
    def handle_arrow_key(self, direction):
        """
        :param direction: 0, 1, 2, 3 in the order right, top, left, down
        :return:
        """
        inc_i, inc_j = {
            0: (1,  0),
            1: (0, -1),
            2: (-1, 0),
            3: (0,  1)
        }[direction]

        futurei, futurej = self.caret_pos[0]+inc_i, self.caret_pos[1]+inc_j
        total_lines_count = len(self.line_string_list)

        if futurej < 0:
            futurej = 0
        elif futurej >= total_lines_count:
            futurej = total_lines_count - 1
            futurei = len(self.line_string_list[futurej])

        if futurei < 0:
            if futurej > 0:
                futurej -= 1
                futurei = len(self.line_string_list[futurej])  # end of previous line
            else:
                futurei = 0
        elif futurei > len(self.line_string_list[futurej]):
            futurei = 0
            futurej += 1

        # commit new values
        if futurej != self.caret_y or futurei != self.caret_x:
            self._caret_pos[0], self._caret_pos[1] = futurei, futurej
            self.pev(EditorEvents.CaretMoves, new_pos=(futurei, futurej))

    # TODO fix the design
    # this is awful, we have 4 methods each one is handling a single key...
    def handle_keyboard_arrow_left(self):
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

    def handle_keyboard_arrow_right(self):
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
            if self.chosen_LineIndex > (self.showStartLine + self.max_nb_lines_shown - 1):
                # handling scroll functionality if necessary (moved below showed lines)
                self.showStartLine += 1
                self.cursor_Y -= self.line_gap
                self.rerenderLineNumbers = True

    def handle_keyboard_arrow_down(self):
        if self.chosen_LineIndex < (self.maxLines - 1):
            # Not in the last line, downward movement possible
            self.chosen_LineIndex += 1
            self.cursor_Y += self.line_gap

            if len(self.line_string_list[self.chosen_LineIndex]) < self.chosen_LetterIndex:
                # reset letter-index to the end
                self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
                self.cursor_X = (len(
                    self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X) + self.xline_start

            if self.chosen_LineIndex > (self.showStartLine + self.max_nb_lines_shown - 1):
                # handle scrolling functionality if necessary (moved below shown lines)
                self.scroll_down()

        elif self.chosen_LineIndex == (self.maxLines - 1):  # im in the last line and want to jump to its end.
            self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])  # end of the line
            self.cursor_X = self.xline_start + (
                    len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X)

    def handle_keyboard_arrow_up(self):
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


class VirtualClipboard:  # simulation
    strv = None

    @classmethod
    def copy(cls, vstr):
        cls.strv = str(vstr)

    @classmethod
    def cut(cls, vstr):
        cls.strv = str(vstr)

    @classmethod
    def paste(cls):
        return cls.strv


sharedstuff_obj = Sharedstuff()
