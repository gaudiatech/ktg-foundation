import sys
sys.path.append('..')

import os
import weakref
import katagames_sdk as katasdk


kengi = katasdk.bootstrap('old_school')
pygame = kengi.pygame
PATH_SRC_FILE = 'editor0/__main__.py'  # this is a super long line of comment just to try out txt wrapping... 'roms/niobepolis.py'


class Resources:
    _names = {}

    @classmethod
    def __init__(cls, loader, path, types, weak_ref=True):
        cls._index(path, types)
        if weakref:
            cls.cache = weakref.WeakValueDictionary()
        else:
            cls.cache = {}
        cls.loader = loader

    @classmethod
    def __getattr__(cls, name):
        try:
            img = cls.cache[name]
        except KeyError:
            img = cls.loader(cls._names[name])
            cls.cache[name] = img
        return img

    @classmethod
    def load(cls, name):
        return cls.__getattr__(name)

    @classmethod
    def _index(cls, path, types):
        # Python version >=3.5 supports glob
        import glob
        for img_type in types:
            for filename in glob.iglob(
                (path + '/**/' + img_type), recursive=True
            ):
                f_base = os.path.basename(filename)
                print({f_base: filename})
                cls._names.update({f_base: filename})


class Fonts(Resources):
    @classmethod
    def __init__(cls, path="."):
        print('path =' +path)
        super().__init__(
            loader=pygame.font.Font,
            path=path,
            types=['*.ttf'],
            weak_ref=False)

    @classmethod
    def __getattr__(cls, name, size):
        try:
            font = cls.cache[name, size]
        except KeyError:
            font = cls.loader(cls._names[name], size)
            cls.cache[name, size] = font
        return font

    @classmethod
    def load(cls, name, size):
        return cls.__getattr__(name, size)


FROM_ARCHIVE = '__BRYTHON__' in globals()
NEXT_GAME_LOADED = 'niobepolis'  # 'main1'
pygame = kengi.pygame
CogObject = kengi.event.CogObj
EventReceiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes
SCR_SIZE = [0, 0]
NB_ROCKS = 3
bullets = list()
FG_COLOR = (119, 255, 0)
music_snd = None
view = ctrl = None
Vector2 = pygame.math.Vector2
MyEvTypes = kengi.event.enum_ev_types(
    'PlayerChanges',  # contains: new_pos, angle
)
update_func_sig = None
lu_event = p_event = None
clockk = pygame.time.Clock()
CgmEvent = kengi.event.CgmEvent
e_manager = None
gameover = False

pygame = kengi.pygame


# ---------------------------------------------------------
# sftext - Scrollable Formatted Text for pygame
# Copyright (c) 2016 Lucas de Morais Siqueira
# Distributed under the GNU Lesser General Public License version 3.
#
#       \ vvvvvvvvvvvvv /
#     >>> STYLE MANAGER <<<
#       / ^^^^^^^^^^^^^ \
#
#     Support by using, forking, reporting issues and giving feedback:
#     https://https://github.com/LukeMS/sftext/
#
#     Lucas de Morais Siqueira (aka LukeMS)
#     lucas.morais.siqueira@gmail.com
#
#    This file is part of sftext.
#
#    sftext is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    any later version.
#
#    sftext is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with sftext. If not, see <http://www.gnu.org/licenses/>.
# ---------------------------------------------------------

import re

DEFAULT_STYLE = {
    # At the momment only font filenames are supported. That means the font
    # must be in the same directory as the main script.
    # Or you could (should?) use a resource manager such as
    'font': 'caladea-regular.ttf',
    'size': 12,
    'indent': 0,
    'bold': False,
    'italic': False,
    'underline': False,
    'color': (157, 163, 157),  # light gray, RGB values
    'align': 'left',
    # if a separate file should be used for italic/bold, speciy it;
    # if not, use None
    'separate_italic': 'caladea-italic.ttf',
    'separate_bold': 'caladea-bold.ttf',
    'separate_bolditalic': 'caladea-bolditalic.ttf',
}


