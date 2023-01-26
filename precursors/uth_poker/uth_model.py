import common
from WalletModel import WalletModel


kengi = common.kengi
find_best_ph = kengi.tabletop.find_best_ph
CardDeck = kengi.tabletop.CardDeck
MyEvTypes = common.MyEvTypes

PokerStates = kengi.struct.enum(
    'AnteSelection',
    'PreFlop',
    'Flop',
    'TurnRiver',
    'Outcome'
)


# -----------------------------------------------------
class UthModel(kengi.Emitter):
    """
    Uth: Ultimate Texas Holdem
    this is a model class, it handles "poker states" (mostly)
    """

    def __init__(self):
        super().__init__()
        self.wallet = WalletModel(250)  # TODO link with CR and use the real wealth value

        self.bet_done = False
        self.player_folded = False

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
        self.goto_next_state()

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
        if newstate == PokerStates.PreFlop:
            print('hi im in preflop')
            self.possible_bet_factor = [3, 4]
            # cards have been dealt !
            self.wallet.ready_to_start = True
            self.visibility['player2'] = self.visibility['player1'] = True
            # TODO should be deck.draw_cards(2) or smth
            self.dealer_hand.extend(self.deck.deal(2))
            self.player_hand.extend(self.deck.deal(2))
            self.wallet.start_match()

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
            print('-- -- -in outcome state')
            self.possible_bet_factor = None
            self.visibility['dealer1'] = self.visibility['dealer2'] = True

            # state dedicated to blit the type of hand (Two pair, Full house etc) + the outcome
            if self.player_folded:
                self.wallet.tag_defeat(True)  # TODO ability to push the ante bet
            else:
                self.dealer_vhand = find_best_ph(self.dealer_hand + self.flop_cards + self.turnriver_cards)
                self.player_vhand = find_best_ph(self.player_hand + self.flop_cards + self.turnriver_cards)
                dealrscore = self.dealer_vhand.value
                playrscore = self.player_vhand.value
                if dealrscore == playrscore:
                    self.wallet.announce_tie()  # TODO gere égalité correctement
                elif dealrscore > playrscore:
                    self.wallet.tag_defeat(True)
                else:  # victory
                    self.wallet.pay_for_victory(self.player_vhand)

            self.visibility['dealer1'] = self.visibility['dealer2'] = True

    def goto_next_state(self):
        """
        iterate the game (pure game logic)
        """
        tr_table = {
            None: PokerStates.AnteSelection,
            PokerStates.AnteSelection: PokerStates.PreFlop,
            PokerStates.PreFlop: PokerStates.Flop,
            PokerStates.Flop: PokerStates.TurnRiver,
            PokerStates.TurnRiver: PokerStates.Outcome,
        }
        self._pokerstate = tr_table[self._pokerstate]
        self._proc_state(self._pokerstate)  # what actions are needed to update the model?
        self.pev(MyEvTypes.StateChanges, pokerstate=self._pokerstate)

        # if self.PREFLOP_PHASE == self.stage:
        #     self.goto_flop()
        # elif self.FLOP_PHASE == self.stage:
        #     self.goto_turnriver()
        # elif self.TR_PHASE == self.stage:
        #     self.goto_outcome()
        # elif self.OUTCOME_ST_CODE == self.stage:
        #     self.go_wait_state()

    # def set_stage(self, sid):
    #     assert 0 < sid <= 7
    #     self.stage = sid
    #     print(f' --new state-- >>> {sid}')
    #     self.pev(common.MyEvTypes.StageChanges)

    @property
    def pl_hand_description(self):
        return self.player_vhand.description

    @property
    def dl_hand_description(self):
        return self.dealer_vhand.description

    def new_round(self):
        # self.wallet.update_money_info()
        self.wallet.start_match()
        self.deck.reset()
        self.folded = False
        for lname in self.visibility.keys():
            self.visibility[lname] = False
        del self.dealer_hand[:]
        del self.player_hand[:]
        del self.flop_cards[:]
        del self.turnriver_cards[:]
        self.set_stage(self.BET0_PHASE)

    def select_bet(self, bullish_choice=False):
        if bullish_choice and self._pokerstate != PokerStates.PreFlop:
            raise RuntimeError('non valid bullish_choice argument detected!')
        b_factor = self.possible_bet_factor[0]
        if bullish_choice:
            b_factor = self.possible_bet_factor[1]

        self.wallet.bet(b_factor)
        self.goto_next_state()

        # if self.stage == self.SETANTE_PHASE:
        #     self.deal_pl_cards()
        # elif self.stage == self.OUTCOME_PHASE:
        #     self.new_round()
        # else:
        #     if self.stage == self.BET0_PHASE:
        #         if bullish_choice == 1:
        #             self.wallet.bet(3)
        #         else:
        #             self.wallet.bet(4)
        #     elif self.stage == self.FLOP_PHASE:
        #         self.wallet.bet(2)
        #     elif self.stage == self.TR_PHASE:
        #         self.wallet.bet(1)
        #     self.pev(MyEvTypes.EndRoundRequested, folded=False)

    def select_check(self):
        if self.stage == self.PREFLOP_PHASE:
            self.goto_flop()
        elif self.stage == self.FLOP_PHASE:
            self.goto_turnriver()
        elif self.stage == self.TR_PHASE:
            self.player_folded = True
            self.pev(MyEvTypes.EndRoundRequested, folded=True)
