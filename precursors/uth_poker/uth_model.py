"""
Comment les gains sont distribués?

---------------
the "Trips" bet
---------------
Royal Flush/Quinte Royale   -> 50:1
Straight Flush/Quinte       -> 40:1
Four of a kind/Carré        -> 30:1
Full/Main pleine            -> 8:1
Flush/Couleur               -> 7:1
Straight/Suite              -> 4:1
Three of a kind/Brelan      -> 3:1

---------------
the "Blind" bet
---------------
Royal Flush/Quinte Royale   -> 500:1
Straight Flush/Quinte       -> 50:1
Four of a kind/Carré        -> 10:1
Full/Main pleine            -> 3:1 (x3)
Flush/Couleur               -> 3:2 (x1.5)
Straight/Suite              -> 1:1

--------------------------
the "Ante", et "Play" bets
--------------------------
On double Play en cas de victoire (toujours),
On double Ante, sauf si Ante a été "push" au préalable
"""

import common


kengi = common.kengi
find_best_ph = kengi.tabletop.find_best_ph
CardDeck = kengi.tabletop.CardDeck
MyEvTypes = common.MyEvTypes


class WalletMod(kengi.Emitter):
    """
    * Si le Croupier a la meilleure combinaison,
    il recupere tt les mises des cases « Blinde »,
    « Mise (Ante) » et « Jouer » (cas particulier pour le Bonus, voir ci-dessous)

    * en cas d’égalité, les mises restent aux joueurs sans gain ni perte
    (cas particulier pour le Bonus, voir ci-dessous)

    * Si un joueur a une meilleure combinaison que le Croupier,
    il récupère l’intégralité de ses mises de départ et ses enjeux seront payés en fct du tableau de paiement...
    Présent dans .compute_blind_multiplier
    """

    def __init__(self, wealth):
        super().__init__()
        self._wealth = wealth

        # ideally this is chosen by the player
        self.__curr_chip_val = 2  # should be measured in CR, if this Uth game is loaded within the Ktg system

        # indique le dernier changement récent ds la richesse & repartition gains
        self.delta_wealth = 0
        self.prev_earnings = None

        # during the match
        self.bets = {
            'trips': 0,
            'ante': 0,
            'blind': 0,
            'play': 0
        }
        self.ready_to_start = False

    @property
    def curr_chipval(self):
        return self.__curr_chip_val

    @curr_chipval.setter
    def curr_chipval(self, newvalue):
        self.__curr_chip_val = newvalue
        print('wallet -> definition of chip val, it is now ...', newvalue)
        self.pev(MyEvTypes.ChipValueUpdate, value=self.__curr_chip_val)

    def stake_chip(self):
        self.bets['ante'] += self.__curr_chip_val
        self.bets['blind'] += self.__curr_chip_val
        self.delta_wealth = 2 * self.__curr_chip_val

        self._wealth -= self.delta_wealth

        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    def unstake_all(self):
        # equivalent a un reset de l'etat du bet, lors de la SETANTE_PHASE
        r = self.bets['ante'] + self.bets['blind'] + self.bets['trips']
        self._reset_bets()
        y = self._wealth
        self._wealth += r
        if y != self._wealth:
            self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    def select_trips(self, val):
        self.bets['trips'] = val
        self.pev(MyEvTypes.BetUpdate)

    def get_all_bets(self):
        return (
            self.bets['trips'], self.bets['ante'], self.bets['blind'], self.bets['play']
        )

    def get_balance(self):
        return self._wealth

    def start_match(self):
        if not self.ready_to_start:
            raise RuntimeError('cannot start match while chips are not staked!')
        # go to bet0 phase

    def bet(self, multiplier):
        """
        before the flop :   3x or 4x ante
        at the flop     :   2x ante
        at the turn&river:  1x ante
        """
        assert isinstance(multiplier, int) and 0 < multiplier < 5
        self.bets['play'] = multiplier * self.bets['ante']
        self._wealth -= self.bets['play']
        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    def _reset_bets(self):
        for bslot in self.bets.keys():
            self.bets[bslot] = 0

    def tag_defeat(self, dealer_qualifies=True):
        """
        dealers does not qualify if dealer's hand is less than a pair!
        when this happens, the ante bet is "pushed"
        """
        if not dealer_qualifies:
            self._wealth += self.bets['ante']
        self._reset_bets()
        print('event money update - wealth:', self._wealth)
        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    def tag_victory(self):
        earnings = self.bets.copy()

        earnings['play'] += earnings['play']
        earnings['ante'] += earnings['ante']

        earnings['blind'] += WalletMod.comp_blind_payout(self.bets['blind'])
        earnings['trips'] = WalletMod.comp_trips_payout(self.bets['trips'])

        reward = sum(tuple(earnings.values()))
        self.delta_wealth = reward
        self.prev_earnings = earnings
        self._wealth += self.delta_wealth
        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    # def win_impact(self):
    #     if self.recorded_outcome == 1:
    #         self._cash += self.recorded_prize
    #     if self.recorded_outcome > -1:
    #         self._cash += self.ante + self.blind + self.playcost  # recup toutes les mises
    #     self.ante = self.blind = self.play = 0  # reset play
    #     self.pev(MyEvTypes.MoneyUpdate, value=self._cash)

    def is_player_broke(self):
        """
        useful method because someone may want to call .pev(EngineEvTypes.GAMEENDS) when player's broke
        :return: True/False
        """
        return self._cash <= 0

    # ---------------------
    #  the 4 methods below compute future gain/loss
    #  but without applying it
    # ---------------------
    @staticmethod
    def compute_blind_multiplier(givenhand):
        """
        Calcul gain spécifique & relatif à la blinde
        Royal flush- 500 pour 1
        Straigth flush- 50 pour 1
        Four of a kind - 10 pour 1
        Full house - 3 pour 1
        Flush - 1.5 pour 1
        Suite - 1 pour 1
        """
        multiplicateur = {
            'High Card': 0,
            'One Pair': 0,
            'Two Pair': 0,
            'Three of a Kind': 0,
            'Straight': 1,
            'Flush': 1.5,
            'Full House': 3,
            'Four of a Kind': 10,
            'Straight Flush': 50
        }[givenhand.description]
        return multiplicateur

    def notify_outcome(self):
        if self.delta_wealth > 0:
            self.pev(MyEvTypes.Victory, amount=self.delta_wealth)
        elif self.delta_wealth == 0:
            self.pev(MyEvTypes.Tie)
        else:
            self.pev(MyEvTypes.Defeat, loss=-1 * (self.ante + self.blind + self.playcost))


