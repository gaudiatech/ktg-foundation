import math
import os
import re
import time
from abc import ABCMeta, abstractmethod
from typing import List

import katagames_sdk as katasdk
# katasdk.bootstrap()

kengi = katasdk.kengi
kengi.bootstrap_e()

EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame
CogObj = katasdk.kengi.event.CogObj


# --------------------------------------
# SHARED
sharedstuffxxxx = None


EditorEvTypes = katasdk.kengi.event.enum_ev_types(
    'TextAreaToCarretOp',
    'CaretMoves',
    'RedrawNeeded'  # the view has to redraw numbers etc.
)
DIR_CARTRIDGES = 'cartridges'

# --------------------------------------
# MODEL
RE_CAPTURE_SUBFILE = r"# >>>(\b[_a-z]+\b\.py)"
SHOW_ICON_DURAT = 2.5  # sec


class Sharedstuff:
    def __init__(self):
        self.latest_t = None  # time info

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

    def dump_full_text(self):
        """
        reconstruct the full file from virtual fileset representation...
        :return:
        """
        res = ''
        bsup = len(self.file_order)
        for rank, fname in enumerate(self.file_order):
            if rank == 0:
                res += '\n'.join(self.files_to_content[fname])
            else:
                res += f'# >>>{fname}\n'
                res += '\n'.join(self.files_to_content[fname])
            if rank != bsup - 1:
                res += '\n'
        return res

    def _disting_files(self, rawcode):
        all_lines = rawcode.splitlines()
        all_lines.append('')  # mind the last empty line

        #  on généralise pour qu'on puisse gérer plusieurs fichiers et pas que 2,
        #  et que l'on puisse choisir son nom xxx.py au lieu d'avoir choisi thing.py en dur!
        groups = re.findall(RE_CAPTURE_SUBFILE, rawcode)

        # find starts
        starts = dict()
        order = list()
        if len(groups):
            for vfilename in groups:
                for k, li in enumerate(all_lines):
                    teststr = f"# >>>{vfilename}"
                    if li == teststr:
                        starts[vfilename] = k + 1
                        order.append(vfilename)

        order.insert(0, 'main.py')

        # find stops
        stops = dict()
        if len(order) > 1:
            kk = 1
            while kk < len(order):
                nxt = order[kk]
                stops[order[kk - 1]] = starts[nxt] - 1
                kk += 1
            stops[order[kk - 1]] = len(all_lines) + 1
        else:
            stops['main.py'] = len(all_lines)

        starts['main.py'] = 0
        print('starts:\n', starts)
        print('stops:\n', stops)

        for e in order:
            self.files_to_content[e] = all_lines[starts[e]:stops[e]]

        self.file_order = order
        self.starters = starts

    def __getitem__(self, item):  # item should be main.py for example
        return self.files_to_content[item]


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


