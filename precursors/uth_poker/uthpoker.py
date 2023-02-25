"""
[Rules]
Ultimate Texas Hold’em is played against the casino, so you’ll be up against the dealer. There can be multiple players
at the table, but that doesn’t change much at all as your only goal is to beat the dealer. Whether other players win or
lose is of no significance to you.

#1 > after paying Ante+Blind, the dealer gives you 2 cards. You can either: Check / Bet 3x the ante / Bet 4x the ante
(If you decide to bet either 3x or 4x after seeing your hand, the dealer will deal the flop, the turn & the river
without you having any further betting options)

#2 > In case you opt to check, the dealer will deal out the flop. Now you can either: Check / Bet 2x the ante
(If you bet, the dealer will deal the turn & the river without you having any further betting options)

#3 > In case you opt to check, the dealer will deal the turn & the river. This is the final betting round. This time,
you can either: Fold / Bet 1x the ante. You cannot check anymore since the river is out.
"""
import common
from game_logic import AnteSelectionState, PreFlopState, FlopState, TurnRiverState, OutcomeState
from uth_model import UthModel
from uth_view import UthView


# aliases
kengi = common.kengi
MyEvTypes = common.MyEvTypes

# const
WARP_BACK = [2, 'niobepolis']
CARD_SIZE_PX = (69, 101)


class PokerUth(kengi.GameTpl):
    """
    rodelizes the whole game!
    """

    def __init__(self):
        self._manager = None
        super().__init__()
        self.m = self.v = None

    def init_video(self):
        kengi.init(2)

    def setup_ev_manager(self):
        self._manager = kengi.get_ev_manager()
        self._manager.setup(common.MyEvTypes)

    def enter(self, vms=None):
        super().enter(vms)

        kengi.declare_game_states(
            common.PokerStates,
            {
                common.PokerStates.AnteSelection: AnteSelectionState,
                common.PokerStates.PreFlop: PreFlopState,
                common.PokerStates.Flop: FlopState,
                common.PokerStates.TurnRiver: TurnRiverState,
                common.PokerStates.Outcome: OutcomeState
            }
        )
        self.m = UthModel()
        common.refmodel = self.m

        self.v = UthView(self.m)
        common.refview = self.v
        self.v.turn_on()


game_obj = PokerUth()
common.refgame = game_obj
# if not isinstance(common.dyncomp, common.DynComponent):  # only if katasdk is active
#     katasdk.gkart_activation(game_obj)

game_obj.loop()
