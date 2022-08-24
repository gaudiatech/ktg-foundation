import time

import katagames_sdk as katasdk
katasdk.bootstrap()

from ctrl import EditorCtrl
from heavy_mod.EditorModel import EditorModel
from heavy_mod.shared import DIR_CARTRIDGES
from model_addon import ScProviderFactory, VirtualFilesetBuffer, sharedstuff_obj
from view import CapelloEditorView


kengi = katasdk.kengi
EngineEvTypes = kengi.event.EngineEvTypes
pygame = kengi.pygame
gameover = False


# ----------------------------------------
#  BODY
@katasdk.tag_gameenter
def game_enter(vmstate):
    global lu_event, paint_ev, e_manager
    kengi.init(2)
    lu_event = kengi.event.CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    paint_ev = kengi.event.CgmEvent(EngineEvTypes.PAINT, screen=None)
    paint_ev.screen = kengi.get_surface()
    e_manager = kengi.event.EventManager.instance()

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
            with open(f'{DIR_CARTRIDGES}/{fileinfo}.py', 'r') as ff:
                pycode_vfileset = VirtualFilesetBuffer(ff.read())

        else:  # game creation
            curr_edition_info = '(creating the new file {})'.format(fileinfo)
            pycode_vfileset = VirtualFilesetBuffer(vmstate.blankfile_template)
        print(curr_edition_info)

    scr_size = paint_ev.screen.get_size()
    # {M}
    # le lightweights model
    # editor_blob = EditorModel(
    #     pycode_vfileset,
    #     offset_x, offset_y,  # offset_y is 0
    #     scr_size[0], scr_size[1] - offset_y, line_numbers_flag=True
    # )
    # --- modele issu de editor4
    offset_x = 32  # offset from the left border of the pygame window
    offset_y = 100  # offset from the top border of the pygame window

    editor_blob = EditorModel(
        offset_x, offset_y, scr_size[0]-55, 3+scr_size[1]//2, kengi.get_surface(), line_numbers_flag=True
    )
    editor_view = CapelloEditorView(editor_blob)
    editor_view.set_bg_color(pygame.color.Color('midnightblue'))
    editor_view.set_syntax_highlighting(True)

    sharedstuff_obj.file_label = None
    # editor_blob.currentfont.render(f'opened file= {fileinfo}', False, (0, 250, 0))
    editor_blob.set_text_from_list(pycode_vfileset['main.py'])
    sharedstuff_obj.screen = kengi.get_surface()
    editor_blob.currentfont = pygame.font.Font(None, 24)

    # {V}
    # editor_view = ModernView(editor_blob, maxfps=45)
    editor_view.turn_on()

    # {C}
    ectrl = EditorCtrl(editor_blob, sharedstuff_obj)
    ectrl.turn_on()

    if not dummy_file:
        if existing_file:
            if vmstate.has_ro_flag(fileinfo):
                editor_view.locked_file = True


@katasdk.tag_gameupdate
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


@katasdk.tag_gameexit
def game_exit(vmstate):
    if vmstate:
        if vmstate.cedit_arg is not None and sharedstuff_obj.dump_content is not None:
            # has to be shared with the VM too
            # Let's hack the .cedit_arg attribute and use it as a return value container
            vmstate.cedit_arg = katasdk.mt_a + vmstate.cedit_arg + katasdk.mt_b + sharedstuff_obj.dump_content
            print('.cedit_arg hacked!')
    print('Editor, over')
    kengi.quit()


if __name__ == '__main__':
    # you can uncomment this only if you run the editor via the VM (not stand-alone)
    # vms = katasdk.get_vmstate()
    game_enter(None)
    while not gameover:
        uresult = game_update(time.time())
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(None)
