"""
Using pairs of (dedicated_controller, specific_gamestate)
is a nice way to ease state transition in this Poker game

Hence we define every game state in the most explicit manner, BUT we keep
the same model & the same view obj ALL ALONG, when transitioning...
"""
import common
from uth_poker.uth_model import PokerStates
from uth_poker.uth_view import UthView

kengi = common.kengi
MyEvTypes = common.MyEvTypes


# --------------------------------------------
class AnteSelectionCtrl(kengi.EvListener):
    """
    selecting the amount to bet
    """
    def __init__(self, ref_m):
        super().__init__()
        self._mod = ref_m
        self.recent_date = None
        self.autoplay = False
        self._last_t = None

    def on_deal_cards(self, ev):
        self._mod.check()  # =>launch match
        self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.PreFlop)
        # useful ??
        self.recent_date = None
        self.autoplay = False
        self._last_t = None

    # Done directly in the View...
    # maybe we will refactor this again once we have poker Backend written..

    # def on_stack_chip(self, ev):
    #     self._mod.wallet.stake_chip(True)

    def on_cycle_chipval(self, ev):
        chval = self._mod.get_chipvalue()
        if ev.upwards:
            common.chip_scrollup(chval)
        else:
            common.chip_scrolldown(chval)

    def on_bet_undo(self, ev):
        pass  # TODO


class AnteSelectionState(kengi.BaseGameState):
    def __init__(self, ident):
        super().__init__(ident)
        self.c = None

    def enter(self):
        # ensure "manually" that the model has the right state
        common.refmodel._pokerstate = PokerStates.AnteSelection

        # force the reset of the view, bc if its not the 1st match played, its state can be "non-eden"
        # and thats not what we need
        common.refview.turn_off()
        common.refview = UthView(common.refmodel)
        common.refview.turn_on()

        print('[AnteSelectionState] enter!')
        common.refview.show_anteselection()
        self.c = AnteSelectionCtrl(common.refmodel)
        self.c.turn_on()

    def release(self):
        self.c.turn_off()
        common.refview.hide_anteselection()
        print('[AnteSelectionState] release!')
        print()


# --------------------------------------------
class PreFlopCtrl(kengi.EvListener):
    """
    selecting the amount to bet
    """
    def __init__(self, ref_m):
        self.m = ref_m
        super().__init__()

    def _iter_gstate(self):
        self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.Flop)

    def on_check_decision(self, ev):
        self.m.check()
        self._iter_gstate()

    # what button has been clicked? The one with x4 or the one with x3?
    def on_bet_high_decision(self, ev):
        print('Impact x4')
        self.m.select_bet(bullish_choice=True)
        self._iter_gstate()

    def on_bet_decision(self, ev):
        print('Impact x3')
        self.m.select_bet()
        self._iter_gstate()


class PreFlopState(kengi.BaseGameState):
    def __init__(self, ident):
        super().__init__(ident)
        self.c = None

    def enter(self):
        print('ENTER preflop')
        common.refview.show_generic_gui()  # that part of Gui will stay active until bets are over
        self.c = PreFlopCtrl(common.refmodel)
        self.c.turn_on()

    def release(self):
        print('EXIT preflop')
        self.c.turn_off()
        common.refview.hide_generic_gui()


# TODo faut decouper ca et remettre des bouts dans les states/le model
# def on_state_changes(self, ev):
#     if self._mod.stage == PokerStates.AnteSelection:
#         self.info_msg0 = self.small_ft.render('Press BACKSPACE to begin', False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
#         self.info_msg1 = None
#         self.info_msg2 = None
#     else:
#         msg = None
#         if self._mod.stage == PokerStates.PreFlop:
#             msg = ' CHECK, BET x3, BET x4'
#         elif self._mod.stage == PokerStates.Flop:
#             msg = ' CHECK, BET x2'
#         elif self._mod.stage == PokerStates.TurnRiver:
#             msg = ' FOLD, BET x1'
#         if msg:
#             self.info_msg0 = self.small_ft.render(self.ASK_SELECTION_MSG, False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
#             self.info_msg1 = self.small_ft.render(msg, False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
#         # TODO display the amount lost


# --------------------------------------------
class FlopCtrl(kengi.EvListener):
    """
    selecting the amount to bet
    """
    def __init__(self, ref_m,):
        super().__init__()
        self.m = ref_m

    def _iter_gstate(self):
        self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.TurnRiver)

    def on_bet_decision(self, ev):
        # TODO what button has been clicked? The one with x4 or the one with x3?
        self.m.select_bet()
        self._iter_gstate()

    def on_check_decision(self, ev):
        self.m.check()
        self._iter_gstate()

    def on_mousedown(self, ev):
        if self.m.autoplay:
            print('Zap')
            self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.TurnRiver)
            self.m._goto_next_state()  # returns False if there's no next state


class FlopState(kengi.BaseGameState):
    def __init__(self, ident):
        super().__init__(ident)
        self.c = None

    def enter(self):
        print(' ENTER flop')
        if not common.refmodel.autoplay:
            common.refview.show_generic_gui()  # show it again!
            widgetc = common.refview.generic_wcontainer
            widgetc.bet_button.label = 'Bet x2'
            widgetc.bethigh_button.set_active(False)

        self.c = FlopCtrl(common.refmodel)
        self.c.turn_on()

    def release(self):
        print(' LEAVE flop')
        self.c.turn_off()
        common.refview.hide_generic_gui()