# -----------------------------------------------------
class UthModel(kengi.Emitter):
    """
    Uth: Ultimate Texas Holdem
    STAGES ARE
    0: "eden state" -> cards not dealt, no money spent
    1: cards dealt yes, both ante and blind have been paid, you pick one option: check/bet 3x/ bet 4x
      if bet 4x you go straight to the last state
      if check you go to state 2
    2: flop revealed, your pick one option: check/bet 2x
      if bet 2x you go to the last state
      if check you go to state 3
    3: turn & river revealed you pick one option: fold/ bet 1x
      if bet you go to the final state
      if fold you loose everything except whats in bonus state 5
    4(final):
      all remaining cards are returned, if any then player is paid. Current round halts
    5:
      pay bonus only, current round halts
    """

    SETANTE_PHASE, BET0_PHASE, PREFLOP_PHASE, FLOP_PHASE, TR_PHASE, RESULTS_PHASE, OUTCOME_PHASE = range(1, 7+1)

    def __init__(self):
        super().__init__()
        self.wallet = WalletMod(250)  # TODO link with CR
        self.has_folded = False
        self.bet_done = False
        self.deck = CardDeck()
        self.revealed = {
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
        self.dealer_vhand = self.player_vhand = None  # temp attributes to save best virtual hand (5 out of 7)
        # stored lists of cards
        self.dealer_hand = []
        self.player_hand = []
        self.flop_cards = []
        self.turnriver_cards = []
        self.stage = self.SETANTE_PHASE

    def __getattr__(self, item):
        if hasattr(self.wallet, item):
            return getattr(self.wallet, item)
        raise AttributeError("'UthModel' object has no attribute '{}'".format(item))

    @property
    def chipvalue(self):
        return self.wallet.curr_chipval

    def set_curr_chipval(self, newv):
        self.wallet.curr_chipval = newv

    # @property
    # def cash(self):
    #     return self.wallet.balance
    #
    @property
    def money_info(self):
        return [
            (self.wallet.bets['ante'], 'ante'),
            (self.wallet.bets['blind'], 'blind'),
            (self.wallet.bets['play'], 'bet')
        ]

    def evolve_state(self):  # state transitions
        if self.PREFLOP_PHASE == self.stage:
            self.goto_flop()
        elif self.FLOP_PHASE == self.stage:
            self.goto_turnriver()
        elif self.TR_PHASE == self.stage:
            self.goto_outcome()
        # elif self.OUTCOME_ST_CODE == self.stage:
        #     self.go_wait_state()

    def set_stage(self, sid):
        assert 0 < sid <= 7
        self.stage = sid
        print(f' --new state-- >>> {sid}')
        self.pev(common.MyEvTypes.StageChanges)

    def deal_pl_cards(self):
        if self.stage != UthModel.SETANTE_PHASE:
            raise ValueError('calling deal_cards while model isnt in the initial state')
        self.wallet.ready_to_start = True
        self.revealed['player2'] = self.revealed['player1'] = True
        # TODO should be deck.draw_cards(2) or smth
        self.dealer_hand.extend(self.deck.deal(2))
        self.player_hand.extend(self.deck.deal(2))
        self.wallet.start_match()
        self.set_stage(self.PREFLOP_PHASE)

    def goto_flop(self):
        for k in range(1, 3 + 1):
            self.revealed[f'flop{k}'] = True
        self.flop_cards.extend(self.deck.deal(3))
        self.set_stage(self.FLOP_PHASE)

    def goto_turnriver(self):
        # betting => betx2, or check
        self.turnriver_cards.extend(self.deck.deal(2))
        self.revealed['turn'] = self.revealed['river'] = True
        self.set_stage(self.TR_PHASE)

    def goto_outcome(self):
        self.revealed['dealer1'] = self.revealed['dealer2'] = True
        self.set_stage(self.OUTCOME_PHASE)

        # state dedicated to blit the type of hand (Two pair, Full house etc) + the outcome
        self.autoplay_flag = False

        if not self.folded:
            self.dealer_vhand = find_best_ph(self.dealer_hand + self.flop_cards + self.turnriver_cards)
            self.player_vhand = find_best_ph(self.player_hand + self.flop_cards + self.turnriver_cards)
            dealrscore = self.dealer_vhand.value
            playrscore = self.player_vhand.value

        if self.folded or (dealrscore > playrscore):
            self.wallet.tag_defeat(True)  # TODO ability to push the ante bet

        elif dealrscore == playrscore:
            self.wallet.announce_tie()  # TODO gere égalité correctement
        else:
            self.wallet.tag_victory()  # self.player_vhand)

        self.revealed['dealer1'] = self.revealed['dealer2'] = True

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
        for lname in self.revealed.keys():
            self.revealed[lname] = False

        del self.dealer_hand[:]
        del self.player_hand[:]
        del self.flop_cards[:]
        del self.turnriver_cards[:]
        self.set_stage(self.BET0_PHASE)

    def select_bet(self, small_or_big):
        """
        :param small_or_big: accepted values: 0 or 1
        """
        bullish_choice = small_or_big + 1
        if self.stage == self.SETANTE_PHASE:
            # an arbitrary val MUST have been chosen for 'Ante' before we run this:
            self.deal_pl_cards()
        elif self.stage == self.OUTCOME_PHASE:
            self.new_round()
        else:
            if self.stage == self.BET0_PHASE:
                if bullish_choice == 1:
                    self.wallet.bet(3)
                else:
                    self.wallet.bet(4)
            elif self.stage == self.FLOP_PHASE:
                self.wallet.bet(2)
            elif self.stage == self.TR_PHASE:
                self.wallet.bet(1)
            self.pev(MyEvTypes.EndRoundRequested, folded=False)

    def select_check(self):
        if self.stage == self.PREFLOP_PHASE:
            self.goto_flop()
        elif self.stage == self.FLOP_PHASE:
            self.goto_turnriver()
        elif self.stage == self.TR_PHASE:
            self.has_folded = True
            self.pev(MyEvTypes.EndRoundRequested, folded=True)