class EditorModel(kengi.event.CogObj):
    # ------------------------------------
    #  constructor first
    # ------------------------------------
    def __init__(self, offset_x, offset_y, area_width, area_height, show_line_no=False, syntax_coloring=False):
        super().__init__()
        # ajout numéro sur la numérotation de lignes, améliore ergonomie debug+multi file
        self.artificial_addon_line = 0

        self.content_ram_only = False

        self.locked_file = False
        self.ref_view = None

        # VISUALS
        self.editor_offset_X = offset_x
        self.editor_offset_Y = offset_y
        self.textAreaWidth = area_width
        self.textAreaHeight = area_height
        self.letter_size_Y = 11

        # disable if youre using the newest ver of the view
        # self.courier_font = pygame.font.SysFont('courier', self.letter_size_Y)
        self.letter_size_X = 10

        self.proto_font = None  # init from outside (right after the view obj is created)
        self.known_spacing = None  # init from outside too

        # tom: i comment this bc we wanna use a font that's not monospace,
        # so the width of a msg needs to be computed dynamically based on what characters are on the line...

        # letter_width = self.courier_font.render(" ", self.aa_option, (0, 0, 0)).get_width()
        # self.letter_size_X = letter_width
        self.syntax_coloring = syntax_coloring

        # LINES
        self.Trenn_counter = 0
        self.MaxLinecounter = 0
        self.line_string_list = []  # LOGIC: Array of actual Strings
        self.lineHeight = self.letter_size_Y

        # self.maxLines is the variable keeping count how many lines we currently have -
        # in the beginning we fill the entire editor with empty lines.
        # self.maxLines = int(math.floor(self.textAreaHeight / self.lineHeight))
        # print('maxlines ', self.maxLines)

        self.showStartLine = 0  # first line (shown at the top of the editor) <- must be zero during init!
        self.line_spacing = 3
        self.line_gap = self.letter_size_Y + self.line_spacing
        self.showable_line_numbers_in_editor = int(
            math.floor(self.textAreaHeight / self.line_gap)
        )

        # for i in range(self.maxLines):  # from 0 to maxLines:
        # INIT editor content
        self.line_string_list.append("")  # Add one blank line
        self.conclusionBarHeight = self.textAreaHeight - self.showable_line_numbers_in_editor * self.line_gap

        # SCROLLBAR
        self.scrollbar: pygame.Rect = None
        self.scrollBarWidth = 8  # must be an even number
        self.scroll_start_y: int = 0
        self.scroll_dragging: bool = False

        # LINE NUMBERS
        self.displayLineNumbers = show_line_no
        if self.displayLineNumbers:
            self.lineNumberWidth = (
                27  # line number background width and also offset for text!
            )
        else:
            self.lineNumberWidth = 0
        self.line_numbers_Y = self.editor_offset_Y

        # TEXT COORDINATES
        self.chosen_LineIndex = 0
        self.chosen_LetterIndex = 0
        self.yline_start = self.editor_offset_Y + 3
        self.yline = self.editor_offset_Y
        self.xline_start_offset = 28
        if self.displayLineNumbers:
            self.xline_start = self.editor_offset_X + self.xline_start_offset
            self.xline = self.editor_offset_X + self.xline_start_offset
        else:
            self.xline_start = self.editor_offset_X
            self.xline = self.editor_offset_X

        # CURSOR - coordinates for displaying the caret while typing
        self.static_cursor = False
        self.cursor_Y = self.yline_start - 3
        self.cursor_X = self.xline_start

        # click down - coordinates used to identify start-point of drag
        self.dragged_active = False
        self.dragged_finished = True
        self.drag_chosen_LineIndex_start = 0
        self.drag_chosen_LetterIndex_start = 0
        self.last_clickdown_cycle = 0

        # click up  - coordinates used to identify end-point of drag
        self.drag_chosen_LineIndex_end = 0
        self.drag_chosen_LetterIndex_end = 0
        self.last_clickup_cycle = 0

        # Key input variables+
        self.key_initial_delay = 300
        self.key_continued_intervall = 30
        pygame.key.set_repeat(self.key_initial_delay, self.key_continued_intervall)

        # Performance enhancing variables
        self.firstiteration_boolean = True

        self.click_hold = False
        self.cycleCounter = 0  # Used to be able to tell whether a mouse-drag action has been handled already or not.

        # ------ gestion multifile ----
        self._curr_tabname = ''  # just saving whats the name of the selected tab (no .py extension)
        self.stored_cart_name = None
        self.topbar_info_msg = []
        # fileslayout  # should store an object, instance of FakeProjectLayout
        self.fake_layout = None
        self.curr_vfile_idx = -1

    # gateway to query info about the virtual fileset
    def get_tabs_quantity(self):
        return len(self.fake_layout.file_order)

    def get_tabs_name(self):
        return list(map(lambda x: x.split('.')[0], self.fake_layout.file_order))

    def set_fileset(self, obj):
        self.fake_layout = obj
        self.switch_file()  # so we target 'main.py'

    def _try_save_file(self, target_kart_id):
        global sharedstuffxxxx
        # cas trivial
        if (target_kart_id is None) or self.locked_file:
            print('BLOCK: not allowed to write')
            if target_kart_id is None:
                print('target_kart_id is None')
            if self.locked_file:
                print('cartridge locked')
            return

        print('SAVE FILE: ', )  # TODO this should be in the ctrl not in the model, right?
        # show save icon:
        sharedstuffxxxx.disp_save_ico = sharedstuffxxxx.latest_t + SHOW_ICON_DURAT
        sharedstuffxxxx.dump_content = self.fake_layout.dump_full_text()

        # ------------------------
        # 2 blockS imported from game_exit & from launch_vm.py script
        # ------------------------
        # 1/2
        vms_obj = katasdk.get_vmstate()
        if vms_obj:
            # has to be shared with the VM too
            # Let's hack the .cedit_arg attribute and use it as a return value container
            vms_obj.cedit_arg = katasdk.mt_a + vms_obj.cedit_arg + katasdk.mt_b + sharedstuffxxxx.dump_content
            print('.cedit_arg hacked!')

        # ---------------------------------------------------------
        #  persist the new kartridge content (overwrite mode)
        # ---------------------------------------------------------
        # 2/2
        if vms_obj.cedit_arg and vms_obj.cedit_arg.find(katasdk.mt_a) >= 0:
            x = vms_obj.cedit_arg
            k_idx = x.find(katasdk.mt_b)
            kartr_name = x[len(katasdk.mt_a):k_idx]
            kartr_content = x[k_idx + len(katasdk.mt_b):]
            # crucial instructions. Real save+after saving, we HAVE TO clear cedit_arg...
            # otherwise we may save the kartridge content over& over again
            vms_obj.push_cart_data(kartr_name, kartr_content)

            # nouveauté p/r a ce quon avait ds launch_vm.py (faut reset correctement vms puisquon sort plus de editor)
            vms_obj.cedit_arg = self.stored_cart_name

        self.content_ram_only = False
        self.topbar_info_msg = [f'Saving [cartridge {self.stored_cart_name}] -> OK!']

    # -------------- activates when pressed ctrl+d in the TextEditorV -------------
    def switch_file(self):
        self.curr_vfile_idx = (self.curr_vfile_idx + 1) % self.fake_layout.size
        vfilename = self.fake_layout.file_order[self.curr_vfile_idx]
        self._curr_tabname = vfilename.split('.')[0]

        self.set_text_from_list(self.fake_layout[vfilename])
        self.artificial_addon_line = self.fake_layout.starters[vfilename]
        # self.topbar_info_msg = f"Editing {self._curr_tabname}"

    def target_file(self, vfname):
        pyinfo = vfname + '.py'
        self.curr_vfile_idx = self.fake_layout.file_order.index(pyinfo)
        self._curr_tabname = vfname
        self.set_text_from_list(self.fake_layout[pyinfo])
        # self.topbar_info_msg = f"Editing {self._curr_tabname}"

    @property
    def active_tab_name(self):
        return self._curr_tabname

    # Scroll functionality
    def scrollbar_up(self) -> None:
        self.showStartLine -= 1
        self.cursor_Y += self.line_gap
        self.pev(EditorEvTypes.RedrawNeeded)

    def scrollbar_down(self) -> None:
        self.showStartLine += 1
        self.cursor_Y -= self.line_gap
        self.pev(EditorEvTypes.RedrawNeeded)

    # input handling KEYBOARD
    def handle_keyboard_input(self, pygame_events, pressed_keys) -> None:
        for event in pygame_events:
            if event.type == pygame.KEYDOWN:

                # ___ COMBINATION KEY INPUTS ___
                # Functionality whether something is highlighted or not (highlight all / paste)
                if (
                        pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]
                ) and event.key == pygame.K_a:
                    self.highlight_all()
                elif (
                        pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]
                ) and event.key == pygame.K_v:
                    self.handle_highlight_and_paste()

                # Functionality for when something is highlighted (cut / copy)
                elif self.dragged_finished and self.dragged_active:
                    if (
                            pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]
                    ) and event.key == pygame.K_x:
                        self.handle_highlight_and_cut()
                    elif (
                            pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]
                    ) and event.key == pygame.K_c:
                        self.handle_highlight_and_copy()
                    else:
                        self.handle_input_with_highlight(
                            event
                        )  # handle char input on highlight

                # ___ SINGLE KEY INPUTS ___
                else:
                    self.pev(EditorEvTypes.TextAreaToCarretOp)
                    # self.ref_view.reset_text_area_to_caret()  # reset visual area to include line of caret if necessary
                    self.chosen_LetterIndex = int(self.chosen_LetterIndex)

                    # Detect tapping/holding of the "DELETE" and "BACKSPACE" key while something is highlighted
                    if (
                            self.dragged_finished
                            and self.dragged_active
                            and (event.unicode == "\x08" or event.unicode == "\x7f")
                    ):
                        # create the uniform event for both keys so we don't have to write two functions
                        deletion_event = pygame.event.Event(
                            pygame.KEYDOWN, key=pygame.K_DELETE
                        )
                        self.handle_input_with_highlight(
                            deletion_event
                        )  # delete and backspace have the same functionality

                    # ___ DELETIONS ___
                    elif event.unicode == "\x08":  # K_BACKSPACE
                        self.handle_keyboard_backspace()
                        self.pev(EditorEvTypes.TextAreaToCarretOp)
                        # self.ref_view.reset_text_area_to_caret()  # reset caret if necessary
                    elif event.unicode == "\x7f":  # K_DELETE
                        self.handle_keyboard_delete()
                        self.pev(EditorEvTypes.TextAreaToCarretOp)
                        # self.ref_view.reset_text_area_to_caret()  # reset caret if necessary

                    # ___ NORMAL KEYS ___
                    # This covers all letters and numbers (not those on numpad).
                    elif len(pygame.key.name(event.key)) == 1:
                        self.insert_unicode(event.unicode)

                    # ___ NUMPAD KEYS ___
                    # for the numbers, numpad must be activated (mod = 4096)
                    elif event.mod == 4096 and 1073741913 <= event.key <= 1073741922:
                        self.insert_unicode(event.unicode)
                    # all other numpad keys can be triggered with & without mod
                    elif event.key in [
                        pygame.K_KP_PERIOD,
                        pygame.K_KP_DIVIDE,
                        pygame.K_KP_MULTIPLY,
                        pygame.K_KP_MINUS,
                        pygame.K_KP_PLUS,
                        pygame.K_KP_EQUALS,
                    ]:
                        self.insert_unicode(event.unicode)

                    # ___ SPECIAL KEYS ___
                    elif event.key == pygame.K_TAB:  # TABULATOR
                        self.handle_keyboard_tab()
                    elif event.key == pygame.K_SPACE:  # SPACEBAR
                        self.handle_keyboard_space()
                    elif (
                            event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER
                    ):  # RETURN
                        self.handle_keyboard_return()
                    elif event.key == pygame.K_UP:  # ARROW_UP
                        self.handle_keyboard_arrow_up()
                    elif event.key == pygame.K_DOWN:  # ARROW_DOWN
                        self.handle_keyboard_arrow_down()
                    elif event.key == pygame.K_RIGHT:  # ARROW_RIGHT
                        self.handle_keyboard_arrow_right()
                    elif event.key == pygame.K_LEFT:  # ARROW_LEFT
                        self.handle_keyboard_arrow_left()

                    else:
                        if event.key not in [
                            pygame.K_RSHIFT,
                            pygame.K_LSHIFT,
                            pygame.K_DELETE,
                            pygame.K_BACKSPACE,
                            pygame.K_CAPSLOCK,
                            pygame.K_LCTRL,
                            pygame.K_RCTRL,
                        ]:
                            # We handled the keys separately
                            # Capslock is apparently implicitly handled when using it in combination
                            print("*** warnings ***"
                                  + "No implementation for key: "
                                  + str(pygame.key.name(event.key))
                                  + str(Warning),
                                  )

    def insert_unicode(self, unicode) -> None:
        self.content_ram_only = True

        self.line_string_list[self.chosen_LineIndex] = (
                self.line_string_list[self.chosen_LineIndex][: self.chosen_LetterIndex]
                + unicode
                + self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        )
        self.chosen_LetterIndex += 1
        self.update_caret_position()

    def handle_keyboard_backspace(self) -> None:
        self.content_ram_only = True

        modidx = False
        if self.chosen_LetterIndex == 0 and self.chosen_LineIndex == 0:
            # First position and in the first Line -> nothing happens
            pass
        elif self.chosen_LetterIndex == 0 and self.chosen_LineIndex > 0:
            # One Line back if at X-Position 0 and not in the first Line

            # set letter and line index to newly current line
            self.chosen_LineIndex -= 1
            self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
            # set visual cursor one line above and at the end of the line

            modidx = True
            # self.cursor_Y -= self.line_gap
            # self.cursor_X = self.xline_start + (
            #         len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X
            # )

            # take the rest of the former line into the current line
            self.line_string_list[self.chosen_LineIndex] = (
                    self.line_string_list[self.chosen_LineIndex]
                    + self.line_string_list[self.chosen_LineIndex + 1]
            )

            # delete the former line
            # LOGICAL lines
            self.line_string_list.pop(self.chosen_LineIndex + 1)
            self.maxLines -= 1
            # VISUAL lines
            self.pev(EditorEvTypes.RedrawNeeded)

            # Handling of the resulting scrolling functionality of removing one line
            if self.showStartLine > 0:
                if (
                        self.showStartLine + self.showable_line_numbers_in_editor
                ) > self.maxLines:
                    # The scrollbar is all the way down. We delete a line,
                    # so we have to "pull everything one visual line down"
                    self.showStartLine -= 1  # "pull one visual line down" (array-based)
                    self.cursor_Y += (
                        self.line_gap
                    )  # move the curser one down.  (visually based)
            if self.chosen_LineIndex == (self.showStartLine - 1):
                # Im in the first rendered line (but NOT  the "0" line) and at the beginning of the line.
                # => move one upward, change showstartLine & cursor placement.
                self.showStartLine -= 1
                modidx = True
                # self.cursor_Y += self.line_gap

        elif self.chosen_LetterIndex > 0:
            # mid-line or end of the line -> Delete a letter
            self.line_string_list[self.chosen_LineIndex] = (
                    self.line_string_list[self.chosen_LineIndex][
                    : (self.chosen_LetterIndex - 1)
                    ]
                    + self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
            )

            self.chosen_LetterIndex -= 1
            modidx = True
            self.update_caret_position()
        else:
            raise ValueError(
                "INVALID CONSTRUCT: handle_keyboard_backspace. \
                             \nLine:"
                + str(self.chosen_LineIndex)
                + "\nLetter: "
                + str(self.chosen_LetterIndex)
            )
        if modidx:
            self.update_caret_position()

    def handle_keyboard_delete(self) -> None:
        self.content_ram_only = True

        if self.chosen_LetterIndex < (len(self.line_string_list[self.chosen_LineIndex])):
            # start of the line or mid-line (Cursor stays on point), cut one letter out
            self.line_string_list[self.chosen_LineIndex] = (
                    self.line_string_list[self.chosen_LineIndex][: self.chosen_LetterIndex]
                    + self.line_string_list[self.chosen_LineIndex][
                      (self.chosen_LetterIndex + 1):
                      ]
            )

        elif self.chosen_LetterIndex == len(self.line_string_list[self.chosen_LineIndex]):
            # End of a line  (choose next line)
            if self.chosen_LineIndex != (
                    self.maxLines - 1
            ):  # NOT in the last line &(prev) at the end of the line, I cannot delete anything
                self.line_string_list[self.chosen_LineIndex] += self.line_string_list[
                    self.chosen_LineIndex + 1
                    ]  # add the contents of the next line to the current one
                self.line_string_list.pop(
                    self.chosen_LineIndex + 1
                )  # delete the Strings-line in order to move the following lines one upwards
                self.maxLines -= 1  # Keep the variable aligned
                self.pev(EditorEvTypes.RedrawNeeded)

                if self.showStartLine > 0:
                    if (
                            self.showStartLine + self.showable_line_numbers_in_editor
                    ) > self.maxLines:
                        # The scrollbar is all the way down.
                        # We delete a line, so we have to "pull everything one visual line down"
                        self.showStartLine -= 1  # "pull one visual line down" (array-based)
                        self.cursor_Y += (
                            self.line_gap
                        )  # move the curser one down.  (visually based)
        else:
            raise ValueError(
                " INVALID CONSTRUCT: handle_keyboard_delete. \
                             \nLine:"
                + str(self.chosen_LineIndex)
                + "\nLetter: "
                + str(self.chosen_LetterIndex)
            )

    def handle_keyboard_arrow_left(self) -> None:
        modidx = False
        if self.chosen_LetterIndex > 0:  # mid-line or end of line
            self.chosen_LetterIndex -= 1
            modidx = True
            # self.cursor_X -= self.letter_size_X
        elif self.chosen_LetterIndex == 0 and self.chosen_LineIndex == 0:
            # first line, first position, nothing happens
            pass
        elif (
                self.chosen_LetterIndex == 0 and self.chosen_LineIndex > 0
        ):  # Move over into previous Line (if there is any)
            self.chosen_LineIndex -= 1
            self.chosen_LetterIndex = len(
                self.line_string_list[self.chosen_LineIndex]
            )  # end of previous line

            # self.cursor_X = self.xline_start + (
            #        len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X
            # )
            # self.cursor_Y -= self.line_gap
            modidx = True

            if self.chosen_LineIndex < self.showStartLine:
                # handling scroll functionality if necessary (moved above shown lines)
                self.showStartLine -= 1
                # self.cursor_Y += self.line_gap
                self.pev(EditorEvTypes.RedrawNeeded)
        if modidx:
            self.update_caret_position()

    def handle_keyboard_arrow_right(self):
        modidx = False
        if self.chosen_LetterIndex < (len(self.line_string_list[self.chosen_LineIndex])):
            # mid-line or start of the line
            self.chosen_LetterIndex += 1
            modidx = True
            # self.cursor_X += self.letter_size_X
        else:
            cond2 = not (self.chosen_LineIndex == (self.maxLines - 1))
            if self.chosen_LetterIndex == len(self.line_string_list[self.chosen_LineIndex]) and cond2:
                # end of line => move over into the start of the next line
                self.chosen_LetterIndex = 0
                self.chosen_LineIndex += 1
                modidx = True
                # self.cursor_X = self.xline_start
                # self.cursor_Y += self.line_gap
                if self.chosen_LineIndex > self.showStartLine + self.showable_line_numbers_in_editor - 1:
                    # handling scroll functionality if necessary (moved below showed lines)
                    self.showStartLine += 1
                    # self.cursor_Y -= self.line_gap
                    self.pev(EditorEvTypes.RedrawNeeded)
        if modidx:
            self.update_caret_position()

    def handle_keyboard_arrow_down(self) -> None:
        modidx = False
        if self.chosen_LineIndex < (self.maxLines - 1):
            # Not in the last line, downward movement possible
            self.chosen_LineIndex += 1
            # self.cursor_Y += self.line_gap
            modidx = True

            if len(self.line_string_list[self.chosen_LineIndex]) < self.chosen_LetterIndex:
                # reset letter-index to the end
                self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
                modidx = True

                # self.cursor_X = (
                #                         len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X
                #                 ) + self.xline_start

            if self.chosen_LineIndex > (
                    self.showStartLine + self.showable_line_numbers_in_editor - 1
            ):
                # handle scrolling functionality if necessary (moved below shown lines)
                self.scrollbar_down()

        elif self.chosen_LineIndex == (
                self.maxLines - 1
        ):  # im in the last line and want to jump to its end.
            self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])  # end of the line
            modidx = True

            # self.cursor_X = self.xline_start + (
            #        len(self.line_string_list[self.chosen_LineIndex]) * self.letter_size_X
            # )
        if modidx:
            self.update_caret_position()

    def handle_keyboard_arrow_up(self) -> None:
        modidx = False
        if self.chosen_LineIndex == 0:
            # first line, cannot go upwards, so we go to the first position
            self.chosen_LetterIndex = 0
            # self.cursor_X = self.xline_start
            modidx = True
        elif self.chosen_LineIndex > 0:
            # subsequent lines, upwards movement possible
            self.chosen_LineIndex -= 1
            # self.cursor_Y -= self.line_gap
            modidx = True
            if len(self.line_string_list[self.chosen_LineIndex]) < self.chosen_LetterIndex:
                # less letters in this line, reset toward the end of the line (to the left)
                self.chosen_LetterIndex = len(self.line_string_list[self.chosen_LineIndex])
                modidx = True
                # self.cursor_X = (
                #                     len(self.line_string_list[self.chosen_LineIndex])
                #                 ) * self.letter_size_X + self.xline_start

            if self.chosen_LineIndex < self.showStartLine:  # scroll up one line
                self.scrollbar_up()
        if modidx:
            self.update_caret_position()

    def handle_keyboard_tab(self) -> None:
        for x in range(0, 4):  # insert 4 spaces
            self.handle_keyboard_space()

    def handle_keyboard_space(self) -> None:
        # insert 1 space
        self.line_string_list[self.chosen_LineIndex] = (
                self.line_string_list[self.chosen_LineIndex][: self.chosen_LetterIndex]
                + " "
                + self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        )
        self.chosen_LetterIndex += 1
        self.update_caret_position()

    def handle_keyboard_return(self) -> None:
        # Get "transfer letters" behind cursor up to the end of the line to next line
        # If the cursor is at the end of the line, transferString is an empty String ("")
        transferString = self.line_string_list[self.chosen_LineIndex][
                         self.chosen_LetterIndex:
                         ]

        # Remove transfer letters from the current line
        self.line_string_list[self.chosen_LineIndex] = self.line_string_list[
                                                           self.chosen_LineIndex
                                                       ][: self.chosen_LetterIndex]

        # set logical cursor indizes and add a new line
        self.chosen_LetterIndex = 0
        self.update_caret_position()

        self.chosen_LineIndex += 1
        self.maxLines += 1

        # self.cursor_X = self.xline_start  # reset cursor to start of the line

        # insert empty line
        self.line_string_list.insert(self.chosen_LineIndex, "")  # logical line

        # Edit the new line -> append transfer letters
        self.line_string_list[self.chosen_LineIndex] = (
                self.line_string_list[self.chosen_LineIndex] + transferString
        )
        self.pev(EditorEvTypes.RedrawNeeded)

        # handle scrolling functionality
        if self.chosen_LineIndex > (
                self.showable_line_numbers_in_editor - 1
        ):  # Last row, visual representation moves down
            self.showStartLine += 1
        else:  # not in last row, put courser one line down without changing the shown line numbers
            self.cursor_Y += self.line_gap

    # from ._input_handling_keyboard_highlight import (
    #     handle_input_with_highlight,
    #     handle_highlight_and_copy,
    #     handle_highlight_and_paste,
    #     handle_highlight_and_cut,
    #     highlight_all,
    #     get_highlighted_characters,
    # )

    # input handling MOUSE
    def mouse_within_texteditor(self, mouse_x, mouse_y) -> bool:
        """
        Returns True if the given coordinates are within the text-editor area of the pygame window, otherwise False.
        """
        # old:
        # rab = self.scrollBarWidth
        # new:
        rab = 0
        # for the new view version, we consider scrollbar is part of the editor
        return self.editor_offset_X + self.lineNumberWidth < mouse_x < (
                self.editor_offset_X + self.textAreaWidth - rab
        ) and self.editor_offset_Y < mouse_y < (
                       self.textAreaHeight + self.editor_offset_Y - self.conclusionBarHeight
               )

    def mouse_within_existing_lines(self, mouse_y):
        """
        Returns True if the given Y-coordinate is within the height of the text-editor's existing lines.
        Returns False if the coordinate is below existing lines or outside of the editor.
        """
        return (
                self.editor_offset_Y
                < mouse_y
                < self.editor_offset_Y + (self.lineHeight * self.maxLines)
        )

    # caret

    def set_drag_start_by_mouse(self, mouse_x, mouse_y) -> None:
        # get line
        self.drag_chosen_LineIndex_start = self.get_line_index(mouse_y)

        # end of line
        if self.get_number_of_letters_in_line_by_mouse(mouse_y) < self.get_letter_index(
                mouse_x
        ):
            self.drag_chosen_LetterIndex_start = len(
                self.line_string_list[self.drag_chosen_LineIndex_start]
            )

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
        if self.get_letter_index(mouse_x) > self.get_number_of_letters_in_line_by_index(
                self.drag_chosen_LineIndex_end
        ):
            self.drag_chosen_LetterIndex_end = len(
                self.line_string_list[self.drag_chosen_LineIndex_end]
            )
        else:  # within existing line
            self.drag_chosen_LetterIndex_end = self.get_letter_index(mouse_x)

    def set_drag_start_after_last_line(self) -> None:
        # select last line
        self.drag_chosen_LineIndex_start = self.maxLines - 1
        # select last letter of the line
        self.drag_chosen_LetterIndex_start = len(
            self.line_string_list[self.drag_chosen_LineIndex_start]
        )

    def set_drag_start_before_first_line(self) -> None:
        self.drag_chosen_LineIndex_start = 0
        self.drag_chosen_LetterIndex_start = 0

    def set_drag_end_after_last_line(self) -> None:
        # select last line
        self.drag_chosen_LineIndex_end = self.maxLines - 1
        # select last letter of the line
        self.drag_chosen_LetterIndex_end = len(
            self.line_string_list[self.drag_chosen_LineIndex_end]
        )

    def update_caret_position_by_drag_start(self) -> None:
        """
        # Updates cursor_X and cursor_Y positions based on the start position of a dragging operation.
        """
        # TODO
        # possible refactor: lets update the logical stuff right away? instead of doing it afterwars in
        # update_caret_position_by_drag_start

        # X Position
        self.cursor_X = self.xline_start + (
                self.drag_chosen_LetterIndex_start * self.letter_size_X
        )
        # Y Position
        self.cursor_Y = (
                self.editor_offset_Y
                + (self.drag_chosen_LineIndex_start * self.line_gap)
                - (self.showStartLine * self.lineHeight)
        )

    def update_caret_position_by_drag_end(self) -> None:
        """
        # Updates cursor_X and cursor_Y positions based on the end position of a dragging operation.
        """
        # X Position
        self.cursor_X = self.xline_start + (
                self.drag_chosen_LetterIndex_end * self.letter_size_X
        )
        # Y Position
        self.cursor_Y = (
                self.editor_offset_Y
                + (self.drag_chosen_LineIndex_end * self.line_gap)
                - (self.showStartLine * self.lineHeight)
        )

    def update_caret_position(self) -> None:
        """
        # Updates cursor_X and cursor_Y positions based on current position by line and letter indices
        """
        if self.proto_font:
            # -- new >>>>>>>>>>>>>>
            chunk = self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]

            x_mini_offset = -2
            self.cursor_X = self.xline_start + self.proto_font.compute_width(chunk,
                                                                             spacing=self.known_spacing) + x_mini_offset
            # version tom
            self.cursor_Y = self.editor_offset_Y
            self.cursor_Y += self.line_spacing + (self.chosen_LineIndex - self.showStartLine) * self.line_gap

        else:
            # -- old >>>>>>>>>>>>> uses monospace

            self.cursor_X = self.xline_start + (self.chosen_LetterIndex * self.letter_size_X)

            self.cursor_Y = (
                    self.editor_offset_Y
                    + (self.chosen_LineIndex * self.line_gap)
                    - (self.showStartLine * self.lineHeight)
            )

    # letter operations (delete, get)
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
        self.line_string_list[line] = (
                self.line_string_list[line][:letter_start]
                + self.line_string_list[line][letter_end:]
        )

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

    def get_line_index(self, mouse_y) -> int:
        """
        Returns possible line-position of mouse -> does not take into account
        how many lines there actually are!
        """
        y = ((mouse_y - self.editor_offset_Y) / self.line_gap) + self.showStartLine
        return int(y)

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
        return (
                self.showStartLine
                <= line
                < self.showStartLine + self.showable_line_numbers_in_editor
        )

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
        self.update_caret_position()  # update caret position to chosen_Index (Line+Letter)
        self.last_clickdown_cycle = 0  # reset drag-cycle
        self.last_clickup_cycle = -1
        self.pev(EditorEvTypes.RedrawNeeded)

        if len(self.line_string_list) <= self.showable_line_numbers_in_editor:
            self.showStartLine = 0  # update first showable line

    # # files for customization of the editor:
    # from ._customization import (
    #     set_line_numbers,
    #     set_font_size,
    #     set_cursor_mode,
    # )

    def get_text_as_string(self) -> str:
        """
        Returns the entire text of the editor as a single string.
        Linebreak characters are used to differentiate between lines.
        :param self:  Texteditor-Class
        :return: String
        """
        return "\n".join(self.line_string_list)

    def get_text_as_list(self) -> List:
        """
        Returns the text in it's logical form as a list of lines.
        :param self:  Texteditor-Class
        :return: List of lines containing the text. Lines cane be empty Strings.
        """
        return self.line_string_list

    def clear_text(self) -> None:
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
        self.pev(EditorEvTypes.RedrawNeeded)

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

    def set_text_from_list(self, text_list) -> None:
        """
        Sets the text of the editor based on a list of strings. Each item in the list represents one line.
        """
        self.clear_text()
        self.line_string_list = text_list
        self.maxLines = len(self.line_string_list)
        self.pev(EditorEvTypes.RedrawNeeded)

    def set_text_from_string(self, string) -> None:
        """
        Sets the text of the editor based on a string. Linebreak characters are parsed.
        """
        self.clear_text()
        self.line_string_list = string.split("\n")
        self.maxLines = len(self.line_string_list)
        self.pev(EditorEvTypes.RedrawNeeded)

    # ----------------
    # remetrre ca dans view at some point?
    # ----------------
    def reset_text_area_to_caret(self):
        """
        Reset visual area to include the line of caret if it is currently not visible. This function ensures
        that whenever we type, the line in which the caret resides becomes visible, even after scrolling.
        """
        if self.chosen_LineIndex < self.showStartLine:  # above visible area
            self.showStartLine = self.chosen_LineIndex
            self.rerenderLineNumbers = True
            self.update_caret_position()
        elif self.chosen_LineIndex > (
                self.showStartLine + self.showable_line_numbers_in_editor - 1
        ):  # below visible area
            self.showStartLine = (
                    self.chosen_LineIndex - self.showable_line_numbers_in_editor + 1
            )
            self.rerenderLineNumbers = True
            self.update_caret_position()
        # TODO: set cursor coordinates