class TextStyle:
    default_style = DEFAULT_STYLE

    @classmethod
    def set_default(cls, source):
        if isinstance(source, str):
            cls.string = str(source)
            cls._get_style()
            cls.default_style = dict(cls.style)
        elif isinstance(source, dict):
            for key, value in source.items():
                cls.default_style[key] = value
        return cls.default_style

    @classmethod
    def get_default(cls, string):
        return cls.default_style

    @classmethod
    def stylize(cls, string, style=None):
        if style is None:
            style = cls.default_style
        stylized = ""

        for key, value in style.items():
            if isinstance(value, str):
                stylized += ("{" + "{} '{}".format(key, value) + "'}")
            else:
                stylized += ("{" + "{} {}".format(key, value) + "}")
        stylized += string
        return stylized

    @classmethod
    def split(cls, string):
        cls.string = str(string)
        cls._get_style()
        return cls.string, cls.style

    @classmethod
    def remove(cls, string):
        cls.string = str(string)
        cls._get_style()
        return cls.string

    @classmethod
    def get(cls, string):
        cls.string = str(string)
        cls._get_style()
        return cls.style

    @classmethod
    def _get_style(cls):
        cls.style = {}
        cls.style['font'] = cls._get_font()
        cls.style['size'] = cls._get_size()
        cls.style['bold'] = cls._get_font_bold()
        cls.style['italic'] = cls._get_font_italic()
        cls.style['underline'] = cls._get_font_underline()
        cls.style['color'] = cls._get_font_color()
        cls.style['align'] = cls._get_font_align()
        cls.style['indent'] = cls._get_font_indent()
        cls.style['separate_bold'] = cls._get_separate_bold()
        cls.style['separate_italic'] = cls._get_separate_italic()
        cls.style['separate_bolditalic'] = cls._get_separate_bolditalic()

    @classmethod
    def _get_font(cls):
        pattern = (
            "{font(_name)? ('|\")(?P<font>[A-Za-z0-9_ -]+"
            "(?P<ext>.ttf))('|\")}")
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            if searchgroup.group('ext'):
                font = searchgroup.group('font')
            else:
                font = searchgroup.group('font') + ".ttf"
                print(font)
        else:
            font = cls.default_style['font']
        cls.string = re.sub(
            (
                "({font(_name)? ('|\")([A-Za-z0-9_ -]+"
                "(.ttf)?)('|\")})"),
            '',
            cls.string)
        return font

    @classmethod
    def _get_separate_italic(cls):
        pattern = (
            "{separate_italic ('|\")(?P<separate_italic>[A-Za-z0-9_ -]+"
            "(?P<ext>.ttf))('|\")}")
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            if searchgroup.group('ext'):
                separate_italic = searchgroup.group('separate_italic')
            else:
                separate_italic = searchgroup.group('separate_italic') + ".ttf"
                print(separate_italic)
        else:
            if cls.style['font'] == cls.default_style['font']:
                separate_italic = cls.default_style['separate_italic']
            else:
                separate_italic = None
        cls.string = re.sub(
            (
                "({separate_italic ('|\")([A-Za-z0-9_ -]+"
                "(.ttf)?)('|\")})"),
            '',
            cls.string)
        return separate_italic

    @classmethod
    def _get_separate_bold(cls):
        pattern = (
            "{separate_bold ('|\")(?P<separate_bold>[A-Za-z0-9_ -]+"
            "(?P<ext>.ttf))('|\")}")
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            if searchgroup.group('ext'):
                separate_bold = searchgroup.group('separate_bold')
            else:
                separate_bold = searchgroup.group('separate_bold') + ".ttf"
                print(separate_bold)
        else:
            if cls.style['font'] == cls.default_style['font']:
                separate_bold = cls.default_style['separate_bold']
            else:
                separate_bold = None
        cls.string = re.sub(
            (
                "({separate_bold ('|\")([A-Za-z0-9_ -]+"
                "(.ttf)?)('|\")})"),
            '',
            cls.string)
        return separate_bold

    @classmethod
    def _get_separate_bolditalic(cls):
        pattern = (
            "{separate_bolditalic ('|\")"
            "(?P<separate_bolditalic>[A-Za-z0-9_ -]+"
            "(?P<ext>.ttf))('|\")}")
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            if searchgroup.group('ext'):
                separate_bolditalic = searchgroup.group('separate_bolditalic')
            else:
                separate_bolditalic = searchgroup.group(
                    'separate_bolditalic') + ".ttf"
                print(separate_bolditalic)
        else:
            if cls.style['font'] == cls.default_style['font']:
                separate_bolditalic = cls.default_style['separate_bolditalic']
            else:
                separate_bolditalic = None
        cls.string = re.sub(
            (
                "({separate_bold ('|\")([A-Za-z0-9_ -]+"
                "(.ttf)?)('|\")})"),
            '',
            cls.string)
        return separate_bolditalic

    @classmethod
    def _get_size(cls):
        pattern = "{(font_)?size (?P<size>\d+)}"
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            size = searchgroup.group('size')
        else:
            size = cls.default_style['size']
        cls.string = re.sub(pattern, '', cls.string)
        return int(size)

    @classmethod
    def _get_font_bold(cls):
        pattern = "{bold ('|\"|)(?P<bold>True|False)('|\"|)}"
        searchgroup = re.search(pattern, cls.string, re.I)
        if searchgroup:
            bold = searchgroup.group('bold')
            cls.string = re.sub(pattern, '', cls.string)
            return bold.lower() == "true"
        else:
            bold = cls.default_style['bold']
            cls.string = re.sub(pattern, '', cls.string)
            return bold

    @classmethod
    def _get_font_italic(cls):
        pattern = "{italic ('|\"|)(?P<italic>True|False)('|\"|)}"
        searchgroup = re.search(pattern, cls.string, re.I)
        if searchgroup:
            italic = searchgroup.group('italic')
            cls.string = re.sub(pattern, '', cls.string)
            return italic.lower() == "true"
        else:
            italic = cls.default_style['italic']
            cls.string = re.sub(pattern, '', cls.string)
            return italic

    @classmethod
    def _get_font_underline(cls):
        pattern = "{underline ('|\"|)(?P<underline>True|False)('|\"|)}"
        searchgroup = re.search(pattern, cls.string, re.I)
        if searchgroup:
            underline = searchgroup.group('underline')
            cls.string = re.sub(pattern, '', cls.string)
            return underline.lower() == "true"
        else:
            underline = cls.default_style['underline']
            cls.string = re.sub(pattern, '', cls.string)
            return underline

    @classmethod
    def _get_font_color(cls):
        pattern = "{color \((?P<color>\d+\, *\d+\, *\d+)(?P<alpha>\, *\d+)?\)}"
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            color = searchgroup.group('color')
            color = tuple(int(c) for c in color.split(","))
        else:
            color = cls.default_style['color']
        cls.string = re.sub(pattern, '', cls.string)
        return color

    @classmethod
    def _get_font_align(cls):
        pattern = "{(.)?align ('|\"|)(?P<align>(left|center|right))('|\"|)}"
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            align = searchgroup.group('align')
        else:
            align = cls.default_style['align']
        cls.string = re.sub(pattern, '', cls.string)
        return align

    @classmethod
    def _get_font_indent(cls):
        pattern = "{indent (?P<indent>\d+)}"
        searchgroup = re.search(pattern, cls.string)
        if searchgroup:
            indent = searchgroup.group('indent')
        else:
            indent = cls.default_style['indent']
        cls.string = re.sub(pattern, '', cls.string)
        return int(indent)


