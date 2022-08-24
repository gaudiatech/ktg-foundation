import katagames_sdk as katasdk
import math


kengi = katasdk.kengi
pygame = kengi.pygame


class EditorModel(kengi.event.CogObj):
    # Scroll functionality
    from ._scrollbar_vertical import (
        scrollbar_up,
        scrollbar_down,
    )

    # input handling KEYBOARD
    from ._input_handling_keyboard import (
        handle_keyboard_input,
        handle_keyboard_delete,
        handle_keyboard_backspace,
        handle_keyboard_return,
        handle_keyboard_space,
        handle_keyboard_tab,
        insert_unicode,
        handle_keyboard_arrow_left,
        handle_keyboard_arrow_right,
        handle_keyboard_arrow_up,
        handle_keyboard_arrow_down,
    )

    from ._input_handling_keyboard_highlight import (
        handle_input_with_highlight,
        handle_highlight_and_copy,
        handle_highlight_and_paste,
        handle_highlight_and_cut,
        highlight_all,
        get_highlighted_characters,
    )

    # input handling MOUSE
    from ._input_handling_mouse import (
        handle_mouse_input,
        mouse_within_texteditor,
        mouse_within_existing_lines,
    )

    # caret
    from ._caret import (
        update_caret_position,
        update_caret_position_by_drag_end,
        update_caret_position_by_drag_start,
        set_drag_start_after_last_line,
        set_drag_end_after_last_line,
        set_drag_start_by_mouse,
        set_drag_end_by_mouse,
        set_drag_end_line_by_mouse,
        set_drag_end_letter_by_mouse,
        set_drag_start_before_first_line,
    )

    # letter operations (delete, get)
    from ._letter_operations import (
        delete_entire_line,
        delete_start_to_letter,
        delete_letter_to_end,
        delete_letter_to_letter,
        get_entire_line,
        get_line_from_start_to_char,
        get_line_from_char_to_end,
        get_line_from_char_to_char,
    )

    from ._editor_getters import (
        get_line_index,
        get_letter_index,
        line_is_visible,
        get_showable_lines,
        get_number_of_letters_in_line_by_mouse,
        get_number_of_letters_in_line_by_index,
    )

    from ._other import jump_to_start, jump_to_end, reset_after_highlight

    # files for customization of the editor:
    from ._customization import (
        set_line_numbers,
        set_font_size,
        set_cursor_mode,
    )
    from ._usage import (
        get_text_as_list,
        get_text_as_string,
        clear_text,
        set_text_from_list,
        set_text_from_string,
    )

    def __init__(
        self,
        offset_x,
        offset_y,
        text_area_width,
        text_area_height,
        screen,
        line_numbers_flag=False,
        style="dark",
        syntax_highlighting_flag=False,
    ):
        super().__init__()
        self.ref_view = None
        self.screen = screen

        # VISUALS
        self.editor_offset_X = offset_x
        self.editor_offset_Y = offset_y
        self.textAreaWidth = text_area_width
        self.textAreaHeight = text_area_height

        self.conclusionBarHeight = 18
        self.letter_size_Y = 11

        # old
        # self.courier_font = pygame.font.SysFont('courier', self.letter_size_Y)

        self.proto_font = None  # init from outside (right after the view obj is created)
        self.known_spacing = None  # init from outside too

        self.aa_option = False

        # tom: i comment this bc we wanna use a font that's not monospace,
        # so the width of a msg needs to be computed dynamically based on what characters are on the line...

        # letter_width = self.courier_font.render(" ", self.aa_option, (0, 0, 0)).get_width()
        # self.letter_size_X = letter_width

        self.syntax_coloring = syntax_highlighting_flag

        # LINES
        self.Trenn_counter = 0
        self.MaxLinecounter = 0
        self.line_string_list = []  # LOGIC: Array of actual Strings
        self.lineHeight = self.letter_size_Y

        # self.maxLines is the variable keeping count how many lines we currently have -
        # in the beginning we fill the entire editor with empty lines.
        self.maxLines = int(math.floor(self.textAreaHeight / self.lineHeight))
        self.showStartLine = 0  # first line (shown at the top of the editor) <- must be zero during init!
        self.line_spacing = 3
        self.line_gap = self.letter_size_Y + self.line_spacing
        self.showable_line_numbers_in_editor = int(
            math.floor(self.textAreaHeight / self.line_gap)
        )

        for i in range(self.maxLines):  # from 0 to maxLines:
            self.line_string_list.append("")  # Add a line

        # SCROLLBAR
        self.scrollbar: pygame.Rect = None
        self.scrollBarWidth = 8  # must be an even number
        self.scroll_start_y: int = None
        self.scroll_dragging: bool = False

        # LINE NUMBERS
        self.displayLineNumbers = line_numbers_flag
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

        # ----------------
        #  faudra remetrre ca dans view
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