# ------------------------------------------
#  VIEW
# - constants
PY_SYNTAX = {
    ('BUILT-IN', 2): (  # py built-in stuff
        'super', 'bool', 'list', 'tuple', 'str', 'int', 'float', 'len', 'enumerate', 'range', 'max', 'min', 'print',
    ),
    ('KEYWORDS', 1): (  # py keywords
        'if', 'else', 'elif', 'for', 'while',
        'not', 'in', 'None', 'True', 'False',
        'def', 'return', 'class', 'as',
    ),
    ('VSPECIAL', 5): (  # vspecial words
        '__init__', 'self'
    )
}


class CapelloEditorView(kengi.event.EventReceiver):
    DEFAULT_DEEP_GRAY_BGCOLOR = (43, 43, 43)  # same gray used by PyCharm
    CYCL_SCROLLING_FREQ = 3  # value: int, 1+  The higher this number is, the more slow it adds on scrolling bar

    def __init__(self, ref_mod):
        super().__init__()
        self.cached_rendering_list = None

        self.color_scrollbar = pygame.color.Color('grey34')
        # used solely for the scrolling via mouse feature
        self.scroll_start_y = 0
        self.scroll_dragging = False
        # avoid scroll too fast
        self.cycleCounter = 0
        # TODO find another way to express the following behavior
        # /!\ its very likely that this wont work in web ctx... start pb {
        key_initial_delay = 350
        key_continued_intervall = 50
        pygame.key.set_repeat(key_initial_delay, key_continued_intervall)
        # } end pb

        self._syntax_coloring = False
        self._bg_color = None

        # for display tabs (multi-file support)
        self.tabline_color = (57, 159, 57)  # for better results this has to match image
        self.img_editortab = pygame.image.load('assets/editorTab.png')
        self.decal_y_tabs = -17

        self.cfonts = [
            # 0.0.9+
            # kengi.gfx.JsonBasedCfont('assets/capello-ft'),
            # kengi.gfx.JsonBasedCfont('assets/capello-ft-a'),
            # kengi.gfx.JsonBasedCfont('assets/capello-ft-b'),
            # kengi.gfx.JsonBasedCfont('assets/capello-ft-c'),
            # kengi.gfx.JsonBasedCfont('assets/capello-ft-d'),
            # kengi.gfx.JsonBasedCfont('assets/capello-ft-e'),
            #-
            # 0.0.9compat
            kengi.gfx.ProtoFont(font_source='assets/capello-ft'),
            kengi.gfx.ProtoFont(font_source='assets/capello-ft-a'),
            kengi.gfx.ProtoFont(font_source='assets/capello-ft-b'),
            kengi.gfx.ProtoFont(font_source='assets/capello-ft-c'),
            kengi.gfx.ProtoFont(font_source='assets/capello-ft-d'),
            kengi.gfx.ProtoFont(font_source='assets/capello-ft-e')
        ]
        self._mod = ref_mod
        self._mod.proto_font = self.cfonts[0]
        self.chosen_sp = 1  # spacing between letters
        self._mod.known_spacing = self.chosen_sp  # copy it to the model

        # color bg the editor
        self.rect_editor = (
            self._mod.editor_offset_X, self._mod.editor_offset_Y, self._mod.textAreaWidth, self._mod.textAreaHeight
        )

        # so we can disp a caret
        self.caret_img = pygame.image.load('assets/Trennzeichen.png')
        cwidth = self.caret_img.get_size()[0]
        adhoc_h = self.cfonts[0].car_height['x']  # all chars have the same height so we can use x, whatever
        # TODO retablir ceci (peut etre?) quand le .scale sera implémenté en web ctx
        # self.caret_img = pygame.transform.scale(self.caret_img, (2*cwidth, 1+adhoc_h))

        # update this when proc event CaretMoves
        self.cursor_xy = [self._mod.xline_start - 1, 0]  # y 0 because we start on line 0
        self.rerenderLineNumbers = True

    def set_bg_color(self, colobj):
        self._bg_color = colobj

    def set_syntax_highlighting(self, boolv):
        print('VIEW: syntax_highlighting receives:', boolv)
        self._mod.syntax_coloring = boolv  # TODO clean this mess
        self._syntax_coloring = boolv

    # --------------
    #  métier, methodes privées
    # --------------
    def findrect_for_tab(self, n):
        w, h = self.img_editortab.get_size()
        return pygame.Rect(
            n * (w + 2) + self._mod.editor_offset_X + self._mod.lineNumberWidth,
            self._mod.editor_offset_Y + self.decal_y_tabs,
            w, h
        )

    def _render_tabs(self, scr_ref):
        w, h = self.img_editortab.get_size()
        selected_tname = self._mod.active_tab_name
        for k, tname in enumerate(self._mod.get_tabs_name()):
            rect = self.findrect_for_tab(k)
            pygame.draw.rect(scr_ref, self.lineNumberBackgroundColor, rect, 0)

        # draw a green line
        # coordy = self._mod.editor_offset_Y-1
        # pygame.draw.line(scr_ref, self.tabline_color,
        #             (self._mod.editor_offset_X+self._mod.lineNumberWidth, coordy),
        #                  (self._mod.editor_offset_X+self._mod.textAreaWidth, coordy),
        #             1)

        # pygame.draw.rect(scr_ref,
        #                  self.tabline_color,
        #                  (
        #                      self._mod.editor_offset_X + self._mod.lineNumberWidth,
        #                      self._mod.editor_offset_Y + self.decal_y_tabs + h,
        #                      self._mod.textAreaWidth,
        #                      1),
        #                  1
        #                  )

        txth = self.cfonts[1].car_height[' ']
        for k, tname in enumerate(self._mod.get_tabs_name()):
            # label the tab
            txtw = self.cfonts[0].compute_width(tname, spacing=self.chosen_sp)
            r = self.findrect_for_tab(k)
            if tname == selected_tname:
                # pygame.draw.rect(scr_ref, self.lineNumberBackgroundColor, (r[0], r[1], r[2], r[3] + 1), 0)
                scr_ref.blit(self.img_editortab, r)
            self.cfonts[4].text_to_surf(tname, scr_ref, (int(r.center[0] - txtw / 2), int(3 + r.center[1] - txth / 2)),
                                        spacing=self.chosen_sp)

    def _get_dicts_syntax_coloring(self):
        res = list()
        # new algo (august 22), detect py keywords and use colours
        for rawline in self._mod.line_string_list:
            curr_li = list()
            reco_smth = None
            while (reco_smth is None) or reco_smth:
                reco_smth = False

                # - detect commentary, lines that start with
                result = re.search(r'#.*$', rawline)
                if result:
                    x, bsup = result.span()
                    found = result.group()
                    if x > 0:
                        curr_li.append({'chars': rawline[:x], 'color': 0, 'style': 'normal'})
                    reco_smth = True
                    rawline = rawline[bsup:]
                    str_col = 4
                    curr_li.append({'chars': found, 'color': str_col, 'style': 'normal'})
                    continue

                # - attempt to detect keywords
                for syntaxcat, known_words in PY_SYNTAX.items():
                    for w in known_words:
                        find_rez = re.search(r'\b' + w + r'\b', rawline)
                        if find_rez:  # update rawline (remove recognized w) & append w to curr_li
                            reco_smth = True
                            x, bsup = find_rez.span()
                            if x > 0:
                                curr_li.append({'chars': rawline[:x], 'color': 0, 'style': 'normal'})
                            rawline = rawline[bsup:]
                            curr_li.append({'chars': w, 'color': syntaxcat[1], 'style': 'normal'})

                # - detect strings enclosed by "
                result = re.search(r'(["\'].*["\'])', rawline)
                if result:
                    found = result.groups()[0]
                    x = rawline.index(found)
                    if x > 0:
                        curr_li.append({'chars': rawline[:x], 'color': 0, 'style': 'normal'})
                    bsup = x + len(found)
                    reco_smth = True
                    rawline = rawline[bsup:]
                    str_col = 3
                    curr_li.append({'chars': found, 'color': str_col, 'style': 'normal'})

            # append the rest of the line, regular color
            curr_li.append({'chars': rawline, 'color': 0, 'style': 'normal'})
            res.append(curr_li)
        return res

    def _get_dicts(self):  # -> List[List[Dict]]
        """
        THIS METHOD = display without color syntaxing!

        Converts the text in the editor based on the line_string_list into a list of lists of dicts.
        Every line is one sublist.
        Since only one color is being applied, we create a list with one dict per line.
        """
        if self._syntax_coloring:
            return self._get_dicts_syntax_coloring()

        # simple case
        if self.cached_rendering_list is None:
            self.cached_rendering_list = list()
            for rawline in self._mod.line_string_list:
                # a single-item list when a single color is used
                self.cached_rendering_list.append([{'chars': rawline, 'color': 0, 'style': 'normal'}])
        return self.cached_rendering_list

    def _render_line_contents(self, li_dicts, rscreen):
        moo = self._mod

        # Preparation of the rendering:
        self.yline = self._mod.yline_start

        # compatible lightweight model, mais pas editor4model
        # begin, end = moo.get_visible_line_indices()

        # compat' editor4model :
        begin = moo.showStartLine
        end = begin + moo.showable_line_numbers_in_editor
        if end >= len(moo.line_string_list):
            end = len(moo.line_string_list)
        # if (begin + moo.maxLines) >= len(moo.line_string_list):
        #     end = len(moo.line_string_list) - 1
        # else:
        #     end = begin + moo.max_nb_lines_shown

        # Actual line rendering based on dict-keys
        for line_list in li_dicts[begin:end]:
            xcoord = self._mod.xline_start
            for a_dict in line_list:
                cidx = a_dict['color']
                pfont = self.cfonts[cidx]
                pfont.text_to_surf(a_dict['chars'], rscreen, (xcoord, self.yline), spacing=self.chosen_sp)
                xcoord += pfont.compute_width(a_dict['chars'], spacing=self.chosen_sp)
            self.yline += moo.line_gap  # next line prep

    def _render_caret(self, rscreen):
        # - deprecated old code(2)
        # rscreen.blit(self.caret_img, (self._mod.cursor_X, self._mod.cursor_Y))
        # - deprecated old code (1)
        # self.Trenn_counter += 1
        # if self.Trenn_counter > (self._maxfps / 5) and self._blob.caret_within_texteditor() and self.dragged_finished:
        #     scr.blit(self.carret_img, (self._blob.cursor_X, self._blob.cursor_Y))
        #     self.Trenn_counter = self.Trenn_counter % ((self._maxfps / 5) * 2)

        # deprec cannot work with heavy_mod
        # rscreen.blit(self.caret_img, self.cursor_xy)
        binf_y = self._mod.editor_offset_Y
        if binf_y < self._mod.cursor_Y < binf_y + self._mod.textAreaHeight:
            rscreen.blit(self.caret_img, (self._mod.cursor_X, self._mod.cursor_Y))

    # -----------------------------
    #  scrollbars
    # -----------------------------
    def render_scrollbar_vertical(self, scr) -> None:
        self.display_scrollbar(scr)

    def display_scrollbar(self, scr):
        if len(self._mod.line_string_list) <= self._mod.showable_line_numbers_in_editor:
            self._mod.scrollbar = None
            return  # if scrollbar is not needed, don't show.

        # scroll bar is a fraction of the space
        w = self._mod.scrollBarWidth
        x = (
                self._mod.editor_offset_X + self._mod.textAreaWidth - self._mod.scrollBarWidth - 2
        )  # -2 for space between edge & scrollbar
        y = int(
            self._mod.editor_offset_Y
            + (w / 2)
            + (self._mod.textAreaHeight * ((self._mod.showStartLine * 1.0) / self._mod.maxLines))
        )
        h = int(
            (self._mod.textAreaHeight - w)
            * ((self._mod.showable_line_numbers_in_editor * 1.0) / self._mod.maxLines)
        )
        h -= 2  # minor adjustment so we don't draw any single pixel outside of the editor boundaries
        self._mod.scrollbar = pygame.Rect(x, y, w, h)

        pygame.draw.circle(
            scr, self.color_scrollbar, (int(x + (w / 2)), y), int(w / 2)
        )  # top round corner
        pygame.draw.rect(
            scr, self.color_scrollbar, self._mod.scrollbar
        )  # actual scrollbar
        pygame.draw.circle(
            scr, self.color_scrollbar, (int(x + (w / 2)), y + h), int(w / 2)
        )  # bottom round corner

    # - old, deprecated version. No logical caret update triggered back then
    def _left_click_handle0(self, mousx, mousy):
        # in order not to have the mouse move around after a click,
        # we need to disable this function until we RELEASE it.

        # /!\ was de-activated, i dunno if its mandatory to use this
        # self.last_clickdown_cycle = self.cycleCounter

        self._mod.click_hold = True
        self._mod.dragged_active = True
        self._mod.dragged_finished = False

        if self._mod.mouse_within_texteditor(mousx, mousy):  # editor area
            if self._mod.mouse_within_existing_lines(mousy):  # in area of existing lines
                self._mod.set_drag_start_by_mouse(mousx, mousy)
            else:  # clicked below the existing lines
                self._mod.set_drag_start_after_last_line()

            self._mod.update_caret_position_by_drag_start()
            # tom add-on:
            # we need this otherwise the carret moves but the next unicode inputed comes at the wrong location!
            # self._mod.set_drag_start_by_mouse(mousx, mousy)
        else:
            pass  # mouse outside of editor => ignored this

    def _left_click_handle(self, mousx, mousy):  # check collision {tab, scrollbar}, then find adhoc pos logical caret.
        if self._mod.get_tabs_quantity() > 1:
            for k, tabname in enumerate(self._mod.get_tabs_name()):
                a, b, c, d = self.findrect_for_tab(k)
                if a < mousx < a + c:
                    if b < mousy < b + d:
                        self._mod.target_file(tabname)
                        return

        if self._mod.scrollbar is not None:
            if self._mod.scrollbar.collidepoint(mousx, mousy):
                self.scroll_start_y = mousy
                self.scroll_dragging = True
                return

        if self._mod.mouse_within_texteditor(mousx, mousy):
            if not self._mod.mouse_within_existing_lines(mousy):  # clicked below the existing lines
                # self._mod.set_drag_start_after_last_line()
                # self._mod.update_caret_position_by_drag_start()
                j = len(self._mod.line_string_list) - 1
                adhoc_txt_line = self._mod.line_string_list[j]
                i = len(adhoc_txt_line)
                self._mod.chosen_LetterIndex, self._mod.chosen_LineIndex = (i, j)
                self._mod.update_caret_position()
                return

            j = (mousy - self._mod.editor_offset_Y) // self._mod.line_gap
            j += self._mod.showStartLine
            adhoc_txt_line = self._mod.line_string_list[j]
            ft = self.cfonts[0]

            i = None
            decalx = self._mod.editor_offset_X
            # TODO fix this computation in case we dont disp line numbers!
            tmarge = self._mod.lineNumberWidth  # marge ds laquelle on a écrit les numéro de ligne

            for adhoc_idx in range(len(adhoc_txt_line), -1, -1):
                if mousx > ft.compute_width(adhoc_txt_line[:adhoc_idx], spacing=self.chosen_sp) + tmarge + decalx - 3:
                    i = adhoc_idx
                    break
            # impact the model
            self._mod.chosen_LetterIndex, self._mod.chosen_LineIndex = (i, j)
            self._mod.update_caret_position()

    # ---------------------
    #  most important method for this cls
    def proc_event(self, ev, source=None):
        if ev.type == EngineEvTypes.PAINT:
            if self.scroll_dragging:
                _, my = kengi.vscreen.proj_to_vscreen(pygame.mouse.get_pos())
                if my > self.scroll_start_y:
                    if self._mod.showStartLine + self._mod.showable_line_numbers_in_editor < len(
                            self._mod.line_string_list):
                        self._mod.scrollbar_down()
                elif my < self.scroll_start_y:
                    if self._mod.showStartLine > 0:
                        self._mod.scrollbar_up()

            self._do_paint(ev.screen)

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = kengi.vscreen.proj_to_vscreen(ev.pos)

            if ev.button == 1:
                self._left_click_handle(mx, my)
            else:
                if self._mod.mouse_within_texteditor(mx, my):
                    if ev.button == 4 and self._mod.showStartLine > 0:
                        self._mod.scrollbar_up()
                    elif ev.button == 5 and self._mod.showStartLine + self._mod.showable_line_numbers_in_editor < self._mod.maxLines:
                        self._mod.scrollbar_down()

        elif ev.type == pygame.MOUSEBUTTONUP:
            if self.scroll_dragging:
                self.scroll_dragging = False
                self.cycleCounter = 0

        elif ev.type == EditorEvTypes.RedrawNeeded:
            self.rerenderLineNumbers = True

        elif ev.type == EditorEvTypes.CaretMoves:
            xinit = self._mod.xline_start
            i, j = ev.new_pos
            a, _ = self._mod.get_visible_line_indices()
            txt_antecedent = self._mod.line_string_list[j][:i]
            # print(f'ante:[{txt_antecedent}]')
            #  i * self._mod.letter_size_X
            self.cursor_xy[0] = xinit - 2 + self.cfonts[0].compute_width(txt_antecedent, spacing=self.chosen_sp)
            self.cursor_xy[1] = (j - a) * self._mod.line_gap

    def _do_paint(self, scr_ref):
        # RENDERING 1 - Background objects
        # self.render_background_coloring(ref_scr)
        scr_ref.fill('grey11')

        if self._bg_color:
            pygame.draw.rect(scr_ref, self._bg_color, self.rect_editor, 0)
        else:
            pygame.draw.rect(scr_ref, self.DEFAULT_DEEP_GRAY_BGCOLOR, self.rect_editor, 0)

        # -- render line numbers --
        if self.rerenderLineNumbers and self._mod.displayLineNumbers:
            # dirty, jit def
            # self.lineNumberBackgroundColor = (44, 33, 33)
            defaultcol = self.DEFAULT_DEEP_GRAY_BGCOLOR
            # self.lineNumberBackgroundColor = defaultcol if (self._bg_color is None) else self._bg_color
            self.lineNumberBackgroundColor = pygame.color.Color('grey12')
            self.lineNumberColor = (80, 77, 188)
            # self.pygfont = pygame.font.SysFont('courier', 12)

            line_numbers_y = self._mod.editor_offset_Y  # init for first line
            binf, bsup = self._mod.showStartLine, self._mod.showStartLine + self._mod.showable_line_numbers_in_editor
            for x in range(binf, bsup):
                # background
                r = (
                    self._mod.editor_offset_X,
                    line_numbers_y,
                    self._mod.lineNumberWidth,
                    self._mod.line_gap,
                )
                pygame.draw.rect(scr_ref, self.lineNumberBackgroundColor, r)

                # line number
                if x < self._mod.get_showable_lines():
                    # x + 1 in order to start with line 1 (only display, logical it's the 0th item in the list
                    nstr = str(x + 1 + self._mod.artificial_addon_line).zfill(3)

                    # -old
                    # text = self.pygfont.render(
                    #    nstr, self._mod.aa_option, self.lineNumberColor
                    # )
                    # text_rect = text.get_rect()
                    # text_rect.center = pygame.Rect(r).center

                    self.cfonts[3].text_to_surf(nstr, scr_ref, (
                        -4 + r[0] + r[2] - self.cfonts[0].compute_width(nstr, spacing=0),
                        r[1] + self._mod.line_spacing),
                                                spacing=0)
                    # -old
                    # scr_ref.blit(text, text_rect)  # render on center of bg block
                line_numbers_y += self._mod.line_gap

        # barre info top
        if len(self._mod.topbar_info_msg):
            for line_no, line_info in enumerate(self._mod.topbar_info_msg):
                self.cfonts[0].text_to_surf(
                    line_info,
                    scr_ref,
                    (5, 1 + 7 * line_no),
                    bgcolor='darkred'
                )

        # ++ tabs ++
        if self._mod.get_tabs_quantity() > 1:
            self._render_tabs(scr_ref)

        # ++ lines of text ++
        list_of_dicts = self._get_dicts()  # find what to draw + syntax coloring if needed
        # format returned by GET_COLOR_DICTS: List[List[Dict]]
        # if there's only one color for the whole line, the model of the line will look like this:
        # [{'chars': the_whole_line_str_obj, 'type': 'normal', 'color': self.textColor}]
        # if many colors, therefore many elements in the inner list...
        self._render_line_contents(list_of_dicts, scr_ref)
        self._render_caret(scr_ref)
        self.render_scrollbar_vertical(scr_ref)


