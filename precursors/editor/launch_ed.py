import time
import katagames_sdk as katasdk
katasdk.bootstrap()

from CapelloEditorView import CapelloEditorView
from ctrl import EditorCtrl
from ScProviderFactory import ScProviderFactory

# i try to make the model lightweight... {
# ++ use the lean version
from model import TextEditor, sharedstuff_obj

# ++ use legacy model
# from TextEditor import TextEditor
# from TextEditor import sharedstuff as sharedstuff_obj
# end of attempts}

from VirtualFilesetBuffer import VirtualFilesetBuffer


# rest of import instructions...
from TextEditorAsciiV import TextEditorAsciiV
from TextEditorView import TextEditorView
from sharedstuff import MFPS

kengi = katasdk.kengi
pygame = kengi.pygame
ascii_canvas = kengi.ascii
lu_event = paint_ev = e_manager = None
EngineEvTypes = kengi.event.EngineEvTypes


def game_enter(vmstate):
    global lu_event, paint_ev, e_manager
    kengi.init(2)
    # ascii_canvas.init(1)  # pass the level of upscaling
    lu_event = kengi.event.CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_ev = kengi.event.CgmEvent(EngineEvTypes.PAINT, screen=None)
    paint_ev.screen = kengi.get_surface()
    e_manager = kengi.event.EventManager.instance()
    offset_x = 0  # offset from the left border of the pygame window
    offset_y = 0  # offset from the top border of the pygame window
    existing_file = False
    # set text content for the editor
    if vmstate is None:
        # local
        provider = ScProviderFactory.build(local_target='LoremIpsum.py')
        pycode_vfileset = VirtualFilesetBuffer(provider.get_source_code())  # just a sample, like just like a LoremIpsum.py ...
        dummy_file = True
    else:
        dummy_file = False
        if vmstate.cedit_arg is None:
            # on peut pogner l'editeur pour montrer son code
            fileinfo = 'editor'
        else:
            fileinfo = vmstate.cedit_arg
        # - fetch code for editing
        if vmstate.has_game(fileinfo):
            existing_file = True
            curr_edition_info = '(editing an existing file {})'.format(fileinfo)
            # AJOUT mercredi 20/04/22 ca peut que marcher en local cela!
            with open(f'{FOLDER_CART}/{fileinfo}.py', 'r') as ff:
                pycode_vfileset = VirtualFilesetBuffer(ff.read())
        else:  # game creation
            curr_edition_info = '(creating the new file {})'.format(fileinfo)
            pycode_vfileset = vmstate.blankfile_template
        print(curr_edition_info)

    # --- another way to do it ---
    # ajout dimanche 10.04
    # f = open(PATH_SRC_FILE, 'r')
    # editor_text_content = f.read()
    # f.close()
    # formatedtxt_obj = SFText(screen, editor_text_content,
    # run precursor alone
    #    font_path='editor0/fonts/')
    # xxx -> 'editor/**assets/gibson0_font.xxx'
    # if vmstate:
    #    print('***** editing file ******* {}'.format(vmstate.cedit_arg))
    #    ft = kengi.gui.ImgBasedFont(xxx, (0, 0, 250))
    #    tt = ft.render('bidule: ' + vmstate.cedit_arg, False, (0, 250, 0))

    scr_size = paint_ev.screen.get_size()
    # {M}
    editor_blob = TextEditor(
        pycode_vfileset,
        offset_x, offset_y,  # offset_y is 0
        scr_size[0], scr_size[1] - offset_y, line_numbers_flag=True
    )
    sharedstuff_obj.file_label = None  # editor_blob.currentfont.render(f'opened file= {fileinfo}', False, (0, 250, 0))
    editor_blob.set_text_from_list(pycode_vfileset['main.py'])
    sharedstuff_obj.screen = kengi.get_surface()
    editor_blob.currentfont = pygame.font.Font(None, 24)

    # {V}
    # *******LEGACY
    # editor_view = TextEditorView(editor_blob, MFPS, shared=sharedstuff_obj)
    # *******ASCII-based
    # editor_view = TextEditorAsciiV(editor_blob, MFPS, shared=sharedstuff_obj)
    # *******CAPELLO(the modern way)
    editor_view = CapelloEditorView(editor_blob)
    editor_view.turn_on()

    # {C}
    ectrl = EditorCtrl(editor_blob)
    ectrl.turn_on()

    if not dummy_file:
        if existing_file:
            if vmstate.has_ro_flag(fileinfo):
                editor_view.locked_file = True


def game_update(t_info=None):
    global lu_event, paint_ev, gameover, e_manager
    lu_event.curr_t = t_info
    e_manager.post(lu_event)
    e_manager.post(paint_ev)
    e_manager.update()
    kengi.flip()
    if sharedstuff_obj.kartridge_output:
        gameover = True
        return sharedstuff_obj.kartridge_output


def game_exit(vmstate):
    if vmstate:
        if vmstate.cedit_arg is not None and sharedstuff_obj.dump_content is not None:
            # has to be shared with the VM too
            # Let's hack the .cedit_arg attribute and use it as a return value container
            vmstate.cedit_arg = katasdk.mt_a + vmstate.cedit_arg + katasdk.mt_b + sharedstuff_obj.dump_content
            print('.cedit_arg hacked!')
    print('Editor, over')
    kengi.quit()


# -------------------
# entry pt, local ctx
# -------------------
if __name__ == '__main__':
    game_enter(katasdk.vmstate)
    gameover = False
    while not gameover:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(katasdk.vmstate)
