import math

import pygame


def set_key_repetition(self, delay=300, intervall=30):
    """
    The delay parameter is the number of milliseconds before the first repeated pygame.KEYDOWN event will be sent.
    After that, another pygame.KEYDOWN event will be sent every interval milliseconds.
    """
    self.key_initial_delay = delay
    self.key_continued_intervall = intervall
    pygame.key.set_repeat(self.key_initial_delay, self.key_continued_intervall)


def set_font_size(self, size=16):
    """
    Sets the given size as font size and re-calculates necessary changes.
    """
    self.letter_size_Y = size
    # current_dir = os.path.dirname(__file__)
    self.courier_font = pygame.font.SysFont('courier', self.letter_size_Y)
    letter_width = self.courier_font.render(" ", self.aa_option, (0, 0, 0)).get_width()
    self.letter_size_X = letter_width
    self.line_gap = 3 + self.letter_size_Y
    self.showable_line_numbers_in_editor = int(
        math.floor(self.textAreaHeight / self.line_gap)
    )


def set_line_numbers(self, b):
    """
    Activates/deactivates showing the line numbers in the editor
    """
    self.displayLineNumbers = b
    if self.displayLineNumbers:
        self.lineNumberWidth = (
            27  # line number background width and also offset for text!
        )
        self.xline_start = self.editor_offset_X + self.xline_start_offset
        self.xline = self.editor_offset_X + self.xline_start_offset
    else:
        self.lineNumberWidth = 0
        self.xline_start = self.editor_offset_X
        self.xline = self.editor_offset_X


def set_cursor_mode(self, mode: str = "blinking"):
    if mode == "blinking":
        self.static_cursor = False
    elif mode == "static":
        self.static_cursor = True
    else:
        e_msg = f"Value '{mode}' is not a valid cursor mode. Set either to 'blinking' or 'static'."
        raise ValueError(e_msg)