# --------------------------------------------
class TurnRiverCtrl(kengi.EvListener):
    """
    selecting the amount to bet
    """
    def __init__(self, ref_m, ref_v):
        super().__init__()
        self.m = ref_m

    def _iter_gstate(self):
        self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.Outcome)

    def on_mousedown(self, ev):
        if self.m.autoplay:
            self.m._goto_next_state()  # returns False if there's no next state
            self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.Outcome)

    def on_bet_decision(self, ev):
        self.m.select_bet()
        print('BET au TR')
        self._iter_gstate()

    def on_check_decision(self, ev):
        self.m.fold()
        print('un check au TR vaut pour Fold!!')
        self._iter_gstate()


class TurnRiverState(kengi.BaseGameState):
    def __init__(self, ident):
        super().__init__(ident)
        self.c = None

    def enter(self):
        print(' ENTER turn-river st.')
        if not common.refmodel.autoplay:
            common.refview.show_generic_gui()
            wcontainer = common.refview.generic_wcontainer
            wcontainer.bethigh_button.set_active(False)
            wcontainer.bet_button.label = 'Bet x1'
            wcontainer.check_button.label = 'Fold'

        self.c = TurnRiverCtrl(common.refmodel, None)
        self.c.turn_on()

    def release(self):
        common.refview.hide_generic_gui()
        print(' LEAVE turn-river st.')
        self.c.turn_off()


# --------------------------------------------
class OutcomeCtrl(kengi.EvListener):
    """
    selecting the amount to bet
    """
    def __init__(self, ref_m):
        super().__init__()
        self._mod = ref_m

    def on_mousedown(self, ev):
        if self._mod.match_over:
            self.pev(kengi.EngineEvTypes.StateChange, state_ident=PokerStates.AnteSelection)

            # COLLECT what was won
            self._mod.wallet.collect_case_victory()

            # force the new round!
            self._mod.init_new_round()


class OutcomeState(kengi.BaseGameState):
    def __init__(self, ident):
        super().__init__(ident)
        self.c = None

    def enter(self):
        print(' ENTER outcome st.')
        self.c = OutcomeCtrl(common.refmodel)
        self.c.turn_on()

    def release(self):
        print(' LEAVE outcome st.')
        self.c.turn_off()


# --------------------------------------------
# class DefaultCtrl(kengi.EvListener):
#     """
#     rq: c'est le controlleur qui doit "dérouler" la partie en fonction du temps,
#     lorsque le joueur a bet ou bien qu'il s'est couché au Turn&River
#     """
#
#     AUTOPLAY_DELAY = 1.0  # sec
#
#     def __init__(self, model, refgame):
#         super().__init__()
#         self.autoplay = False
#
#         self._mod = model
#         self._last_t = None
#         self.elapsed_t = 0
#         self.recent_date = None
#         self.refgame = refgame
#
#     def on_keydown(self, ev):
#         if ev.key == kengi.pygame.K_ESCAPE:
#             self.refgame.gameover = True
#             return
#
#         if self._mod.stage == PokerStates.AnteSelection:
#             if ev.key == kengi.pygame.K_DOWN:
#                 self.pev(MyEvTypes.CycleChipval, upwards=False)
#             elif ev.key == kengi.pygame.K_UP:
#                 self.pev(MyEvTypes.CycleChipval, upwards=True)
#             elif ev.key == kengi.pygame.K_BACKSPACE:
#                 self.pev(MyEvTypes.DealCards)
#             return
#
#         if not self._mod.match_over:
#             # backspace will be used to CHECK / FOLD
#             if ev.key == kengi.pygame.K_BACKSPACE:
#                 if self._mod.stage == PokerStates.TurnRiver:
#                     self._mod.fold()
#                 else:
#                     self._mod.check()
#
#             # enter will be used to select the regular
#             elif ev.key == kengi.pygame.K_RETURN:
#                 if self._mod.stage != PokerStates.AnteSelection:
#                     self._mod.select_bet()  # a BET operation (x3, x2 or even x1, it depends on the stage)
#
#             # case: on the pre-flop the player can select a MEGA-BET (x4) lets use space for this action!
#             elif ev.key == kengi.pygame.K_SPACE:
#                 if self._mod.stage == PokerStates.PreFlop:
#                     self._mod.select_bet(True)
#
#     def on_mousedown(self, ev):
#         if self._mod.match_over:
#             # force a new round!
#             self._mod.reboot_match()
#
#     def on_rien_ne_va_plus(self, ev):
#         self.autoplay = True
#         self.elapsed_t = 0
#         self._last_t = None
#
#     def on_update(self, ev):
#         if self.autoplay:
#             if self._last_t is None:
#                 self._last_t = ev.curr_t
#             else:
#                 dt = ev.curr_t - self._last_t
#                 self.elapsed_t += dt
#                 self._last_t = ev.curr_t
#                 if self.elapsed_t > self.AUTOPLAY_DELAY:
#                     self.elapsed_t = 0
#                     rez = self._mod._goto_next_state()  # returns False if there's no next state
#                     if not rez:
#                         self.autoplay = False
#                         self.elapsed_t = 0
#                         self._last_t = None