# ----------------------------------------
#  CTRL
class EditorCtrl(kengi.event.EventReceiver):
    def __init__(self, ref_mod, ref_view, shared):
        super().__init__()
        self._mod = ref_mod
        self._view = ref_view

        self.keypress_duration = 0

        self.sharedstuff = shared
        self.dragged_active = False
        self.dragged_finished = True

        self.arrow_keys_active = {
            pygame.K_RIGHT: False, pygame.K_UP: False, pygame.K_LEFT: False, pygame.K_DOWN: False,
        }

    def proc_event(self, ev, source=None):
        global sharedstuffxxxx
        """
        in particular, we need to handle:
        - escape = exit
        - ctrl+s = save content
        - ctrl+r the "refresh" operation: allows the user to pseudo-split his/her program
        - ctrl+n the "next file" operation: allows the user to cycle through all pseudo-files
        """
        if ev.type == kengi.event.EngineEvTypes.LOGICUPDATE:
            dt = 0
            if sharedstuffxxxx.latest_t is not None:
                dt = ev.curr_t - sharedstuffxxxx.latest_t
            sharedstuffxxxx.latest_t = ev.curr_t
            self.keypress_duration += dt

        # elif ev.type == pygame.KEYUP:
        #     if any(self.arrow_keys_active):
        #         pressed_key = pygame.key.get_pressed()
        #         for kcode in self.arrow_keys_active.keys():
        #             self.arrow_keys_active[kcode] = pressed_key[kcode]

        elif ev.type == pygame.KEYDOWN:
            kcode = ev.key
            hit = False
            if kcode == pygame.K_RIGHT:
                self._mod.handle_keyboard_arrow_right()
                hit = True
            elif kcode == pygame.K_UP:
                self._mod.handle_keyboard_arrow_up()
                hit = True
            elif kcode == pygame.K_LEFT:
                self._mod.handle_keyboard_arrow_left()
                hit = True
            elif kcode == pygame.K_DOWN:
                self._mod.handle_keyboard_arrow_down()
                hit = True
            if hit:
                return

            pressed_keys = pygame.key.get_pressed()
            uholding_ctrl = pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]

            if ev.key in (pygame.K_RIGHT, pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN):
                self.arrow_keys_active[ev.key] = True

            elif ev.key == pygame.K_ESCAPE:
                if len(self._mod.topbar_info_msg):
                    self._mod.topbar_info_msg = []
                else:
                    self.sharedstuff.kartridge_output = [2, 'niobepolis']
                    # self.pev(EngineEvTypes.GAMEENDS)
                    # print('[EditorCtrl] thrownig gameends event')

            # -----------------------------
            #  nouveauté ! feat inédite aout 22
            # -----------------------------
            elif uholding_ctrl and ev.key == pygame.K_h:

                # self._view.syntax_coloring = not self._view.syntax_coloring
                # wtf! why do I still have this in the model, not the view?
                # TODO refactor
                self._mod.syntax_coloring = not self._mod.syntax_coloring
                self._view.set_syntax_highlighting(self._mod.syntax_coloring)
                print('Coloring toggled!')
            elif uholding_ctrl and ev.key == pygame.K_l:
                if self._mod.content_ram_only:
                    self._mod.topbar_info_msg = ['Cannot preview. Need to save file first (press Ctrl+s)']
                    return

                vms = katasdk.get_vmstate()
                cartname = self._mod.stored_cart_name

                vms.py_sourcecode = self._mod.fake_layout.dump_full_text()
                retour = katasdk.debug_syntaxcheck(f'cartridges/{cartname}.py')

                print(f'..................\nTesting cartridges/{cartname}.py\n....................\n')

                if not retour[0]:
                    print('syntax test ERROR')
                    # TODO faire en sorte que ce soit le ctrl qui est impacté ainsi on pourra mieux gérer jpense?
                    self._mod.topbar_info_msg = retour[1].splitlines()
                else:
                    print('syntax test PASS')
                    # /!\ side -effect of debug_syntaxcheck is that references on (init_f,update_f,exit_f) changed

                    # TODO ensure that references on init_f, update_f and exit_f have changed indeed
                    vms.recover = False
                    vms.debugging_scr = cartname  # on indique que la VM devra exec ça en mode debug
                    sharedstuffxxxx.kartridge_output = [2, '+DEBUGMODE+']

                # clear keyboard cache and clear event queue
                # trashevents = pygame.event.get()
                # kengi.event.EventManager.instance().update()
                return

            elif uholding_ctrl and ev.key == pygame.K_s:
                # ds tous les cas faut refresh
                # # RUN WITHOUT a vm
                #
                # TODO need to refresh so the editor can re-split if the user enters
                # a new comment in the form # >>>myfile.py during cartridge edition

                self._mod._try_save_file(katasdk.get_vmstate().cedit_arg)

            elif uholding_ctrl and ev.key == pygame.K_d:  # charge contenu de thing.py
                self._view.cached_rendering_list = None
                self._mod.switch_file()

            else:
                self._handle_keyb_input(ev, pressed_keys, False)  # 0 if self.latest_t is None else self.latest_t)

    def _handle_keyb_input(self, event, allkeys, unknown):
        # ___ COMBINATION KEY INPUTS ___
        # Functionality whether something is highlighted or not (highlight all / paste)
        ctrl_key_pressed = allkeys[pygame.K_LCTRL] or allkeys[pygame.K_RCTRL]
        if ctrl_key_pressed and event.key == pygame.K_a:
            self._blob.highlight_all()

        # elif ctrl_key_pressed and event.key == pygame.K_n:
        #    self._mod.switch_file()  # edit next vfile

        elif ctrl_key_pressed and event.key == pygame.K_z:
            # TODO implement undo operation
            print('undo not implemented yet!')
            pass

        elif ctrl_key_pressed and event.key == pygame.K_v:
            self.handle_highlight_and_paste()

        # ---------------
        #  temporarily disabled features : save stuff, copy/past
        # ---------------
        # elif ctrl_key_pressed and event.key == pygame.K_s:
        #     print('**SAVE detected**')
        #     sharedstuff.disp_save_ico = tinfo + SAVE_ICO_LIFEDUR
        #     sharedstuff.dump_content = self._blob.get_text_as_string()
        #
        # # Functionality for when something is highlighted (cut / copy)
        # elif self.dragged_finished and self.dragged_active:
        #     if (pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]) and event.key == pygame.K_x:
        #         self.handle_highlight_and_cut()
        #     elif (pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]) and event.key == pygame.K_c:
        #         self.handle_highlight_and_copy()
        #     else:
        #         self.handle_input_with_highlight(event)

        # ___ SINGLE KEY INPUTS ___
        else:
            numpad_ope = [
                pygame.K_KP_PERIOD, pygame.K_KP_DIVIDE, pygame.K_KP_MULTIPLY,
                pygame.K_KP_MINUS, pygame.K_KP_PLUS, pygame.K_KP_EQUALS
            ]

            self._mod.reset_text_area_to_caret()  # reset visual area to include line of caret if necessary
            self._mod.chosen_LetterIndex = int(self._mod.chosen_LetterIndex)

            # ___ DELETIONS ___
            if event.unicode == '\x08':  # K_BACKSPACE
                self._mod.handle_keyboard_backspace()
                self._mod.reset_text_area_to_caret()  # reset caret if necessary
                self._view.cached_rendering_list = None

            elif event.unicode == '\x7f':  # K_DELETE
                self._mod.handle_keyboard_delete()
                self._mod.reset_text_area_to_caret()  # reset caret if necessary
                self._view.cached_rendering_list = None

            # ___ NORMAL KEYS ___
            # This covers all letters and numbers (not those on numpad).
            elif len(pygame.key.name(event.key)) == 1:
                self._mod.insert_unicode(event.unicode)
                self._view.cached_rendering_list = None
            elif event.unicode == '_':
                self._mod.insert_unicode('_')
                self._view.cached_rendering_list = None

            # TODO enable numpad keys again, once the ktg VM is clean
            # ___ NUMPAD KEYS ___
            # for the numbers, numpad must be activated (mod = 4096)
            # elif event.mod == 4096 and 1073741913 <= event.key <= 1073741922:
            #    self.insert_unicode(event.unicode)

            # all other numpad keys can be triggered with & without mod
            elif event.key in numpad_ope:
                self.insert_unicode(event.unicode)
                self._view.cached_rendering_list = None

            # ___ SPECIAL KEYS ___
            elif event.key == pygame.K_TAB:  # TABULATOR
                for _ in range(4):  # four spaces
                    self._mod.handle_keyboard_space()

            elif event.key == pygame.K_SPACE:  # SPACEBAR
                self._mod.handle_keyboard_space()
                self._view.cached_rendering_list = None

            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:  # RETURN
                self._mod.handle_keyboard_return()
                self._view.cached_rendering_list = None

            # ------------------------------
            #  arrow keys
            # ------------------------------
            else:
                tmp_arr = [
                    pygame.K_RSHIFT, pygame.K_LSHIFT, pygame.K_DELETE,
                    pygame.K_BACKSPACE, pygame.K_CAPSLOCK, pygame.K_LCTRL,
                    pygame.K_RCTRL]
                if event.key not in tmp_arr:
                    # We handled the keys separately
                    # Capslock is apparently implicitly handled
                    # when using it in combination
                    print('*WARNING* No implementation for key: ', end='')
                    print(pygame.key.name(event.key))
        return False


