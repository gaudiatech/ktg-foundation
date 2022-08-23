import re

import katagames_sdk as katasdk
from shared import EditorEvents

kengi = katasdk.kengi
pygame = kengi.pygame
Receiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes


# ------------------------------------------
#  VIEW
# - constants
DEEP_GRAY_BGCOLOR = (43, 43, 43)  # same gray used by PyCharm

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
    def __init__(self, ref_mod):
        super().__init__()
        self._mod = ref_mod
        self.chosen_sp = 1  # spacing between letters

        # TODO find another way to express the following behavior
        # /!\ its very likely that this wont work in web ctx... start pb {
        key_initial_delay = 350
        key_continued_intervall = 50
        pygame.key.set_repeat(key_initial_delay, key_continued_intervall)
        # } end pb

        self.syntax_coloring = True
        self.cfonts = [
            kengi.gfx.ProtoFont('assets/capello-ft'),
            kengi.gfx.ProtoFont('assets/capello-ft-a'),
            kengi.gfx.ProtoFont('assets/capello-ft-b'),
            kengi.gfx.ProtoFont('assets/capello-ft-c'),
            kengi.gfx.ProtoFont('assets/capello-ft-d'),
            kengi.gfx.ProtoFont('assets/capello-ft-e'),
        ]

        # so we can disp a caret
        self.caret_img = pygame.image.load('myassets/Trennzeichen.png')
        cwidth = self.caret_img.get_size()[0]
        adhoc_h = self.cfonts[0].car_height['x']  # all chars have the same height so we can use x, whatever
        # TODO retablir ceci (peut etre?) quand le .scale sera implémenté en web ctx
        # self.caret_img = pygame.transform.scale(self.caret_img, (2*cwidth, 1+adhoc_h))

        # update this when proc event CaretMoves
        self.caret_xy = [self._mod.xline_start-1, 0]  # y 0 because we start on line 0

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
        if self.syntax_coloring:
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
        first_line = self._mod.showStartLine
        if moo.max_nb_lines_shown < len(moo.line_string_list):
            # we got more text than we are able to display
            last_line = moo.showStartLine + moo.max_nb_lines_shown
        else:
            last_line = moo.maxLines

        # Actual line rendering based on dict-keys
        for line_list in li_dicts[first_line: last_line]:
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
        rscreen.blit(self.caret_img, self.caret_xy)

    # ---------------------
    #  most important method for this cls
    def proc_event(self, ev, source=None):
        if ev.type == EngineEvTypes.PAINT:
            scr_ref = ev.screen
            scr_ref.fill(DEEP_GRAY_BGCOLOR)
            list_of_dicts = self._get_dicts()  # find what to draw + syntax coloring if needed
            # format returned by GET_COLOR_DICTS: List[List[Dict]]
            # if there's only one color for the whole line, the model of the line will look like this:
            # [{'chars': the_whole_line_str_obj, 'type': 'normal', 'color': self.textColor}]
            # if many colors, therefore many elements in the inner list...
            self._render_line_contents(list_of_dicts, scr_ref)
            self._render_caret(scr_ref)

        elif ev.type == EditorEvents.CaretMoves:
            xinit = self._mod.xline_start
            i, j = ev.new_pos
            print('recv new_pos caret: ', ev.new_pos)
            txt_antecedent = self._mod.line_string_list[j][:i]
            # print(f'ante:[{txt_antecedent}]')
            #  i * self._mod.letter_size_X
            self.caret_xy[0] = xinit-2 + self.cfonts[0].compute_width(txt_antecedent, spacing=self.chosen_sp)
            self.caret_xy[1] = j * self._mod.line_gap
