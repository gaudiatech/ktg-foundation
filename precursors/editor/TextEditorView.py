import katagames_sdk as katasdk
# import sharedstuff

sharedstuff = None
kengi = katasdk.kengi
pygame = kengi.pygame
EngineEvTypes = kengi.event.EngineEvTypes


SAVE_ICO_LIFEDUR = 2


# ----------------------------------------------
#   start of editor view
#   N.B. we have split the legacy class
#   to have a view that inherits from kengi.event.EventReceiver
# ----------------------------------------------
class TextEditorView(kengi.event.EventReceiver):
    def __init__(self, editorblob_obj, maxfps, shared=None):
        global sharedstuff
        if shared:
            sharedstuff = shared
        super().__init__()
        self._blob = editorblob_obj  # blob bc its not 100% refactored, yet
        self._maxfps = maxfps
        self.latest_t = None
        self._prev_mouse_x, self._prev_mouse_y = 0, 0

        self.firstiteration_boolean = True
        self.click_hold = False
        self.cycleCounter = 0  # Used to be able to tell whether a mouse-drag action has been handled already or not.

        self.icosurf = pygame.image.load('myassets/saveicon.png')
        saveicon_size = self.icosurf.get_size()
        scr_size = sharedstuff.screen.get_size()
        self.icosurf_pos = ((scr_size[0]-saveicon_size[0])//2, (scr_size[1]-saveicon_size[1])//2)

        self.carret_img = pygame.image.load('myassets/Trennzeichen.png').convert_alpha()

        # click down - coordinates used to identify start-point of drag
        self.dragged_active = False
        self.dragged_finished = True
        self.last_clickdown_cycle = 0
        self.last_clickup_cycle = 0

        self.Trenn_counter = 0

        # Colors
        self.codingBackgroundColor = (40, 41, 41)
        self.codingScrollBarBackgroundColor = (49, 50, 50)
        self.lineNumberColor = (255, 255, 255)
        self.lineNumberBackgroundColor = (60, 61, 61)
        self.textColor = (255, 255, 255)
        self.color_scrollbar = (60, 61, 61)

    #def __getattr__(self, item):  # hack for easing the refactoring
    #    return getattr(self._blob, item)

    def _manage_mouse_drag(self):
        return
        mouse_x, mouse_y = kengi.core.proj_to_vscreen(pygame.mouse.get_pos())
        mouse_pressed = pygame.mouse.get_pressed()

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

            # TODO the dragging operation is kinda broken, fix this!
            # tom has commented out this line on may 11th
            # self.update_caret_position()
            # i can see that i can select text, but
            #  - i have to Ctrl-A first
            #  - the update of highlighted txt comes late!

            # reset after upclick so we don't execute this block again and again.
            self.last_clickdown_cycle = 0
            self.last_clickup_cycle = -1

        # Scrollbar - Dragging
        if mouse_pressed[0] == 1 and self.scroll_dragging:
            # left mouse is being pressed after click on scrollbar
            if mouse_y < self.scroll_start_y and self.showStartLine > 0:
                # dragged higher
                self.scrollbar_up()
            elif mouse_y > self.scroll_start_y and self.showStartLine + self.showable_line_numbers_in_editor < self.maxLines:
                # dragged lower
                self.scrollbar_down()

    def proc_event(self, ev, source):
        # def use_events(self, pygame_events, pressed_keys, shared, tinfo=None):
        # needs to be called within a while loop to be able to catch key/mouse input 'n update visuals throughout use
        if ev.type == EngineEvTypes.LOGICUPDATE:
            self.cycleCounter = self.cycleCounter + 1
            self.latest_t = ev.curr_t
            self._manage_mouse_drag()

        elif ev.type == pygame.QUIT:
            sharedstuff.kartridge_output = [2, 'niobepolis']
            return

        elif ev.type == EngineEvTypes.PAINT:
            # first rendering
            if self.firstiteration_boolean:
                self.firstiteration_boolean = False
                tmp = (self._blob.editor_offset_X, self._blob.editor_offset_Y, self._blob.textAreaWidth, self._blob.textAreaHeight)
                # paint entire area to avoid pixel error beneath line numbers
                pygame.draw.rect(ev.screen, self.codingBackgroundColor, tmp)

            self.do_paint(ev.screen)

        elif ev.type == pygame.KEYDOWN:
            pressed_keys = pygame.key.get_pressed()
            self.handle_keyboard_input(ev, pressed_keys, 0 if self.latest_t is None else self.latest_t)

        elif ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            mouse_pressed = pygame.mouse.get_pressed()
            mouse_x, mouse_y = kengi.vscreen.proj_to_vscreen(pygame.mouse.get_pos())
            # debugging
            if ev.type == pygame.MOUSEBUTTONDOWN:
                print('click')
            self._prev_mouse_x, self._prev_mouse_y = mouse_x, mouse_y
            self.handle_mouse_input(ev, mouse_x, mouse_y, mouse_pressed)

    def do_paint(self, scr_ref):
        # RENDERING 1 - Background objects
        self.render_background_coloring(scr_ref)
        self.render_line_numbers(scr_ref)

        # RENDERING 2 - Lines
        self.render_highlight(self._prev_mouse_x, self._prev_mouse_y)

        # single-color text
        list_of_dicts = self.get_single_color_dicts()
        self.render_line_contents_by_dicts(list_of_dicts, scr_ref)

        self.render_caret(scr_ref)

        self.display_scrollbar(scr_ref)
        if sharedstuff.file_label:
            scr_ref.blit(sharedstuff.file_label, (0, 0))

        if self.latest_t is not None:
            if sharedstuff.disp_save_ico:
                scr_ref.blit(self.icosurf, self.icosurf_pos)
                if self.latest_t > sharedstuff.disp_save_ico:
                    sharedstuff.disp_save_ico = None
        kengi.flip()

    def get_single_color_dicts(self):  # -> List[List[Dict]]
        """
        Converts the text in the editor based on the line_string_list into a list of lists of dicts.
        Every line is one sublist.
        Since only one color is being applied, we create a list with one dict per line.
        """
        rendering_list = []
        for line in self._blob.line_string_list:
            # appends a single-item list
            rendering_list.append([{'chars': line, 'type': 'normal', 'color': self.textColor}])
        return rendering_list

    def render_highlight(self, mouse_x, mouse_y):
        """
        Renders highlighted area:
        1. During drag-action -> area starts at drag_start and follows mouse
        2. After drag-action -> area stays confined to selected area by drag_start and drag_end
        """

        if self.dragged_active:  # some text is highlighted or being highlighted
            line_start = self._blob.drag_chosen_LineIndex_start
            letter_start = self._blob.drag_chosen_LetterIndex_start

            if self.dragged_finished:  # highlighting operation is done, user "clicked-up" with the left mouse button
                line_end = self.drag_chosen_LineIndex_end
                letter_end = self.drag_chosen_LetterIndex_end
                if letter_end < 0:
                    letter_end = 0
                self.highlight_lines(line_start, letter_start, line_end, letter_end)  # Actual highlighting

            else:  # active highlighting -> highlighted area follows mouse movements
                line_end = self._blob.get_line_index(mouse_y)
                letter_end = self._blob.get_letter_index(mouse_x)
                # adapt line_end: if mouse_y below showable area / existing lines,
                if line_end >= self._blob.get_showable_lines():
                    line_end = self._blob.get_showable_lines() - 1  # select last showable/existing line as line_end

                # Correct letter_end based on cursor position / letters in the cursor's line
                if letter_end < 0:  # cursor is left of the line
                    letter_end = 0
                elif letter_end > len(self._blob.line_string_list[line_end]):
                    letter_end = len(self._blob.line_string_list[line_end])

                self._blob.highlight_lines(line_start, letter_start, line_end, letter_end)  # Actual highlighting

    def render_background_coloring(self, scr) -> None:
        """
        Renders background color of the text area.
        """
        bg_left = self._blob.editor_offset_X + self._blob.lineNumberWidth
        bg_top = self._blob.editor_offset_Y
        bg_width = self._blob.textAreaWidth - self._blob.lineNumberWidth
        bg_height = self._blob.textAreaHeight
        pygame.draw.rect(scr, self.codingBackgroundColor, (bg_left, bg_top, bg_width, bg_height))

    def render_line_numbers(self, scr):
        """
        While background rendering is done for all "line-slots"
        (to overpaint remaining "old" numbers without lines)
        we render line-numbers only for existing string-lines.
        """
        if self._blob.displayLineNumbers and self._blob.rerenderLineNumbers:
            self._blob.rerenderLineNumbers = False
            line_numbers_y = self._blob.editor_offset_Y  # init for first line
            for x in range(self._blob.showStartLine, self._blob.showStartLine + self._blob.showable_line_numbers_in_editor):

                # background
                r = (self._blob.editor_offset_X, line_numbers_y, self._blob.lineNumberWidth, self._blob.line_gap)
                pygame.draw.rect(scr, self.lineNumberBackgroundColor, r)  # to debug use: ,1) after r

                # line number
                if x < self._blob.get_showable_lines():
                    # x + 1 in order to start with line 1 (only display, logical it's the 0th item in the list
                    text = self._blob.currentfont.render(str(x + 1).zfill(2), self._blob.txt_antialiasing, self.lineNumberColor)
                    text_rect = text.get_rect()
                    text_rect.center = pygame.Rect(r).center
                    scr.blit(text, text_rect)  # render on center of bg block
                line_numbers_y += self._blob.line_gap

    def render_line_contents_by_dicts(self, dicts, scr):
        # Preparation of the rendering:
        self.yline = self._blob.yline_start
        first_line = self._blob.showStartLine
        if self._blob.showable_line_numbers_in_editor < len(self._blob.line_string_list):
            # we got more text than we are able to display
            last_line = self.showStartLine + self.showable_line_numbers_in_editor
        else:
            last_line = self._blob.maxLines

        # Actual line rendering based on dict-keys
        for line_list in dicts[first_line: last_line]:
            xcoord = self._blob.xline_start
            for a_dict in line_list:
                surface = self._blob.currentfont.render(a_dict['chars'], self._blob.txt_antialiasing,
                                                  a_dict['color'])  # create surface
                scr.blit(surface, (xcoord, self.yline))  # blit surface onto screen
                xcoord = xcoord + (len(a_dict['chars']) * self._blob.letter_size_X)  # next line-part prep

            self.yline += self._blob.line_gap  # next line prep

    def render_caret(self, scr):
        """
        Called every frame. Displays a cursor for x frames, then none for x frames. Only displayed if line in which
        caret resides is visible and there is no active dragging operation going on.
        Dependent on FPS -> 5 intervalls per second
        Creates 'blinking' animation
        """
        self.Trenn_counter += 1
        if self.Trenn_counter > (self._maxfps / 5) and self._blob.caret_within_texteditor() and self.dragged_finished:
            scr.blit(self.carret_img, (self._blob.cursor_X, self._blob.cursor_Y))
            self.Trenn_counter = self.Trenn_counter % ((self._maxfps / 5) * 2)

    def handle_keyboard_input(self, event, pressed_keys, tinfo):
        if event.key == pygame.K_ESCAPE:
            sharedstuff.kartridge_output = [2, 'niobepolis']
            return True

        # ___ COMBINATION KEY INPUTS ___
        # Functionality whether something is highlighted or not (highlight all / paste)
        ctrl_key_pressed = pressed_keys[pygame.K_LCTRL] or pressed_keys[pygame.K_RCTRL]
        if ctrl_key_pressed and event.key == pygame.K_a:
            self._blob.highlight_all()

        elif ctrl_key_pressed and event.key == pygame.K_z:
            # TODO implement undo operation
            print('undo not implemented yet!')
            pass

        elif ctrl_key_pressed and event.key == pygame.K_v:
            self.handle_highlight_and_paste()

        elif ctrl_key_pressed and event.key == pygame.K_s:
            print('**SAVE detected**')
            sharedstuff.disp_save_ico = tinfo + SAVE_ICO_LIFEDUR
            sharedstuff.dump_content = self._blob.get_text_as_string()

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

            self._blob.reset_text_area_to_caret()  # reset visual area to include line of caret if necessary
            self._blob.chosen_LetterIndex = int(self._blob.chosen_LetterIndex)

            # print("event", event)

            # Detect tapping/holding of the "DELETE" and "BACKSPACE" key while something is highlighted
            # ** for removing SELECTION **
            # if self.dragged_finished and self.dragged_active and \
            #         (event.unicode == '\x08' or event.unicode == '\x7f'):
            #     # create the uniform event for both keys so we don't have to write two functions
            #     deletion_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DELETE)
            #     self.handle_input_with_highlight(deletion_event)  # delete and backspace have the same functionality

            # ___ DELETIONS ___
            if event.unicode == '\x08':  # K_BACKSPACE
                self._blob.handle_keyboard_backspace()
                self._blob.reset_text_area_to_caret()  # reset caret if necessary

            elif event.unicode == '\x7f':  # K_DELETE
                self._blob.handle_keyboard_delete()
                self._blob.reset_text_area_to_caret()  # reset caret if necessary

            # ___ NORMAL KEYS ___
            # This covers all letters and numbers (not those on numpad).
            elif len(pygame.key.name(event.key)) == 1:
                self._blob.insert_unicode(event.unicode)
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
                self._blob.handle_keyboard_tab()
            elif event.key == pygame.K_SPACE:  # SPACEBAR
                self._blob.handle_keyboard_space()
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:  # RETURN
                self._blob.handle_keyboard_return()
            elif event.key == pygame.K_UP:  # ARROW_UP
                self._blob.handle_keyboard_arrow_up()
            elif event.key == pygame.K_DOWN:  # ARROW_DOWN
                self._blob.handle_keyboard_arrow_down()
            elif event.key == pygame.K_RIGHT:  # ARROW_RIGHT
                self._blob.handle_keyboard_arrow_right()
            elif event.key == pygame.K_LEFT:  # ARROW_LEFT
                self._blob.handle_keyboard_arrow_left()
            else:
                if event.key not in [pygame.K_RSHIFT, pygame.K_LSHIFT, pygame.K_DELETE,
                                     pygame.K_BACKSPACE, pygame.K_CAPSLOCK, pygame.K_LCTRL, pygame.K_RCTRL]:
                    # We handled the keys separately
                    # Capslock is apparently implicitly handled
                    # when using it in combination
                    print('*WARNING* No implementation for key: ', end='')
                    print(pygame.key.name(event.key))
        return False

    def handle_mouse_input(self, event, mouse_x, mouse_y, mouse_pressed) -> None:
        """
        Handles mouse input based on mouse events (Buttons down/up + coordinates).
        Handles drag-and-drop-select as well as single-click.
        The code only differentiates the single-click only as so far, that
            the DOWN-event is on the same position as the UP-event.

        Implemented so far:
        - left-click (selecting as drag-and-drop or single-click)
        - mouse-wheel (scrolling)
        """

        # ___ MOUSE CLICKING DOWN ___ #

        # Mouse scrolling wheel should only work if it is within the coding area (excluding scrollbar area)
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self._blob.mouse_within_texteditor(mouse_x, mouse_y):
                # ___ MOUSE SCROLLING ___ #
                if event.button == 4 and self.showStartLine > 0:
                    self._blob.scrollbar_up()
                elif event.button == 5 and self.showStartLine + self.showable_line_numbers_in_editor < self.maxLines:
                    self._blob.scrollbar_down()

                # ___ MOUSE LEFT CLICK DOWN ___ #
                elif event.button == 1:  # left mouse button
                    if not self.click_hold:
                        print(' button 1')
                        # in order not to have the mouse move around after a click,
                        # we need to disable this function until we RELEASE it.
                        self.last_clickdown_cycle = self.cycleCounter
                        self.click_hold = True
                        self.dragged_active = True
                        self.dragged_finished = False
                        if self._blob.mouse_within_texteditor(mouse_x, mouse_y):  # editor area

                            if self._blob.mouse_within_existing_lines(mouse_y):  # in area of existing lines
                                self._blob.set_drag_start_by_mouse(mouse_x, mouse_y)
                            else:  # clicked below the existing lines
                                self._blob.set_drag_start_after_last_line()
                            print('inside txt')
                            self._blob.update_caret_position_by_drag_start()

                            # tom add-on:
                            # we need this otherwise the carret moves but the text input is at the wrong location!
                            # self._blob.set_drag_start_by_mouse(mouse_x, mouse_y)

                        else:  # mouse outside of editor, don't care.
                            pass
            # Scrollbar-handling
            else:
                if self.scrollbar is not None:
                    if self.scrollbar.collidepoint(mouse_x, mouse_y):
                        self.scroll_start_y = mouse_y
                        self.scroll_dragging = True

        # ___ MOUSE LEFT CLICK UP ___ #
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.scroll_dragging = False  # reset scroll (if necessary)

                if self.click_hold:
                    # mouse dragging only with left mouse up
                    # mouse-up only valid if we registered a mouse-down within the editor via click_hold earlier

                    self.last_clickup_cycle = self.cycleCounter
                    self.click_hold = False

                    if self._blob.mouse_within_texteditor(mouse_x, mouse_y):  # editor area
                        if self._blob.mouse_within_existing_lines(mouse_y):  # in area of existing lines
                            self._blob.set_drag_end_by_mouse(mouse_x, mouse_y)
                        else:  # clicked beneath the existing lines
                            self._blob.set_drag_end_after_last_line()
                        self._blob.update_caret_position_by_drag_end()

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

    def display_scrollbar(self, scr):
        if len(self._blob.line_string_list) > self._blob.showable_line_numbers_in_editor:
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
            pygame.draw.rect(scr, self.color_scrollbar, self.scrollbar)
            # bottom round corner
            pygame.draw.circle(scr, self.color_scrollbar, (int(x + (w / 2)), y + h), int(w / 2))
        else:  # if scrollbar is not needed, don't show
            self.scrollbar = None
