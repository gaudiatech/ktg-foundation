import katagames_sdk as katasdk
katasdk.bootstrap()


from TextEditor import TextEditor
# from TextEditorView import TextEditorView
from TextEditorAsciiV import TextEditorAsciiV  # W-i-p replacing the view
import sharedstuff


# class Sharedstuff:
#     def __init__(self):
#         self.disp_save_ico = None  # contains info 'bout time when it needs display
#         self.dump_content = None
#         self.kartridge_output = None
#         self.screen = None
#         self.editor = None
#         self.file_label = None  # for showing what is being edited
#
#         self.editor_blob = None
#         self.editor_view = None


# - gl. variables
kengi = katasdk.kengi
EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame
glclock = pygame.time.Clock()
ticker = None
editor_text_content = ''
formatedtxt_obj = None
# sharedstuff = None


# - constants
MFPS = 50
SAVE_ICO_LIFEDUR = 1.33  # sec

# constant to have smth just like "lorem ipsum" text, if needed
DUMMY_PYCODE = """
# Define the cloud object by extending pygame.sprite.Sprite
# Use an image for a better-looking sprite
class Cloud(pygame.sprite.Sprite):
    def __init__(self):
        super(Cloud, self).__init__()
        self.surf = pygame.image.load("cloud.png").convert()
        self.surf.set_colorkey((0, 0, 0), RLEACCEL)
        # The starting position is randomly generated
        self.rect = self.surf.get_rect(
            center=(
                random.randint(SCREEN_WIDTH + 20, SCREEN_WIDTH + 100),
                random.randint(0, SCREEN_HEIGHT),
            )
        )

    # Move the cloud based on a constant speed
    # Remove the cloud when it passes the left edge of the screen
    def update(self):
        self.rect.move_ip(-5, 0)
        if self.rect.right < 0:
            self.kill()
"""

# constant defined to implement a crude formatting
# one can display keywords simply by using a different color for these words
PY_KEYWORDS = (
    # types
    'bool', 'list', 'tuple', 'str', 'int', 'float',
    # flow control
    'if', 'else', 'elif', 'for', 'while',
    # built-in functions
    'len', 'not', 'in', 'enumerate', 'range'
    # literals
    'None', 'True', 'False',
    # misc
    'def', 'return', 'class', 'self'
)


class CustomGameTicker:
    def __init__(self):
        self.lu_event = kengi.event.CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
        self.paint_event = kengi.event.CgmEvent(EngineEvTypes.PAINT, screen=kengi.get_surface())
        self.manager = kengi.event.EventManager.instance()

    def refresh(self):
        self.manager.post(self.lu_event)
        self.manager.post(self.paint_event)
        self.manager.update()


# - functions for the web -
def game_enter(vmstate):
    global ticker
    katasdk.set_mode('hd')

    ticker = CustomGameTicker()

    # sharedstuff = Sharedstuff()
    sharedstuff.screen = kengi.get_surface()
    scr_size = sharedstuff.screen.get_size()

    offset_x = 0  # offset from the left border of the pygame window
    offset_y = 10  # offset from the top border of the pygame window

    # set text content for the editor
    if vmstate and vmstate.cedit_arg is not None:  # on peut pogner une cible a editer!
        fileinfo = vmstate.cedit_arg
        if vmstate.cedit_arg in vmstate.gamelist_func():
            infomsg = '** edit existing file {} **'.format(vmstate.cedit_arg)
            # AJOUT mercredi 20/04/22 ca peut que marcher en local cela!
            f = open(f'roms/{fileinfo}.py', 'r')
            py_code = f.read()
            f.close()
        else:  # game creation
            infomsg = '** creating new file {} **'.format(vmstate.cedit_arg)
            py_code = vmstate.blankfile_template
        print(infomsg)
    else:
        fileinfo = '?'
        py_code = DUMMY_PYCODE  # just a sample, like just like a LoremIpsum.py ...

    # another way to do it --------------
    # ajout dimanche 10.04
    # f = open(PATH_SRC_FILE, 'r')
    # editor_text_content = f.read()
    # f.close()
    # formatedtxt_obj = SFText(screen, editor_text_content,
    # run precursor alone
    #    font_path='editor0/fonts/')
    # xxx -> 'editor/**assets/gibson0_font.png'
    # if vmstate:
    #    print('***** editing file ******* {}'.format(vmstate.cedit_arg))
    #    ft = kengi.gui.ImgBasedFont(xxx, (0, 0, 250))
    #    tt = ft.render('bidule: ' + vmstate.cedit_arg, False, (0, 250, 0))
    # ------------

    editor_blob = TextEditor(
        offset_x, offset_y, scr_size[0], scr_size[1]-offset_y, line_numbers_flag=True
    )
    sharedstuff.file_label = editor_blob.currentfont.render(f'opened file= {fileinfo}', False, (0, 250, 0))
    editor_blob.set_text_from_string(py_code)

    editor_view = TextEditorAsciiV(editor_blob, MFPS)
    editor_view.turn_on()


def game_update(t_info=None):
    global gameover, ticker
    ticker.lu_event.curr_t = t_info
    ticker.refresh()  # will update models,view + proc the event manager

    if sharedstuff.kartridge_output:
        gameover = True
        return sharedstuff.kartridge_output

    glclock.tick(MFPS)


def game_exit(vmstate):
    if vmstate:
        if vmstate.cedit_arg is not None and sharedstuff.dump_content is not None:
            # has to be shared with the VM, too
            # let's hack the .cedit_arg attribute, use it as a return value container
            vmstate.cedit_arg = katasdk.mt_a + vmstate.cedit_arg + katasdk.mt_b + sharedstuff.dump_content
            print('.cedit_arg hacked!')

    print('Editor, over')
    kengi.quit()


# --------------------------------------------
#  Entry pt, local ctx
# --------------------------------------------
if __name__ == '__main__':
    import time

    game_enter(katasdk.vmstate)
    gameover = False
    while not gameover:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(katasdk.vmstate)
