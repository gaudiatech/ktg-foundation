import katagames_sdk as katasdk

kengi = katasdk.kengi
pygame = kengi.pygame
Receiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes


# ----------------------------------------
#  CTRL
class EditorCtrl(Receiver):
    def __init__(self, ref_mod, shared):
        super().__init__()
        self._mod = ref_mod
        self.sharedstuff = shared
        self.dragged_active = False
        self.dragged_finished = True

    def proc_event(self, ev, source=None):
        """
        in particular, we need to handle:
        - escape = exit
        - ctrl+s = save content
        - ctrl+r the "refresh" operation: allows the user to pseudo-split his/her program
        - ctrl+n the "next file" operation: allows the user to cycle through all pseudo-files
        """
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.sharedstuff.kartridge_output = [2, 'niobepolis']
                # self.pev(EngineEvTypes.GAMEENDS)
                # print('[EditorCtrl] thrownig gameends event')

            else:
                pressed_keys = pygame.key.get_pressed()
                self._handle_keyb_input(ev, pressed_keys, False)  # 0 if self.latest_t is None else self.latest_t)

    def _handle_keyb_input(self, event, allkeys, unknown):
        # ___ COMBINATION KEY INPUTS ___
        # Functionality whether something is highlighted or not (highlight all / paste)
        ctrl_key_pressed = allkeys[pygame.K_LCTRL] or allkeys[pygame.K_RCTRL]
        if ctrl_key_pressed and event.key == pygame.K_a:
            self._blob.highlight_all()

        elif ctrl_key_pressed and event.key == pygame.K_n:
            self._mod.switch_file()  # edit next vfile

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

            elif event.unicode == '\x7f':  # K_DELETE
                self._mod.handle_keyboard_delete()
                self._mod.reset_text_area_to_caret()  # reset caret if necessary

            # ___ NORMAL KEYS ___
            # This covers all letters and numbers (not those on numpad).
            elif len(pygame.key.name(event.key)) == 1:
                self._mod.insert_unicode(event.unicode)
            elif event.unicode == '_':
                self._mod.insert_unicode('_')

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
                for _ in range(4):  # four spaces
                    self._mod.handle_keyboard_space()

            elif event.key == pygame.K_SPACE:  # SPACEBAR
                self._mod.handle_keyboard_space()

            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:  # RETURN
                self._mod.handle_keyboard_return()

            # ------------------------------
            #  arrow keys
            # ------------------------------
            elif event.key in (pygame.K_RIGHT, pygame.K_UP, pygame.K_LEFT, pygame.K_DOWN):
                # self._mod.handle_arrow_key({
                #     pygame.K_RIGHT: 0,
                #     pygame.K_UP: 1,
                #     pygame.K_LEFT: 2,
                #     pygame.K_DOWN: 3
                # }[event.key])
                if event.key == pygame.K_RIGHT:
                    self._mod.handle_keyboard_arrow_right()
                elif event.key == pygame.K_UP:
                    self._mod.handle_keyboard_arrow_up()
                elif event.key == pygame.K_LEFT:
                    self._mod.handle_keyboard_arrow_left()
                elif event.key == pygame.K_DOWN:
                    self._mod.handle_keyboard_arrow_down()
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
