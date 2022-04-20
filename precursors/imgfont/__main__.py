import katagames_sdk as katasdk

katasdk.bootstrap('super_retro')
kengi = katasdk.kengi
pygame = kengi.pygame


# -----------------
# code below borrowed from the 'Gleamshroom' game, engine.py
# authored by DaFluffyPotato (https://itch.io/profile/dafluffypotato)

# import katagames_sdk as katasdk
# kengi = katasdk.import_kengi()
def swap_color(img, old_c, new_c):
    img.set_colorkey(old_c)
    print(type(img))
    surf = img.copy()
    surf.fill(new_c)
    surf.blit(img, (0, 0))
    return surf


def clip(surf, x, y, x_size, y_size):
    handle_surf = surf.copy()
    clip_rect = pygame.Rect(x, y, x_size, y_size)

    # TODO fix pygame.surface.set_clip, get_clip
    handle_surf.set_clip(clip_rect)
    t = handle_surf.get_clip()
    # t = handle_surf

    # TODO fix pygame.surface.subsurface(rect)
    image = surf.subsurface(t)
    return image.copy()
    #print(' TYPE ', str(handle_surf))
    #return handle_surf


def load_font_img(path, font_color):
    fg_color = (255, 0, 0)
    bg_color = (0, 0, 0)
    font_img = pygame.image.load(path).convert()
    # TODO reactive color
    font_img = swap_color(font_img, fg_color, font_color)

    last_x = 0
    letters = []
    letter_spacing = []
    for x in range(font_img.get_width()):
        if font_img.get_at((x, 0))[0] == 127:
            letters.append(
                clip(font_img, last_x, 0, x - last_x, font_img.get_height())
            )
            letter_spacing.append(x - last_x)
            last_x = x + 1
        x += 1
    for letter in letters:
        letter.set_colorkey(bg_color)
    return letters, letter_spacing, font_img.get_height()


class Font:
    def __init__(self, path, color):
        self.letters, self.letter_spacing, self.line_height = load_font_img(path, color)

        self.font_order = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R',
                           'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j',
                           'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '.', '-',
                           ',', ':', '+', '\'', '!', '?', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' ] #, '(', ')',
                           # '/', '_', '=', '\\', '[', ']', '*', '"', '<', '>', ';']
        print(len(self.font_order))
        print(len(self.letters))
        if len(self.font_order) > len(self.letters):
            raise ValueError('cannot find enough letters in image ' + path)

        self.space_width = self.letter_spacing[0]
        self.base_spacing = 1
        self.line_spacing = 2

    def width(self, text):
        text_width = 0
        for char in text:
            if char == ' ':
                text_width += self.space_width + self.base_spacing
            else:
                text_width += self.letter_spacing[self.font_order.index(char)] + self.base_spacing
        return text_width

    def render(self, text, surf, loc, line_width=0):
        x_offset = 0
        y_offset = 0
        if line_width != 0:
            spaces = []
            x = 0
            for i, char in enumerate(text):
                if char == ' ':
                    spaces.append((x, i))
                    x += self.space_width + self.base_spacing
                else:
                    x += self.letter_spacing[self.font_order.index(char)] + self.base_spacing
            line_offset = 0
            for i, space in enumerate(spaces):
                if (space[0] - line_offset) > line_width:
                    line_offset += spaces[i - 1][0] - line_offset
                    if i != 0:
                        text = text[:spaces[i - 1][1]] + '\n' + text[spaces[i - 1][1] + 1:]
        for char in text:
            if char not in ['\n', ' ']:
                surf.blit(self.letters[self.font_order.index(char)], (loc[0] + x_offset, loc[1] + y_offset))
                x_offset += self.letter_spacing[self.font_order.index(char)] + self.base_spacing
            elif char == ' ':
                x_offset += self.space_width + self.base_spacing
            else:
                y_offset += self.line_spacing + self.line_height
                x_offset = 0


# -----------------------------


# kengi.core.init('super_retro')
scr = kengi.core.get_screen()
gameover = False
ft_obj = ft_obj2 = None

allchars = ''
for ccode in range(ord('a'), ord('z') + 1):
    allchars += chr(ccode)
for ccode in range(ord('A'), ord('Z') + 1):
    allchars += chr(ccode)


def game_enter(vmstate=None):
    global ft_obj, ft_obj2
    ft_obj, ft_obj2 = (
        Font('imgfont/myassets/large_font.png', 'darkblue'),
        Font('imgfont/myassets/small_font.png', 'green')
    )


def game_update(infot=None):
    global gameover, ft_obj, ft_obj2
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            gameover = True

    scr.fill('antiquewhite3')
    ft_obj.render('salut mec', scr, (32, 128))
    ft_obj2.render(allchars, scr, (16, 24))
    kengi.core.display_update()


def game_exit(vmstate=None):
    kengi.quit()
    print('gentle pgm EXIT')


if __name__ == '__main__':  # local run
    game_enter()
    while not gameover:
        game_update()
    game_exit()
