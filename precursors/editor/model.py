"""
in this file, I try to create a cleaner version of the model,
used by the KTG code editor.
We strip down legacy model, removing everything that isnt useful
"""
import math
import re


class Sharedstuff:
    def __init__(self):
        self.disp_save_ico = None  # contains info 'bout time when it needs display
        self.dump_content = None
        self.kartridge_output = None
        self.screen = None
        self.file_label = None  # for showing what is being edited


class EditorModel:

    def __init__(self, py_code, offset_x, offset_y,  dimx, dimy, line_numbers_flag=False):
        """
        :param py_code:
        :param offset_x:
        :param offset_y:
        :param dimx:
        :param dimy:
        :param line_numbers_flag: should we display line numbers?
        """
        self.editor_offset_X = offset_x
        self.editor_offset_Y = offset_y

        self.textAreaWidth = dimx
        self.textAreaHeight = dimy

        self.line_string_list = None
        self.maxLines = 0
        self.rerenderLineNumbers = True
        self.displayLineNumbers = line_numbers_flag  # accessed from outside /!\
        self.showStartLine = 0  # accessed from outside
        self.status_info_msg = ''  # acessed from the view

        # 2 vars accessed from the view as well, to render the carret
        self.chosen_LetterIndex = 0
        self.chosen_LineIndex = 0

        # this line is here so the text is not overriding column dedicated to  line number display...
        self.xline_start_offset = 25

        # size of letters
        self.letter_size_Y = 12

        # not sure if the following block is super useful, ive added it only to support 4 arrows operations
        self.showable_line_numbers_in_editor = 15  # -->maybe can have a default val, then we set real val via the view
        self.lineHeight = 20  # -------->view
        self.letter_size_X = 8  # -------->view
        self.lineNumberWidth = 24  # --------->view
        self.txt_antialiasing = False  #-->view

        linespacing = 2
        self.line_gap = self.letter_size_Y + linespacing

        self.yline_start = offset_y  # cest pas dupe val?

        # CURSOR - coordinates for displaying the caret while typing
        self.cursor_Y = self.cursor_X = None
        self.xline = self.xline_start = None
        self.reset_cursor()

        self.curr_vfile_idx = -1
        self.fake_layout = py_code
        # could do this: VirtualFileset(py_code), if code wasnt already modeled as vfileset
        self.switch_file()  # load main.py

    # ---> used by legacy view
    def get_showable_lines(self):
        return self.showable_line_numbers_in_editor

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
                self.showStartLine + self.showable_line_numbers_in_editor - 1):  # below visible area
            self.showStartLine = self.chosen_LineIndex - self.showable_line_numbers_in_editor + 1
            self.rerenderLineNumbers = True
            self.update_caret_position()
        # next possible enhancement: set cursor coordinates

    def _clear_text(self):
        self.line_string_list = list()  # model: list of actual Strings for each line
        self.maxLines = int(math.floor(self.textAreaHeight / self.lineHeight))  # TODO dont mix with the view
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
        self.cursor_X += self.letter_size_X
        self.chosen_LetterIndex += 1

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

    def handle_keyboard_return(self):
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

    def insert_unicode(self, unicode):
        nl = self.line_string_list[self.chosen_LineIndex][:self.chosen_LetterIndex]
        nl += unicode
        nl += self.line_string_list[self.chosen_LineIndex][self.chosen_LetterIndex:]
        self.line_string_list[self.chosen_LineIndex] = nl
        self.chosen_LetterIndex += 1
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

    # -------------------- this is awful, fix it plz -----------------
    # four methods while you could use just one... sigh
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
