# from uth_model import WalletMod
import common
import time


kengi = common.kengi


class UthCtrl(kengi.EvListener):
    """
    rq: c'est le controlleur qui doit "dérouler" la partie en fonction du temps,
    lorsque le joueur a bet ou bien qu'il s'est couché au Turn&River
    """

    AUTOPLAY_DELAY = 1.0  # sec

    def __init__(self, model, refgame):
        super().__init__()
        self.autoplay = False

        self._mod = model
        self._last_t = None
        self.elapsed_t = 0
        self.recent_date = None
        self.refgame = refgame

    def on_new_match(self, ev):
        self.recent_date = None
        self.autoplay = False
        self._last_t = None

    def on_keydown(self, ev):
        if ev.key == kengi.pygame.K_ESCAPE:
            self.refgame.gameover = True

        # backspace will be used to CHECK / FOLD
        elif ev.key == kengi.pygame.K_BACKSPACE:
            print('[Ctrl] - player check')
            self._mod.select_check()

        # enter will be used to select the regular BET option, x3, x2 or x1 depends on the stage
        elif ev.key == kengi.pygame.K_RETURN:
            print('[Ctrl] - player regular bet')
            self._mod.select_bet(0)

        # case: at the beginning of the game the player can select the MEGA-BET x4 lets use space for that
        # we'll also use space to begin the game. State transition: init -> discov
        elif ev.key == kengi.pygame.K_SPACE:
            print('[Ctrl] - player maxi bet, x4')
            if self._mod.stage != UthModel.BET_PHASE:
                if self._mod.stage == UthModel.DISCOV_ST_CODE:
                    self._mod.input_bet(1)

    def on_end_round_requested(self, ev):
        self.autoplay = True
        self._mod.evolve_state()

        self.elapsed_t = 0
        self._last_t = None

    def on_update(self, ev):
        if self.autoplay:
            if self._last_t is None:
                self._last_t = ev.curr_t
                return
            dt = ev.curr_t - self._last_t
            self.elapsed_t += dt
            self._last_t = ev.curr_t

            if self.elapsed_t > self.AUTOPLAY_DELAY:
                self.elapsed_t = 0
                self._mod.evolve_state()
