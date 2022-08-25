import re

import katagames_sdk as katasdk
from heavy_mod.shared import EditorEvTypes


kengi = katasdk.kengi
pygame = kengi.pygame
Receiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes


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


class CapelloEditorView(Receiver):
    DEFAULT_DEEP_GRAY_BGCOLOR = (43, 43, 43)  # same gray used by PyCharm

    def __init__(self, ref_mod):
        super().__init__()

        # used solely for the scrolling via mouse feature
        self.scroll_start_y = 0
        self.scroll_dragging = False
        # avoid scroll too fast
        self.cycleCounter = 0

        self.color_scrollbar = pygame.color.Color('grey34')

        # TODO find another way to express the following behavior
        # /!\ its very likely that this wont work in web ctx... start pb {
        key_initial_delay = 350
        key_continued_intervall = 50
        pygame.key.set_repeat(key_initial_delay, key_continued_intervall)
        # } end pb

        self._syntax_coloring = False
        self._bg_color = None

        self.cfonts = [
            kengi.gfx.ProtoFont('assets/capello-ft'),
            kengi.gfx.ProtoFont('assets/capello-ft-a'),
            kengi.gfx.ProtoFont('assets/capello-ft-b'),
            kengi.gfx.ProtoFont('assets/capello-ft-c'),
            kengi.gfx.ProtoFont('assets/capello-ft-d'),
            kengi.gfx.ProtoFont('assets/capello-ft-e'),
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
        self.caret_img = pygame.image.load('myassets/Trennzeichen.png')
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
        self._syntax_coloring = bool(boolv)

    # --------------
    #  métier, methodes privées
    # --------------

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
                        curr_li.append({'chars':  rawline[:x], 'color': 0, 'style': 'normal'})
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
        else:  # simple case
            rendering_list = list()
            for rawline in self._mod.line_string_list:
                # a single-item list when a single color is used
                rendering_list.append([{'chars': rawline, 'color': 0, 'style': 'normal'}])
            return rendering_list

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
        #rscreen.blit(self.caret_img, self.cursor_xy)
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

    def _left_click_handle(self, mousx, mousy):  # find adhoc pos for logical caret...
        if self._mod.scrollbar is not None:
            if self._mod.scrollbar.collidepoint(mousx, mousy):
                self.scroll_start_y = mousy
                self.scroll_dragging = True
                print('dragging starts')
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
            self._do_paint(ev.screen)

        elif ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = kengi.vscreen.proj_to_vscreen(ev.pos)
            if self._mod.mouse_within_texteditor(mx, my):
                if ev.button == 1:
                    self._left_click_handle(mx, my)
                elif ev.button == 4 and self._mod.showStartLine > 0:
                    self._mod.scrollbar_up()
                elif ev.button == 5 and self._mod.showStartLine + self._mod.showable_line_numbers_in_editor < self._mod.maxLines:
                    self._mod.scrollbar_down()

        elif ev.type == pygame.MOUSEBUTTONUP:
            if self.scroll_dragging:
                self.scroll_dragging = False
                self.cycleCounter = 0

        elif ev.type == pygame.MOUSEMOTION:
            if self.scroll_dragging:
                if not (self.cycleCounter % 8):
                    _, my = kengi.vscreen.proj_to_vscreen(ev.pos)
                    if my > self.scroll_start_y:
                        if self._mod.showStartLine+self._mod.showable_line_numbers_in_editor < len(self._mod.line_string_list):
                            self._mod.scrollbar_down()
                    elif my < self.scroll_start_y:
                        if self._mod.showStartLine > 0:
                            self._mod.scrollbar_up()
                    self.scroll_start_y = my
                self.cycleCounter += 1

        elif ev.type == EditorEvTypes.RedrawNeeded:
            self.rerenderLineNumbers = True

        elif ev.type == EditorEvTypes.CaretMoves:
            xinit = self._mod.xline_start
            i, j = ev.new_pos
            a, _ = self._mod.get_visible_line_indices()

            print('recv new_pos caret: ', ev.new_pos)
            txt_antecedent = self._mod.line_string_list[j][:i]
            # print(f'ante:[{txt_antecedent}]')
            #  i * self._mod.letter_size_X
            self.cursor_xy[0] = xinit - 2 + self.cfonts[0].compute_width(txt_antecedent, spacing=self.chosen_sp)
            self.cursor_xy[1] = (j-a) * self._mod.line_gap

    def _do_paint(self, scr_ref):
        # ---------
        # RENDERING 1 - Background objects
        # self.render_background_coloring(ref_scr)
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
            binf, bsup = self._mod.showStartLine, self._mod.showStartLine+self._mod.showable_line_numbers_in_editor
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
                    nstr = str(x + 1).zfill(3)

                    # -old
                    #text = self.pygfont.render(
                    #    nstr, self._mod.aa_option, self.lineNumberColor
                    #)
                    #text_rect = text.get_rect()
                    #text_rect.center = pygame.Rect(r).center

                    self.cfonts[3].text_to_surf(nstr, scr_ref, (-4+r[0]+r[2]-self.cfonts[0].compute_width(nstr, spacing=0), r[1]+self._mod.line_spacing), spacing=0)
                    # -old
                    # scr_ref.blit(text, text_rect)  # render on center of bg block
                line_numbers_y += self._mod.line_gap

        # ++ lines of text ++

        list_of_dicts = self._get_dicts()  # find what to draw + syntax coloring if needed
        # format returned by GET_COLOR_DICTS: List[List[Dict]]
        # if there's only one color for the whole line, the model of the line will look like this:
        # [{'chars': the_whole_line_str_obj, 'type': 'normal', 'color': self.textColor}]
        # if many colors, therefore many elements in the inner list...
        self._render_line_contents(list_of_dicts, scr_ref)
        self._render_caret(scr_ref)

        self.render_scrollbar_vertical(scr_ref)
