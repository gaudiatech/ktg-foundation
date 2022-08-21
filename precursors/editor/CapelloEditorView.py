import katagames_sdk as katasdk


# CHOSEN SYNTAX COLORING (white + 5 other colors)
# a- keywords like def, if, else, None, import, class... darkorange (201, 117, 49)
# b- built-in types and functions like print, list, str, etc. ALSO literals like 878 or 11.3 blue-ish gray (136,136,198)
# c- strings surrounded by '' or ""... green sapin (73, 138, 88) BUT ALSO triple quote/multi-line comments
# d- comments: well, it's just a light gray (95, 95, 105)
# e- very special keywords like __init__, self: a gentle purple (119, 50, 125)
# PY_SYNTAX will be used to implement a crude syntax coloring
# (-> simply use another color when one of the words listed in PY_SYNTAX is encountered)

# - constants
DEEP_GRAY_BGCOLOR = (43, 43, 43)  # same gray used by PyCharm

PY_SYNTAX = {
    ('KEYWORDS', 1): (  # py keywords
        'if', 'else', 'elif', 'for', 'while',
        'not', 'in', 'None', 'True', 'False',
        'def', 'return', 'class', 'as',
    ),
    ('BUILT-IN', 2): (  # py built-in stuff
        'bool', 'list', 'tuple', 'str', 'int', 'float', 'len', 'enumerate', 'range', 'max', 'min', 'super',
    ),
    ('VSPECIAL', 3): (  # vspecial words
        '__init__', 'self'
    )
}


# - aliases
kengi = katasdk.kengi
Receiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes


class CapelloEditorView(Receiver):
    def __init__(self, ref_mod):
        super().__init__()
        self._mod = ref_mod

        self.syntax_coloring = True
        self.cfonts = [
            kengi.gfx.ProtoFont('spec-assets/capello-ft'),
            kengi.gfx.ProtoFont('spec-assets/capello-ft-a'),
            kengi.gfx.ProtoFont('spec-assets/capello-ft-b'),
            kengi.gfx.ProtoFont('spec-assets/capello-ft-c'),
            kengi.gfx.ProtoFont('spec-assets/capello-ft-d'),
            kengi.gfx.ProtoFont('spec-assets/capello-ft-e'),
        ]

    # --------------
    #  métier, methodes privées
    # --------------
    def _get_color_dicts(self):  # -> List[List[Dict]]
        """
        THIS METHOD = display without color syntaxing!

        Converts the text in the editor based on the line_string_list into a list of lists of dicts.
        Every line is one sublist.
        Since only one color is being applied, we create a list with one dict per line.
        """
        rendering_list = list()
        if not self.syntax_coloring:
            for rawline in self._mod.line_string_list:
                # a single-item list when a single color is used
                rendering_list.append([{'chars': rawline, 'color': 0, 'style': 'normal'}])
            return rendering_list

        # new algo (august 22), detect py keywords and use colours
        for rawline in self._mod.line_string_list:
            curr_li = list()
            reco_smth = None
            while (reco_smth is None) or reco_smth:
                reco_smth = False
                for syntaxcat, known_words in PY_SYNTAX.items():
                    for w in known_words:
                        find_rez = rawline.find(w+' ')
                        if find_rez >= 0:  # update rawline (remove recognized w) & append w to curr_li
                            reco_smth = True
                            if find_rez == 0:
                                rawline = rawline[find_rez+len(w):]
                                curr_li.append({'chars': w, 'color': syntaxcat[1], 'style': 'normal'})
                            else:
                                curr_li.append({'chars': w, 'color': syntaxcat[1], 'style': 'normal'})
            # append the rest
            curr_li.append({'chars': rawline, 'color': 0, 'style': 'normal'})
            rendering_list.append(curr_li)
        return rendering_list

    def _render_line_contents(self, li_dicts, rscreen):
        # - naive algo
        # for k, line_todraw in enumerate(li_dicts):
        #     cidx = line_todraw[0]['color']
        #     pfont = self.cfonts[cidx]
        #     pfont.text_to_surf(line_todraw[0]['chars'], rscreen, (8, 8 + 10 * k), spacing=1)

        moo = self._mod

        # Preparation of the rendering:
        self.yline = self._mod.yline_start
        first_line = self._mod.showStartLine
        if moo.showable_line_numbers_in_editor < len(moo.line_string_list):
            # we got more text than we are able to display
            last_line = moo.showStartLine + moo.showable_line_numbers_in_editor
        else:
            last_line = moo.maxLines

        # Actual line rendering based on dict-keys
        for line_list in li_dicts[first_line: last_line]:
            xcoord = moo.xline_start
            for a_dict in line_list:
                cidx = a_dict['color']
                pfont = self.cfonts[cidx]

                #surface = self._blob.currentfont.render(a_dict['chars'], self._blob.txt_antialiasing, a_dict['color'])  # create surface
                #rscreen.blit(surface, (xcoord, self.yline))  # blit surface onto screen
                pfont.text_to_surf(a_dict['chars'], rscreen, (xcoord, self.yline), spacing=1)
                xcoord = xcoord + (len(a_dict['chars']) * moo.letter_size_X)  # next line-part prep
            self.yline += moo.line_gap  # next line prep

    def _render_caret(self, rscreen):
        pass  # TODO

    # ---------------------
    #  main method for this cls
    # ---------------------
    def proc_event(self, ev, source=None):
        if ev.type != EngineEvTypes.PAINT:
            return

        scr_ref = ev.screen
        scr_ref.fill(DEEP_GRAY_BGCOLOR)
        list_of_dicts = self._get_color_dicts()  # find what to draw + syntax coloring if needed
        # format returned by GET_COLOR_DICTS: List[List[Dict]]
        # if there's only one color for the whole line, the model of the line will look like this:
        # [{'chars': the_whole_line_str_obj, 'type': 'normal', 'color': self.textColor}]
        # if many colors, therefore many elements in the inner list...

        self._render_line_contents(list_of_dicts, scr_ref)
        self._render_caret(scr_ref)
