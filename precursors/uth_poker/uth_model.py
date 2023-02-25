import common
from WalletModel import WalletModel


MyEvTypes = common.MyEvTypes

kengi = common.kengi
CardDeck = kengi.tabletop.CardDeck
find_best_ph = kengi.tabletop.find_best_ph

PokerStates = common.PokerStates


class UthModel(kengi.Emitter):
    """
    Uth: Ultimate Texas Holdem
    this is a model class, it handles "poker states" (mostly)
    """

    def __init__(self):
        super().__init__()
        self.wallet = WalletModel(250)  # TODO link with CR and use the real wealth value

        self.match_over = False
        self.bet_done = False
        self.player_folded = False

        self.result = None

        # ---------------
        # CARD MANAGEMENT
        # ---------------
        self.deck = CardDeck()
        self.visibility = {
            'dealer1': False,
            'dealer2': False,

            'flop3': False,
            'flop2': False,
            'flop1': False,

            'turn': False,
            'river': False,

            'player1': False,
            'player2': False
        }
        # temp attributes to save best virtual hand (5 cards chosen out of 7)
        self.dealer_vhand = self.player_vhand = None

        # stored lists of cards
        self.dealer_hand = []
        self.player_hand = []
        self.flop_cards = []
        self.turnriver_cards = []

        # ----------------
        # STATE MANAGEMENT
        # ----------------
        self._pokerstate = None
        self.possible_bet_factor = None  # will be [3, 4] then [2, ] then [1, ]
        self._goto_next_state()

    @property
    def autoplay(self):
        return self.bet_done or self.player_folded

    def quantify_reward(self):
        return self.wallet.prev_gain

    def get_card_code(self, info):
        """
        can be anythin in [
         dealer1, dealer2, player1, player2, flop3, flop2, flop1,
         river, turn
        ]
        """
        if info == 'dealer1':
            return self.dealer_hand[0].code
        if info == 'dealer2':
            return self.dealer_hand[1].code
        if info == 'player1':
            return self.player_hand[0].code
        if info == 'player2':
            return self.player_hand[1].code
        if info == 'flop3':
            return self.flop_cards[2].code
        if info == 'flop2':
            return self.flop_cards[1].code
        if info == 'flop1':
            return self.flop_cards[0].code
        if info == 'turn':
            return self.turnriver_cards[0].code
        if info == 'river':
            return self.turnriver_cards[1].code
        raise ValueError('unrecognized >info< argument passed to UthModel.get_card_code')

    @property
    def stage(self):
        return self._pokerstate

    def get_chipvalue(self):
        return self.wallet.curr_chipval

    def set_chipvalue(self, newv):
        self.wallet.curr_chipval = newv

    def get_balance(self):
        return self.wallet.get_balance()

    def get_all_bets(self):
        return self.wallet.all_infos

    def _proc_state(self, newstate):
        if newstate == PokerStates.AnteSelection:
            self.possible_bet_factor = None
            # self.init_new_round()

        elif newstate == PokerStates.PreFlop:
            print('hi im in preflop')
            self.possible_bet_factor = [3, 4]
            # cards have been dealt !
            self.wallet.ready_to_start = True

            # TODO should be deck.draw_cards(2) or smth
            self.dealer_hand.extend(self.deck.deal(2))
            self.player_hand.extend(self.deck.deal(2))
            self.visibility['player2'] = self.visibility['player1'] = True

        elif newstate == PokerStates.Flop:
            print('hi im in the flop state')
            self.possible_bet_factor = [2, ]
            for k in range(1, 3 + 1):
                self.visibility[f'flop{k}'] = True
            self.flop_cards.extend(self.deck.deal(3))

        elif newstate == PokerStates.TurnRiver:
            print('eee im in the TurnRiver state')
            self.possible_bet_factor = [1, ]
            # betting => betx2, or check
            self.turnriver_cards.extend(self.deck.deal(2))
            self.visibility['turn'] = self.visibility['river'] = True

        elif newstate == PokerStates.Outcome:
            self.possible_bet_factor = None
            self.visibility['dealer1'] = self.visibility['dealer2'] = True

            # state dedicated to blit the type of hand (Two pair, Full house etc) + the outcome
            if self.player_folded:
                self.result = -1
                self.wallet.impact_fold()

            else:
                self.dealer_vhand = find_best_ph(self.dealer_hand + self.flop_cards + self.turnriver_cards)
                self.player_vhand = find_best_ph(self.player_hand + self.flop_cards + self.turnriver_cards)
                self.result = self.wallet.resolve(self.player_vhand, self.dealer_vhand)

            self.match_over = True
            self.pev(MyEvTypes.MatchOver, won=self.result)

    def _goto_next_state(self):
        """
        iterate the game (pure game logic)

        !! for a much cleaner structure, this should be done via
         --- a set of (GameStates, controller) pairs ---
        TODO refactoring Uth
        """
        if self._pokerstate is None:
            self.init_new_round()

        tr_table = {
            None: PokerStates.AnteSelection,
            PokerStates.AnteSelection: PokerStates.PreFlop,
            PokerStates.PreFlop: PokerStates.Flop,
            PokerStates.Flop: PokerStates.TurnRiver,
            PokerStates.TurnRiver: PokerStates.Outcome,
            PokerStates.Outcome: None
        }
        self._pokerstate = tr_table[self._pokerstate]

        # since February, the model should not decide what game state we are in,
        # let controllers do this job !
        # TODO finish the refactoring
        # - specific update of the model !!!
        self._proc_state(self._pokerstate)  # these actions should probably be moved to specific controllers

        # if self._pokerstate is None:
        #     return False
        # else:
        #        ........... _proc_state ...........  # describe &exec what actions are needed to update the model
        #     self.pev(MyEvTypes.StateChanges, pokerstate=self._pokerstate)
        #     return True

    def check(self):
        self._goto_next_state()

    def fold(self):
        self.player_folded = True
        self._goto_next_state()

    @property
    def pl_hand_description(self):
        return self.player_vhand.description

    @property
    def dl_hand_description(self):
        return self.dealer_vhand.description

    def init_new_round(self):
        print('-------------model init new round --------------------')
        self.match_over = False
        self.wallet.reset_bets(int(self.wallet.prev_victorious))

        del self.dealer_hand[:]
        del self.player_hand[:]
        del self.flop_cards[:]
        del self.turnriver_cards[:]

        for lname in self.visibility.keys():
            self.visibility[lname] = False

        self.deck.reset()
        self.bet_done = False
        self.player_folded = False
        self.pev(MyEvTypes.NewMatch)

    def select_bet(self, bullish_choice=False):
        if bullish_choice and self._pokerstate != PokerStates.PreFlop:
            raise RuntimeError('non valid bullish_choice argument detected!')
        b_factor = self.possible_bet_factor[0]
        if bullish_choice:
            b_factor = self.possible_bet_factor[1]
        self.wallet.bet(b_factor)
        self.bet_done = True

        self._goto_next_state()
        self.pev(MyEvTypes.RienNeVaPlus)

    # def select_check(self):
    #     if self.stage == self.PREFLOP_PHASE:
    #         self.goto_flop()
    #     elif self.stage == self.FLOP_PHASE:
    #         self.goto_turnriver()
    #     elif self.stage == self.TR_PHASE:
    #         self.player_folded = True
    #         self.pev(MyEvTypes.RienNeVaPlus)
