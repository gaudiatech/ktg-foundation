import math
import katagames_sdk as katasdk
katasdk.bootstrap()
kengi = katasdk.kengi
EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame


# - constants
# TODO: let's code a very crude formatting
# one can display keywords simply by using a boldface font
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
DUMMY_PYCODE = """
# Define the cloud object by extending pygame.sprite.Sprite
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
"""

# RQ: to inject text into the editor use either:
# set_text_from_list(self, text_list)
# or
# def set_text_from_string(self, string):

# -------------- editor starts ---------------
# temp (local tinkering)
# import os
# os.chdir('../')


SAVE_ICO_LIFEDUR = 0.77  # sec


class Pyperclip:  # simulation
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


class TextEditor:  # (kengi.event.EventReceiver):
    # ++++++++++ Scroll functionality
    def display_scrollbar(self):
        if len(self.line_string_list) > self.showable_line_numbers_in_editor:
            # scroll bar is a fraction of the space
            w = self.scrollBarWidth

            # line below: -2 for space between edge & scrollbar
            x = self.editor_offset_X + self.textAreaWidth - self.scrollBarWidth - 2
            y = self.editor_offset_Y + (w / 2) + (self.textAreaHeight * ((self.showStartLine * 1.0) / self.maxLines))
            y = int(y)
            h = (self.textAreaHeight - w) * ((self.showable_line_numbers_in_editor * 1.0) / self.maxLines)
            h = int(h)

            self.scrollbar = pygame.Rect(x, y, w, h)
            # actual scrollbar
            pygame.draw.rect(self.screen, self.color_scrollbar, self.scrollbar)
            # bottom round corner
            pygame.draw.circle(self.screen, self.color_scrollbar, (int(x + (w / 2)), y + h), int(w / 2))
        else:  # if scrollbar is not needed, don't show
            self.scrollbar = None

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
        self.update_caret_position()  # update caret position to chosen_Index (Line+Letter)
        self.last_clickdown_cycle = 0  # reset drag-cycle
        self.last_clickup_cycle = -1
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

    # +++++++++++++++ input handling MOUSE
    def handle_mouse_input(self, pygame_events, mouse_x, mouse_y, mouse_pressed) -> None:
        """
        Handles mouse input based on mouse events (Buttons down/up + coordinates).
        Handles drag-and-drop-select as well as single-click.
        The code only differentiates the single-click only as so far, that
            the DOWN-event is on the same position as the UP-event.

        Implemented so far:
        - left-click (selecting as drag-and-drop or single-click)
        - mouse-wheel (scrolling)
        """

        for event in pygame_events:
            # ___ MOUSE CLICKING DOWN ___ #
            # Scrollbar-handling
            if event.type == pygame.MOUSEBUTTONDOWN and not self.mouse_within_texteditor(mouse_x, mouse_y):
                if self.scrollbar is not None:
                    if self.scrollbar.collidepoint(mouse_x, mouse_y):
                        self.scroll_start_y = mouse_y
                        self.scroll_dragging = True

            # Mouse scrolling wheel should only work if it is within the coding area (excluding scrollbar area)
            if event.type == pygame.MOUSEBUTTONDOWN and self.mouse_within_texteditor(mouse_x, mouse_y):
                # ___ MOUSE SCROLLING ___ #
                if event.button == 4 and self.showStartLine > 0:
                    self.scrollbar_up()
                elif event.button == 5 and self.showStartLine + self.showable_line_numbers_in_editor < self.maxLines:
                    self.scrollbar_down()

                # ___ MOUSE LEFT CLICK DOWN ___ #
                elif event.button == 1:  # left mouse button
                    if not self.click_hold:
                        # in order not to have the mouse move around after a click,
                        # we need to disable this function until we RELEASE it.
                        self.last_clickdown_cycle = self.cycleCounter
                        self.click_hold = True
                        self.dragged_active = True
                        self.dragged_finished = False
                        if self.mouse_within_texteditor(mouse_x, mouse_y):  # editor area
                            if self.mouse_within_existing_lines(mouse_y):  # in area of existing lines
                                self.set_drag_start_by_mouse(mouse_x, mouse_y)
                            else:  # clicked below the existing lines
                                self.set_drag_start_after_last_line()
                            self.update_caret_position_by_drag_start()
                        else:  # mouse outside of editor, don't care.
                            pass

            # ___ MOUSE LEFT CLICK UP ___ #
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:

                self.scroll_dragging = False  # reset scroll (if necessary)

                if self.click_hold:
                    # mouse dragging only with left mouse up
                    # mouse-up only valid if we registered a mouse-down within the editor via click_hold earlier

                    self.last_clickup_cycle = self.cycleCounter
                    self.click_hold = False

                    if self.mouse_within_texteditor(mouse_x, mouse_y):  # editor area
                        if self.mouse_within_existing_lines(mouse_y):  # in area of existing lines
                            self.set_drag_end_by_mouse(mouse_x, mouse_y)
                        else:  # clicked beneath the existing lines
                            self.set_drag_end_after_last_line()
                        self.update_caret_position_by_drag_end()

                    else:  # mouse-up outside of editor
                        if mouse_y < self.editor_offset_Y:
                            # Mouse-up above editor -> set to first visible line
                            self.drag_chosen_LineIndex_end = self.showStartLine
                        elif mouse_y > (self.editor_offset_Y + self.textAreaHeight - self.conclusionBarHeight):
                            # Mouse-up below the editor -> set to last visible line
                            if self.maxLines >= self.showable_line_numbers_in_editor:
                                xxy = self.showStartLine + self.showable_line_numbers_in_editor - 1
                                self.drag_chosen_LineIndex_end = xxy
                            else:
                                self.drag_chosen_LineIndex_end = self.maxLines - 1
                        else:  # mouse left or right of the editor outside
                            self.set_drag_end_line_by_mouse(mouse_y)
                        # Now we can determine the letter based on mouse_x (and selected line within the function)
                        self.set_drag_end_letter_by_mouse(mouse_x)

            # _______ CHECK FOR MOUSE DRAG AND HANDLE CLICK _______ #
            if (self.last_clickup_cycle - self.last_clickdown_cycle) >= 0:
                # Clicked the mouse lately and has not been handled yet.
                # To differentiate between click and drag we check whether the down-click
                # is on the same letter and line as the up-click!
                # We set the boolean variables here and handle the caret positioning.
                if self.drag_chosen_LineIndex_end == self.drag_chosen_LineIndex_start and \
                        self.drag_chosen_LetterIndex_end == self.drag_chosen_LetterIndex_start:
                    self.dragged_active = False  # no letters are actually selected -> Actual click
                else:
                    self.dragged_active = True  # Actual highlight

                self.dragged_finished = True  # we finished the highlighting operation either way

                # handle caret positioning
                self.chosen_LineIndex = self.drag_chosen_LineIndex_end
                self.chosen_LetterIndex = self.drag_chosen_LetterIndex_end
                self.update_caret_position()

                # reset after upclick so we don't execute this block again and again.
                self.last_clickdown_cycle = 0
                self.last_clickup_cycle = -1

        # Scrollbar - Dragging
        if mouse_pressed[0] == 1 and self.scroll_dragging:
            # left mouse is being pressed after click on scrollbar
            if mouse_y < self.scroll_start_y and self.showStartLine > 0:
                # dragged higher
                self.scrollbar_up()
            elif mouse_y > self.scroll_start_y \
                    and self.showStartLine + self.showable_line_numbers_in_editor < self.maxLines:
                # dragged lower
                self.scrollbar_down()

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
        # X Position
        self.cursor_X = self.xline_start + (self.drag_chosen_LetterIndex_start * self.letter_size_X)
        # Y Position
        self.cursor_Y = self.editor_offset_Y
        self.cursor_Y += self.drag_chosen_LineIndex_start * self.line_gap
        self.cursor_Y -= self.showStartLine * self.lineHeight

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

    def get_single_color_dicts(self):  # -> List[List[Dict]]
        """
        Converts the text in the editor based on the line_string_list into a list of lists of dicts.
        Every line is one sublist.
        Since only one color is being applied, we create a list with one dict per line.
        """
        rendering_list = []
        for line in self.line_string_list:
            # appends a single-item list
            rendering_list.append([{'chars': line, 'type': 'normal', 'color': self.textColor}])
        return rendering_list

    def set_line_numbers(self, b) -> None:
        """
        Activates/deactivates showing the line numbers in the editor
        """
        self.displayLineNumbers = b
        if self.displayLineNumbers:
            self.lineNumberWidth = 27  # line number background width and also offset for text!
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

    def __init__(self, offset_x, offset_y, text_area_width, text_area_height, scr, line_numbers_flag=False):
        self.screen = scr

        # kengi+sdk flavored font obj
        self.currentfont = kengi.gui.ImgBasedFont('editor/myassets/gibson1_font.png', (87, 77, 11))
        self.letter_size_Y = self.currentfont.get_linesize()

        self._prev_mouse_x, self._prev_mouse_y = 0, 0

        # VISUALS
        self.txt_antialiasing = 0
        self.editor_offset_X = offset_x
        self.editor_offset_Y = offset_y
        self.textAreaWidth = text_area_width
        self.textAreaHeight = text_area_height
        self.conclusionBarHeight = 18
        letter_width = self.currentfont.render(" ", self.txt_antialiasing, (0, 0, 0)).get_width()
        self.letter_size_X = letter_width
        self.carret_img = pygame.image.load('editor/myassets/Trennzeichen.png').convert_alpha()

        # LINES
        self.Trenn_counter = 0
        self.MaxLinecounter = 0
        self.line_string_list = []  # LOGIC: Array of actual Strings
        self.lineHeight = self.letter_size_Y

        # self.maxLines is the variable keeping count how many lines we currently have -
        # in the beginning we fill the entire editor with empty lines.
        self.maxLines = 20  #int(math.floor(self.textAreaHeight / self.lineHeight))
        self.showStartLine = 0  # first line (shown at the top of the editor) <- must be zero during init!

        linespacing = 2
        self.line_gap = self.letter_size_Y + linespacing
        self.showable_line_numbers_in_editor = int(math.floor(self.textAreaHeight / self.line_gap))

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
            self.lineNumberWidth = 27  # line number background width and also offset for text!
        else:
            self.lineNumberWidth = 0
        self.line_numbers_Y = self.editor_offset_Y

        # TEXT COORDINATES
        self.chosen_LineIndex = 0
        self.chosen_LetterIndex = 0
        self.yline_start = self.editor_offset_Y + 1  # +1 is here so we can align line numbers & txtcontent surfaces

        self.yline = self.editor_offset_Y
        self.xline_start_offset = 28
        if self.displayLineNumbers:
            self.xline_start = self.editor_offset_X + self.xline_start_offset
            self.xline = self.editor_offset_X + self.xline_start_offset
        else:
            self.xline_start = self.editor_offset_X
            self.xline = self.editor_offset_X

        # CURSOR - coordinates for displaying the caret while typing
        self.cursor_Y = self.editor_offset_Y
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

        # Colors
        self.codingBackgroundColor = (40, 41, 41)
        self.codingScrollBarBackgroundColor = (49, 50, 50)
        self.lineNumberColor = (255, 255, 255)
        self.lineNumberBackgroundColor = (60, 61, 61)
        self.textColor = (255, 255, 255)
        self.color_scrollbar = (60, 61, 61)

        self.lexer = None  # PythonLexer()
        self.formatter = None  # ColorFormatter()
        # there's only dark scheme
        # self.set_colorscheme(style)

        # Key input variables+
        self.key_initial_delay = 300
        self.key_continued_intervall = 30
        pygame.key.set_repeat(self.key_initial_delay, self.key_continued_intervall)

        # Performance enhancing variables
        self.firstiteration_boolean = True
        self.rerenderLineNumbers = True
        self.click_hold = False
        self.cycleCounter = 0  # Used to be able to tell whether a mouse-drag action has been handled already or not.

        self.clock = pygame.time.Clock()
        self.FPS = 60  # we need to limit the FPS so we don't trigger the same actions too often (e.g. deletions)

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
            pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def highlight_from_start_to_letter(self, line, letter) -> None:
        """
        Highlight from the beginning of a line to a specific letter by index.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, 0)
            x2, y2 = self.get_rect_coord_from_indizes(line, letter)
            pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def highlight_entire_line(self, line) -> None:
        """
        Full highlight of the entire line - first until last letter.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, 0)
            x2, y2 = self.get_rect_coord_from_indizes(line, len(self.line_string_list[line]))
            pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

    def highlight_from_letter_to_letter(self, line, letter_start, letter_end) -> None:
        """
        Highlights within a single line from letter to letter by indizes.
        """
        if self.line_is_visible(line):
            x1, y1 = self.get_rect_coord_from_indizes(line, letter_start)
            x2, y2 = self.get_rect_coord_from_indizes(line, letter_end)
            pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(x1, y1, x2 - x1, self.line_gap))

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

    def render_highlight(self, mouse_x, mouse_y) -> None:
        """
        Renders highlighted area:
        1. During drag-action -> area starts at drag_start and follows mouse
        2. After drag-action -> area stays confined to selected area by drag_start and drag_end
        """

        if self.dragged_active:  # some text is highlighted or being highlighted
            line_start = self.drag_chosen_LineIndex_start
            letter_start = self.drag_chosen_LetterIndex_start

            if self.dragged_finished:  # highlighting operation is done, user "clicked-up" with the left mouse button
                line_end = self.drag_chosen_LineIndex_end
                letter_end = self.drag_chosen_LetterIndex_end
                if letter_end < 0:
                    letter_end = 0
                self.highlight_lines(line_start, letter_start, line_end, letter_end)  # Actual highlighting

            else:  # active highlighting -> highlighted area follows mouse movements
                line_end = self.get_line_index(mouse_y)
                letter_end = self.get_letter_index(mouse_x)
                # adapt line_end: if mouse_y below showable area / existing lines,
                if line_end >= self.get_showable_lines():
                    line_end = self.get_showable_lines() - 1  # select last showable/existing line as line_end

                # Correct letter_end based on cursor position / letters in the cursor's line
                if letter_end < 0:  # cursor is left of the line
                    letter_end = 0
                elif letter_end > len(self.line_string_list[line_end]):
                    letter_end = len(self.line_string_list[line_end])

                self.highlight_lines(line_start, letter_start, line_end, letter_end)  # Actual highlighting

    #def proc_event(self, ev, source):
    def use_events(self, pygame_events, pressed_keys, shared, tinfo=None):
        # needs to be called within a while loop to be able to catch key/mouse input 'n update visuals throughout use
        self.cycleCounter = self.cycleCounter + 1
        # first iteration
        tmp = (self.editor_offset_X, self.editor_offset_Y, self.textAreaWidth, self.textAreaHeight)
        if self.firstiteration_boolean:
            # paint entire area to avoid pixel error beneath line numbers
            pygame.draw.rect(self.screen, self.codingBackgroundColor, tmp)
            self.firstiteration_boolean = False

        self.handle_keyboard_input(pygame_events, pressed_keys, shared, tinfo)

        mouse_pressed = pygame.mouse.get_pressed()
        mouse_x, mouse_y = kengi.core.proj_to_vscreen(pygame.mouse.get_pos())
        self._prev_mouse_x, self._prev_mouse_y = mouse_x, mouse_y
        self.handle_mouse_input(pygame_events, mouse_x, mouse_y, mouse_pressed)

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
        self.line_string_list = string.split('\n')
        self.maxLines = len(self.line_string_list)
        self.rerenderLineNumbers = True

    # --------------------------------------------------------------------
    #   KEYB MANAGEMENT
    # --------------------------------------------------------------------

    def handle_keyboard_input(self, pygame_events, pressed_keys, shstuff, tinfo=None):

        for event in pygame_events:
            if event.type == pygame.KEYDOWN:
                ctrl_k_pressed = pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]
                # alt_pressed = pressed_keys[pygame.K_RALT] or pressed_keys[pygame.K_LALT]

                # how to exit prog
                if event.key == pygame.K_ESCAPE:
                    shstuff.kartridge_output = [2, 'niobepolis']
                    return True

                # ___ COMBINATION KEY INPUTS ___
                # Functionality whether something is highlighted or not (highlight all / paste)
                elif ctrl_k_pressed and event.key == pygame.K_a:
                    self.highlight_all()
                elif ctrl_k_pressed and event.key == pygame.K_v:
                    self.handle_highlight_and_paste()
                elif ctrl_k_pressed and event.key == pygame.K_s:
                    print('**SAVE detected**')
                    shstuff.disp_save_ico = tinfo + SAVE_ICO_LIFEDUR
                    shstuff\
                        .dump_content = self.get_text_as_string()

                # Functionality for when something is highlighted (cut / copy)
                elif self.dragged_finished and self.dragged_active:
                    if (pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]) and event.key == pygame.K_x:
                        self.handle_highlight_and_cut()
                    elif (pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]) and event.key == pygame.K_c:
                        self.handle_highlight_and_copy()
                    else:
                        self.handle_input_with_highlight(event)  # handle char input on highlight

                # ___ SINGLE KEY INPUTS ___
                else:
                    numpad_ope = [
                        pygame.K_KP_PERIOD, pygame.K_KP_DIVIDE, pygame.K_KP_MULTIPLY,
                        pygame.K_KP_MINUS, pygame.K_KP_PLUS, pygame.K_KP_EQUALS
                    ]

                    self.reset_text_area_to_caret()  # reset visual area to include line of caret if necessary
                    self.chosen_LetterIndex = int(self.chosen_LetterIndex)

                    # print("event", event)

                    # Detect tapping/holding of the "DELETE" and "BACKSPACE" key while something is highlighted
                    if self.dragged_finished and self.dragged_active and \
                            (event.unicode == '\x08' or event.unicode == '\x7f'):
                        # create the uniform event for both keys so we don't have to write two functions
                        deletion_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE)
                        self.handle_input_with_highlight(
                            deletion_event)  # delete and backspace have the same functionality

                    # ___ DELETIONS ___
                    elif event.unicode == '\x08':  # K_BACKSPACE
                        self.handle_keyboard_backspace()
                        self.reset_text_area_to_caret()  # reset caret if necessary
                    elif event.unicode == '\x7f':  # K_DELETE
                        self.handle_keyboard_delete()
                        self.reset_text_area_to_caret()  # reset caret if necessary

                    # ___ NORMAL KEYS ___
                    # This covers all letters and numbers (not those on numpad).
                    elif len(pygame.key.name(event.key)) == 1:
                        self.insert_unicode(event.unicode)
                    elif event.unicode == '_':
                        self.insert_unicode('_')

                    # TODO enable numpad keys again, once the ktg VM is clean
                    # ___ NUMPAD KEYS ___
                    # for the numbers, numpad must be activated (mod = 4096)
                    # elif event.mod == 4096 and 1073741913 <= event.key <= 1073741922:
                    #    self.insert_unicode(event.unicode)

                    # all other numpad keys can be triggered with & without mod
                    elif event.key in numpad_ope:
                        self.insert_unicode(event.unicode)

                    # ___ SPECIAL KEYS ___
                    elif event.key == pygame.K_TAB:  # TABULATOR
                        self.handle_keyboard_tab()
                    elif event.key == pygame.K_SPACE:  # SPACEBAR
                        self.handle_keyboard_space()
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:  # RETURN
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
                        if event.key not in [pygame.K_RSHIFT, pygame.K_LSHIFT, pygame.K_DELETE,
                                             pygame.K_BACKSPACE, pygame.K_CAPSLOCK, pygame.K_LCTRL, pygame.K_RCTRL]:
                            # We handled the keys separately
                            # Capslock is apparently implicitly handled
                            # when using it in combination
                            print('*WARNING* No implementation for key: ', end='')
                            print(pygame.key.name(event.key))
        return False

    def insert_unicode(self, unicode) -> None:
        self.line_string_list[self.chosen_LineIndex] = self.line_string_list[self.chosen_LineIndex][
                                                       :self.chosen_LetterIndex] + unicode + \
                                                       self.line_string_list[self.chosen_LineIndex][
                                                       self.chosen_LetterIndex:]
        self.cursor_X += self.letter_size_X
        self.chosen_LetterIndex += 1

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
        paste_string = Pyperclip.paste()
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
        Pyperclip.copy(copy_string)

    def handle_highlight_and_cut(self):
        """
        Copy highlighted String into clipboard if anything is highlighted, else no action.
        Delete highlighted part of the text.
        """
        # Copy functionality
        copy_string = self.get_highlighted_characters()  # copy characters
        Pyperclip.copy(copy_string)

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

    # --------------- future vue ----------------------
    def do_paint(self):
        # RENDERING 1 - Background objects
        self.render_background_coloring()
        self.render_line_numbers()

        # RENDERING 2 - Lines
        self.render_highlight(self._prev_mouse_x, self._prev_mouse_y)

        # single-color text
        list_of_dicts = self.get_single_color_dicts()
        self.render_line_contents_by_dicts(list_of_dicts)

        self.render_caret()
        self.display_scrollbar()
        self.clock.tick(self.FPS)

    def render_background_coloring(self) -> None:
        """
        Renders background color of the text area.
        """
        bg_left = self.editor_offset_X + self.lineNumberWidth
        bg_top = self.editor_offset_Y
        bg_width = self.textAreaWidth - self.lineNumberWidth
        bg_height = self.textAreaHeight
        pygame.draw.rect(self.screen, self.codingBackgroundColor, (bg_left, bg_top, bg_width, bg_height))

    def render_line_numbers(self):
        """
        While background rendering is done for all "line-slots"
        (to overpaint remaining "old" numbers without lines)
        we render line-numbers only for existing string-lines.
        """
        if self.displayLineNumbers and self.rerenderLineNumbers:
            self.rerenderLineNumbers = False
            line_numbers_y = self.editor_offset_Y  # init for first line
            for x in range(self.showStartLine, self.showStartLine + self.showable_line_numbers_in_editor):

                # background
                r = (self.editor_offset_X, line_numbers_y, self.lineNumberWidth, self.line_gap)
                pygame.draw.rect(self.screen, self.lineNumberBackgroundColor, r)  # to debug use: ,1) after r

                # line number
                if x < self.get_showable_lines():
                    # x + 1 in order to start with line 1 (only display, logical it's the 0th item in the list
                    text = self.currentfont.render(str(x + 1).zfill(2), self.txt_antialiasing, self.lineNumberColor)
                    text_rect = text.get_rect()
                    text_rect.center = pygame.Rect(r).center
                    self.screen.blit(text, text_rect)  # render on center of bg block
                line_numbers_y += self.line_gap

    def render_line_contents_by_dicts(self, dicts) -> None:
        # Preparation of the rendering:
        self.yline = self.yline_start
        first_line = self.showStartLine
        if self.showable_line_numbers_in_editor < len(self.line_string_list):
            # we got more text than we are able to display
            last_line = self.showStartLine + self.showable_line_numbers_in_editor
        else:
            last_line = self.maxLines

        # Actual line rendering based on dict-keys
        for line_list in dicts[first_line: last_line]:
            xcoord = self.xline_start
            for a_dict in line_list:
                surface = self.currentfont.render(a_dict['chars'], self.txt_antialiasing,
                                                  a_dict['color'])  # create surface
                self.screen.blit(surface, (xcoord, self.yline))  # blit surface onto screen
                xcoord = xcoord + (len(a_dict['chars']) * self.letter_size_X)  # next line-part prep

            self.yline += self.line_gap  # next line prep

    def render_caret(self):
        """
        Called every frame. Displays a cursor for x frames, then none for x frames. Only displayed if line in which
        caret resides is visible and there is no active dragging operation going on.
        Dependent on FPS -> 5 intervalls per second
        Creates 'blinking' animation
        """
        self.Trenn_counter += 1
        if self.Trenn_counter > (self.FPS / 5) and self.caret_within_texteditor() and self.dragged_finished:
            self.screen.blit(self.carret_img, (self.cursor_X, self.cursor_Y))
            self.Trenn_counter = self.Trenn_counter % ((self.FPS / 5) * 2)