if __name__ == '__main__':
    mystyle = {
        # At the momment only font filenames are supported. That means the font
        # must be in the same directory as the main script.
        # Or you could (should?) use a resource manager such as
        'font': 'caladea-regular.ttf', #'Fontin.ttf',
        'size': 12,
        'indent': 0,
        'bold': False,
        'italic': False,
        'underline': False,
        'color': (128, 144, 160),  # RGB values
        'align': 'left',
        # if a separate file should be used for italic/bold, speciy it;
        # if not, use None
        'separate_italic':'caladea-italic.ttf', #'Fontin-Italic.ttf',
        'separate_bold': 'caladea-bold.ttf' #'Fontin-Bold.ttf'
    }

    TextStyle.set_default(mystyle)
    plain_text, new_style = TextStyle.split("{bold 'True'}Boldy!")
    print('\n"{}"'.format(new_style))


BGCOLOR = (41, 45, 52)

class SFText:
    def __init__(self, screen, text, font_path='.', style=None):

        if isinstance(text, bytes):
            # print('text is', bytes)
            self.text = text.decode('utf-8')
        elif isinstance(text, str):
            # print('text is', str)
            self.text = text

        self.fonts = Fonts(path=font_path)

        if style:
            TextStyle.set_default(style)

        self.screen = screen
        self.screen_rect = self.screen.get_rect()
        self.bg = self.screen.copy()

        print('parsing text')
        self.parse_text()
        print('done parsing')

    def set_font(self, obj):
        if obj['bold'] and obj['italic'] and obj['separate_bolditalic']:
            obj['font_obj'] = self.fonts.load(
                obj['separate_bolditalic'], obj['size'])
        elif obj['separate_bold'] and obj['bold']:
            obj['font_obj'] = self.fonts.load(
                obj['separate_bold'], obj['size'])
        elif obj['separate_italic'] and obj['italic']:
            obj['font_obj'] = self.fonts.load(
                obj['separate_italic'], obj['size'])
        else:
            obj['font_obj'] = self.fonts.load(
                obj['font'], obj['size'])

    def parse_text(self):
        self.parsed = []
        scr_w = self.screen_rect.width

        self.default_style = TextStyle.default_style
        self.default_style['font_obj'] = self.fonts.load(
            self.default_style['font'], self.default_style['size'])
        self.default_style['w'], self.default_style['h'] = (
            self.default_style['font_obj'].size(' '))

        y = 0
        for line in self.text.splitlines():
            x = 0
            for style in line.split("{style}"):

                text, styled_txt = TextStyle.split(style)

                self.set_font(styled_txt)
                font = styled_txt['font_obj']

                w, h = styled_txt['w'], styled_txt['h'] = font.size(' ')
                # determine the amount of space needed to render text

                wraps = self.wrap_text(text, scr_w, x, styled_txt)

                for wrap in wraps:
                    rect = pygame.Rect((0, 0), font.size(wrap['text']))

                    if (x + wrap['w1'] + w * 3) > scr_w:
                        x = 0
                        y += wrap['h']

                    if len(wraps) == 1 and wrap['align'] == 'center':
                        rect.midtop = (
                            self.screen_rect.centerx,
                            self.screen_rect.bottom + y)
                    else:
                        rect.topleft = (
                            x + w * 3,
                            self.screen_rect.bottom + y)
                    wrap['rect'] = rect
                    wrap['x'] = x
                    wrap['y'] = y
                    if False:
                        print("\n{}: {},".format('x', wrap['x']), end='')
                        print("{}: {},".format('y', wrap['y']), end='')
                        print("{}: {},".format('w', wrap['w']), end='')
                        print("{}: {}".format('h', wrap['h']))
                        print(wrap['text'])
                    self.parsed.append(wrap)

                    x += wrap['w1']
            y += wrap['h']

        print('done parsing')
        self.start_y = 0 - self.screen_rect.h + self.default_style['h']
        self.y = int(self.start_y)
        self.end_y = (
                -sum(p['h'] for p in self.parsed if p['x'] == 0)
                - self.default_style['h'] * 2)

    def wrap_text(self, text, width, _x, styled_txt):
        style = dict(styled_txt)
        x = int(_x)
        wrapped = []
        size = style['font_obj'].size
        c_width = style['w']

        # print(size(text))
        # print(width)
        if size(text)[0] <= (
                width - c_width * 6 - x
        ):
            # print('fits')
            style['text'] = text
            style['w1'] = size(text)[0]
            wrapped.append(style)

            return wrapped
        else:
            # print("doesn't fit")
            # print(text)
            wrapped = [text]
            guessed_length = ((width - c_width * 6 - x) // c_width)
            all_fit = False
            all_fit_iter = 1
            while not all_fit:
                # DEBUG #
                #########
                for i in range(len(wrapped)):
                    fit = size(wrapped[i])[0] < width - c_width * 6 - x
                    iter_length = int(guessed_length)

                    while not fit:
                        # DEBUG #
                        #########
                        if guessed_length <= 2 or iter_length <= 2:
                            # print('if guessed_length <= 2')
                            x = 0
                            guessed_length = (
                                    (width - c_width * 6 - x) // c_width)
                            iter_length = int(guessed_length)
                            continue

                        guess = wrapped[i][:iter_length]
                        # print('while not fit: "{}"'.format(guess))
                        if guess[-1:] not in [" ", ",", ".", "-", "\n"]:
                            # print('if guess[-1:] not in:')
                            iter_length -= 1
                        else:
                            if size(guess)[0] < width - c_width * 6 - x:
                                remains = wrapped[i][iter_length:]
                                wrapped[i] = guess
                                wrapped.append(remains)
                                fit = True
                            else:
                                iter_length -= 1
                    all_fit_iter += 1

                    # print("Cut point: {}".format(iter_length))
                    # print('Guess: ({})"{}"'.format(type(guess), guess))
                    # print('Remains: "{}"'.format(remains))
                    # print("[{}]fit? {}".format(i, fit))
                status = True
                for i in range(len(wrapped)):
                    if size(wrapped[i])[0] >= width:
                        status = False
                all_fit = status

            for i in range(len(wrapped)):
                # print('"{}"'.format(wrapped[i]))
                style['text'] = wrapped[i]
                style['w1'] = size(wrapped[i])[0]
                wrapped[i] = dict(style)

            return wrapped

    def on_update(self):
        for i, p in enumerate(self.parsed[:]):
            rect = p['rect'].move(0, self.y)

            if not isinstance(p['text'], pygame.Surface):
                p['font_obj'].set_bold(False)
                p['font_obj'].set_italic(False)

                if p['bold'] and p['italic'] and not p['separate_bolditalic']:
                    print('pygame-bold', p['text'])
                    p['font_obj'].set_bold(p['bold'])
                    print('pygame-italic', p['text'])
                    p['font_obj'].set_italic(p['italic'])
                elif not p['separate_bold'] and p['bold']:
                    print('pygame-bold', p['text'])
                    p['font_obj'].set_bold(p['bold'])
                elif not p['separate_italic'] and p['italic']:
                    print('pygame-italic', p['text'])
                    p['font_obj'].set_italic(p['italic'])

                p['font_obj'].set_underline(p['underline'])

                p['text'] = p['font_obj'].render(p['text'], 1, p['color'])
            self.screen.blit(p['text'], rect)

            if rect.top >= (
                    self.screen_rect.bottom - self.default_style['h']
            ):
                break

    def scroll(self, y=0):
        if isinstance(y, int):
            self.y += y
            if self.y < self.end_y:
                self.y = self.end_y
            elif self.y > self.start_y:
                self.y = self.start_y
        elif isinstance(y, str):
            if y == 'home':
                self.y = self.start_y
            elif y == 'end':
                self.y = self.end_y

    def post_update(self):
        self.screen.blit(self.bg, (0, 0))

    def on_key_press(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_UP:
            self.scroll(50)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEUP:
            self.scroll(500)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_HOME:
            self.scroll('home')

        elif event.type == pygame.KEYDOWN and event.key == pygame.K_DOWN:
            self.scroll(-50)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEDOWN:
            self.scroll(-500)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_END:
            self.scroll('end')

    def on_mouse_scroll(self, event):
        if event.button == 4:
            self.scroll(50)
        elif event.button == 5:
            self.scroll(-50)


# -------- functions for the web ----------

screen = None
tt = None
editor_text_content = ''
formatedtxt_obj = None


def game_enter(vmstate=None):
    # pygame.init()
    #     surf = pygame.display.set_mode((640, 480))

    global SCR_SIZE, view, ctrl, lu_event, p_event, e_manager, screen, tt, formatedtxt_obj, editor_text_content

    screen = kengi.core.get_screen()
    e_manager = kengi.event.EventManager.instance()
    SCR_SIZE = screen.get_size()

    # ajout dimanche 10.04
    f = open(PATH_SRC_FILE, 'r')
    editor_text_content = f.read()
    f.close()

    formatedtxt_obj = SFText(screen, editor_text_content,
        # run precursor alone
        font_path='editor0/fonts/'
                             )
    fileinfo = PATH_SRC_FILE
    if vmstate:
        print('***** editing file ******* {}'.format(vmstate.cedit_arg))
        fileinfo = vmstate.cedit_arg
    ft = kengi.gui.ImgBasedFont('editor0/myassets/gibson0_font.png', (0, 0, 250))
    tt = ft.render(f'opened file= {fileinfo}', False, (0, 250, 0))


def game_update(t_info=None):
    global p_event, clockk, update_func_sig, screen, tt, formatedtxt_obj, gameover
    for ev in pygame.event.get():
        # need to be done anyway, so we dont overflow the event queue
        if ev.type == pygame.QUIT:
            gameover = True
            return [2, 'niobepolis']
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                return [2, 'niobepolis']
            else:
                formatedtxt_obj.on_key_press(ev)

    screen.fill(BGCOLOR)
    if tt:
        screen.blit(tt, (0, 0))
    formatedtxt_obj.on_update()

    kengi.flip()


def game_exit(vmstate=None):
    kengi.quit()
    pass


# - tom is testing
if __name__ == '__main__':
    game_enter()
    while not gameover:
        game_update()
    game_exit()
