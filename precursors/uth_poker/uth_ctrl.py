import common
from uth_poker.uth_model import PokerStates


kengi = common.kengi
MyEvTypes = common.MyEvTypes


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

    def on_chip_cycle(self, ev):
        chval = self._mod.get_chipvalue()
        if ev.upwards:
            common.chip_scrollup(chval)
        else:
            common.chip_scrolldown(chval)

    def on_keydown(self, ev):
        if ev.key == kengi.pygame.K_ESCAPE:
            self.refgame.gameover = True
            return

        if self._mod.stage == PokerStates.AnteSelection:
            if ev.key == kengi.pygame.K_DOWN:
                self.pev(MyEvTypes.ChipCycle, upwards=False)
            elif ev.key == kengi.pygame.K_UP:
                self.pev(MyEvTypes.ChipCycle, upwards=True)
            elif ev.key == kengi.pygame.K_BACKSPACE:
                self._mod.check()
            return

        if not self._mod.match_over:
            # backspace will be used to CHECK / FOLD
            if ev.key == kengi.pygame.K_BACKSPACE:
                if self._mod.stage == PokerStates.TurnRiver:
                    self._mod.fold()
                else:
                    self._mod.check()

            # enter will be used to select the regular
            elif ev.key == kengi.pygame.K_RETURN:
                if self._mod.stage != PokerStates.AnteSelection:
                    self._mod.select_bet()  # a BET operation (x3, x2 or even x1, it depends on the stage)

            # case: on the pre-flop the player can select a MEGA-BET (x4) lets use space for this action!
            elif ev.key == kengi.pygame.K_SPACE:
                if self._mod.stage == PokerStates.PreFlop:
                    self._mod.select_bet(True)

    def on_mousedown(self, ev):
        if self._mod.match_over:
            # force a new round!
            self._mod.reboot_match()

    def on_rien_ne_va_plus(self, ev):
        self.autoplay = True
        self.elapsed_t = 0
        self._last_t = None

    def on_update(self, ev):
        if self.autoplay:
            if self._last_t is None:
                self._last_t = ev.curr_t
            else:
                dt = ev.curr_t - self._last_t
                self.elapsed_t += dt
                self._last_t = ev.curr_t
                if self.elapsed_t > self.AUTOPLAY_DELAY:
                    self.elapsed_t = 0
                    rez = self._mod._goto_next_state()  # returns False if there's no next state
                    if not rez:
                        self.autoplay = False
                        self.elapsed_t = 0
                        self._last_t = None
