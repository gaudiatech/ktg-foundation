
import katagames_sdk as katasdk

kengi = katasdk.bootstrap('super_retro')

pygame = kengi.pygame
screen = kengi.get_surface()
width, height = screen.get_size()
IMGPATH = 'alphabet/myassets/gibson0_font.png'
INIT_TXT = 'hello user this\nis\nsome\ndope\ntext'
ALT_TXT = 'i\nunderstand that\nyou watch the console'

homemade_ft_obj = block = None


def game_enter(vmstate=None):
    global block, homemade_ft_obj
    homemade_ft_obj = kengi.gui.ImgBasedFont(IMGPATH, (0, 255, 0))
    block = kengi.gui.TextBlock(homemade_ft_obj, INIT_TXT, (0, 0, 0))
    block.rect.center = (width // 2, height // 2)  # lets center the text block


def game_update(infot=None):
    global ended
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            ended = True
            return [1, None]

        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_BACKSPACE:
                ended = True
                return [2, 'niobepolis']
            elif ev.key == pygame.K_RETURN:
                block.text_align = (block.text_align + 1) % 2  # switch text align
            elif ev.key == pygame.K_SPACE:
                block.text = ALT_TXT

        elif ev.type == pygame.KEYUP:
            if not pygame.key.get_pressed()[pygame.K_SPACE]:
                block.text = INIT_TXT
    screen.fill('white')
    block.draw(screen)
    kengi.flip()


def game_exit(vmstate=None):
    kengi.quit()


if __name__ == '__main__':
    print('*~*~*\npress and hold the space bar ; press ENTER to change alignment')
    ended = False
    game_enter()
    while not ended:
        game_update()
    game_exit()