# -------------- end of editor ---------------


class Sharedstuff:
    def __init__(self):
        self.disp_save_ico = None  # contains info 'bout time when it needs display
        self.dump_content = None
        self.kartridge_output = None
        self.screen = None
        self.editor = None
        self.file_label = None  # for showing what is being edited
        self.dirtymodel = None


ico_surf = None
scr_size = None
icosurf_pos = None
e_manager = None
lu_event = p_event = None
editor_text_content = ''
formatedtxt_obj = None
gameover = False
sharedstuff = None


class CustomGameTicker:
    def __init__(self):
        self.lu_event = kengi.event.CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
        self.paint_event = kengi.event.CgmEvent(EngineEvTypes.PAINT, screen=kengi.get_surface())
        self.manager = kengi.event.EventManager.instance()

    def refresh(self):
        self.manager.post(self.lu_event)
        self.manager.post(self.paint_event)
        self.manager.update()


ticker = None


# - functions for the web -
def game_enter(vmstate):
    global sharedstuff, ticker, ico_surf, scr_size, icosurf_pos
    katasdk.set_mode('old_school')

    sharedstuff = Sharedstuff()
    sharedstuff.screen = kengi.get_surface()
    scr_size = sharedstuff.screen.get_size()

    ico_surf = pygame.image.load('editor/myassets/saveicon.png')
    tt = ico_surf.get_size()
    icosurf_pos = ((scr_size[0]-tt[0])//2, (scr_size[1]-tt[1])//2)

    offset_x = 0  # offset from the left border of the pygame window
    offset_y = 10  # offset from the top border of the pygame window

    ticker = CustomGameTicker()

    # Instantiation
    # TX.set_line_numbers(True)  # if you wish to change flag afterwards

    # set text content for the editor
    if vmstate and vmstate.cedit_arg is not None:  # on peut pogner une cible a editer!
        fileinfo = vmstate.cedit_arg
        if vmstate.cedit_arg in vmstate.gamelist_func():
            infomsg = '** edit existing file {} **'.format(vmstate.cedit_arg)
            # AJOUT mercredi 20/04/22 ca peut que marcher en local cela!
            f = open(f'roms/{fileinfo}.py', 'r')
            py_code = f.read()
            f.close()

        else:  # game creation
            infomsg = '** creating new file {} **'.format(vmstate.cedit_arg)
            py_code = vmstate.blankfile_template
        print(infomsg)
    else:
        fileinfo = '?'
        py_code = DUMMY_PYCODE  # just a sample, like just like a LoremIpsum.py ...

    # another way to do it --------------
    # ajout dimanche 10.04
    # f = open(PATH_SRC_FILE, 'r')
    # editor_text_content = f.read()
    # f.close()
    # formatedtxt_obj = SFText(screen, editor_text_content,
    # run precursor alone
    #    font_path='editor0/fonts/')
    # xxx -> 'editor/**assets/gibson0_font.png'
    # if vmstate:
    #    print('***** editing file ******* {}'.format(vmstate.cedit_arg))
    #    ft = kengi.gui.ImgBasedFont(xxx, (0, 0, 250))
    #    tt = ft.render('bidule: ' + vmstate.cedit_arg, False, (0, 250, 0))
    # ------------

    sharedstuff.dirtymodel = TextEditor(
        offset_x, offset_y, scr_size[0], scr_size[1]-offset_y, kengi.get_surface(), line_numbers_flag=True
    )
    # sharedstuff.dirtymodel.turn_on()

    sharedstuff.file_label = sharedstuff.dirtymodel.currentfont.render(f'opened file= {fileinfo}', False, (0, 250, 0))
    sharedstuff.dirtymodel.set_text_from_string(py_code)

    # sharedstuff.viewer = EditorView(offset_x, offset_y, ssize[0], ssize[1]-offset_y)
    # sharedstuff.viewer.turn_on()


def game_update(t_info=None):
    global gameover, sharedstuff, ticker
    scr = sharedstuff.screen
    if sharedstuff.dirtymodel.use_events(pygame.event.get(), pygame.key.get_pressed(), sharedstuff, t_info):
        gameover = True
        return
    if sharedstuff.kartridge_output:
        gameover = True
        return sharedstuff.kartridge_output

    sharedstuff.dirtymodel.do_paint()
    # ticker.refresh()

    if sharedstuff.disp_save_ico:
        if t_info > sharedstuff.disp_save_ico:
            sharedstuff.disp_save_ico = None
        scr.blit(ico_surf, icosurf_pos)

    scr.blit(sharedstuff.file_label, (0, 0))
    kengi.flip()


def game_exit(vmstate):
    global sharedstuff
    if vmstate.cedit_arg is not None and sharedstuff.dump_content is not None:
        # has to be shared with the VM, too
        # let's hack the .cedit_arg attribute, use it as a return value container
        vmstate.cedit_arg = katasdk.mt_a + vmstate.cedit_arg + katasdk.mt_b + sharedstuff.dump_content
        print('.cedit_arg hacked!')
    kengi.quit()
    print('sortie de lediteur!')


# --------------------------------------------
#  Entry pt, local ctx
# --------------------------------------------
import time
if __name__ == '__main__':
    game_enter(katasdk.vmstate)
    while not gameover:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(katasdk.vmstate)
