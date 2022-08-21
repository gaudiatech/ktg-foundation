import pygame

import katagames_sdk as katasdk


kengi = katasdk.kengi
Receiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes


class EditorCtrl(Receiver):
    def __init__(self, ref_mod):
        super().__init__()
        self._mod = ref_mod

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
                self.pev(EngineEvTypes.GAMEENDS)
                print('[EditorCtrl] thrownig gameends event')