# ----------------------------------------
#  BODY
# @katasdk.tag_gameenter
def game_enter(vmstate):
    global lu_event, paint_ev, e_manager, sharedstuffxxxx
    # reset global variables for the Editor cartridge
    sharedstuffxxxx = Sharedstuff()

    kengi.init(2)
    lu_event = kengi.event.CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_ev = kengi.event.CgmEvent(EngineEvTypes.PAINT, screen=None)
    paint_ev.screen = kengi.get_surface()
    e_manager = kengi.event.EventManager.instance()

    # nécessairement lancé via VM
    # => soit on edite "editor" soit ce qui se trouve dans vmstate.cedit_arg
    # RQ: ce qui se trouve dans cedit_arg peut ne pas exister!
    # if vmstate is None:
    # provider = ScProviderFactory.build(local_target='LoremIpsum.py')
    # pycode_vfileset = VirtualFilesetBuffer(provider.get_source_code()) - comment: just like a LoremIpsum.py ...
    # dummy_file = True
    # else:
    if (vmstate is None) or vmstate.cedit_arg is None:
        # on peut pogner l'editeur pour montrer son code
        fileinfo = 'editor'
    else:
        fileinfo = vmstate.cedit_arg
    print('*** editor va ouvrir ', fileinfo)

    # - fetch code for editing
    if (vmstate is not None) and vmstate.has_game(fileinfo):
        file_exists = True
        # curr_edition_info = '(editing an existing file {})'.format(fileinfo)
        # AJOUT mercredi 20/04/22 ca peut que marcher en local cela!
        with open(f'{DIR_CARTRIDGES}/{fileinfo}.py', 'r') as ff:
            py_sourcecode = ff.read()
            pycode_vfileset = VirtualFilesetBuffer(py_sourcecode)

    else:  # game creation
        file_exists = False
        # curr_edition_info = '(creating the new file {})'.format(fileinfo)
        py_sourcecode = ScProviderFactory.DUMMY_PYCODE
        pycode_vfileset = VirtualFilesetBuffer(py_sourcecode)

    scr_size = paint_ev.screen.get_size()
    offset_x = 0  # offset from the left border of the pygame window
    offset_y = 38  # offset from the top border of the pygame window
    editor_blob = EditorModel(
        offset_x, offset_y, scr_size[0], scr_size[1] - offset_y, show_line_no=True
    )
    editor_blob.stored_cart_name = fileinfo

    # imagine a debug (spe run/preview) has occured and ended with errors, we need to forward the info now
    if (vmstate is not None) and len(vmstate.exception_info):
        editor_blob.topbar_info_msg = vmstate.exception_info
        vmstate.exception_info = []

    # set only one text editor_blob.set_text_from_list(pycode_vfileset['main.py'])
    editor_blob.set_fileset(pycode_vfileset)

    editor_view = CapelloEditorView(editor_blob)
    editor_view.set_bg_color(pygame.color.Color('midnightblue'))
    editor_view.set_syntax_highlighting(True)
    if file_exists:
        if vmstate.has_ro_flag(fileinfo):
            editor_view.locked_file = True

    sharedstuffxxxx.file_label = None
    # editor_blob.currentfont.render(f'opened file= {fileinfo}', False, (0, 250, 0))
    sharedstuffxxxx.screen = kengi.get_surface()
    editor_blob.currentfont = pygame.font.Font(None, 24)
    editor_view.turn_on()

    # {C}
    ectrl = EditorCtrl(editor_blob, editor_view, sharedstuffxxxx)
    ectrl.turn_on()


# @katasdk.tag_gameupdate
def game_update(t_info=None):
    global lu_event, paint_ev, e_manager
    lu_event.curr_t = t_info
    e_manager.post(lu_event)
    e_manager.post(paint_ev)
    e_manager.update()
    kengi.flip()
    if sharedstuffxxxx.kartridge_output:
        return sharedstuffxxxx.kartridge_output


# @katasdk.tag_gameexit
def game_exit(vmstate):
    # this was done on exit before 25/08/22,
    # now its done directly in the Save function
    # if vmstate:
    #     if vmstate.cedit_arg is not None and sharedstuff_obj.dump_content is not None:
    #         # has to be shared with the VM too
    #         # Let's hack the .cedit_arg attribute and use it as a return value container
    #         vmstate.cedit_arg = katasdk.mt_a + vmstate.cedit_arg + katasdk.mt_b + sharedstuff_obj.dump_content
    #         print('.cedit_arg hacked!')
    print('---------------------- Editor, over ----------------------------')
    kengi.quit()


if __name__ == '__main__':
    gameover = False
    game_enter(None)
    while not gameover:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(None)
