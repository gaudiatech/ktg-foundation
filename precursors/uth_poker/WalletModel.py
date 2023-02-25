"""
Distribution de gains:

--------------------------
the "Ante", et "Play" bets
--------------------------
On double Play en cas de victoire (toujours), On double Ante,
sauf si Ante a été "push" au préalable

"""
import common

kengi = common.kengi
MyEvTypes = common.MyEvTypes


class WalletModel(kengi.Emitter):
    """
    This class handles (in the model) everything that’s related to money.

    What events are used?
     - MoneyUpdate
     - ChipUpdate
    """

    def __init__(self, wealth):
        super().__init__()
        self._wealth = wealth
        self.prev_victorious = 0
        self.prev_total_bet = None

        # this value can be chosen by the player. Ideally this should be measured in CR,
        # as soon as the Uth game is active within the Ktg system
        self.__curr_chip_val = 2

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
        self.pev(MyEvTypes.ChipUpdate, value=self.__curr_chip_val)

    def can_stack(self, trips=False):
        if trips:
            return self.__curr_chip_val <= self._wealth
        else:
            if (self._wealth - 2 * self.__curr_chip_val) < 0:
                return False
            return True

    def stack_chip(self, trips=False):
        if trips:
            self.bets['trips'] += self.__curr_chip_val
            self.delta_wealth = self.__curr_chip_val
        else:
            self.bets['ante'] += self.__curr_chip_val
            self.bets['blind'] += self.__curr_chip_val
            self.delta_wealth = 2 * self.__curr_chip_val

        self._wealth -= self.delta_wealth
        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    def reset_bets(self, collect_mode=0):
        if collect_mode == 0:
            pass
        elif collect_mode == 1:
            clawback = self.bets['ante'] + self.bets['trips']
            self._wealth += clawback
        elif collect_mode == 2:
            clawback = self.bets['ante'] + self.bets['trips'] + self.bets['trips']
            self._wealth += clawback

        for bslot in self.bets.keys():
            self.bets[bslot] = 0

        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    # def reset(self):
    #     for bslot in self.bets.keys():
    #         self.bets[bslot] = 0

    def select_trips(self, val):
        self.bets['trips'] = val
        self.pev(MyEvTypes.BetUpdate)

    @property
    def all_infos(self):
        return self.bets['trips'], self.bets['ante'], self.bets['blind'], self.bets['play']

    def get_balance(self):
        return self._wealth

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

    def resolve(self, pl_vhand, dealer_vhand):
        """
        en fin de partie on peut appeler cette fonction qui va determiner quelle suite à donner
        (l’impact sur l’argent du joueur)
        de la fin de partie ...

        Algo pseudo-code:
        * si égalité, les mises restent aux joueurs sans gain ni perte
        (cas particulier pour le Bonus, voir ci-dessous)

        * si Dealer vhand > Player vhand
        alors dealer recupere tt les mises des cases « Mise (Ante) »,« Blinde »,  et « Play »

        * Si Player vhand > Dealer vhand
        alors player récupère l’intégralité de ses mises de départ
        + ses enjeux seront récompensés en fct du tableau de paiement indiqué +haut
        """
        player_sc, dealer_sc = pl_vhand.value, dealer_vhand.value

        self.prev_total_bet = sum(tuple(self.bets.values()))
        self.prev_victorious = 0
        if player_sc < dealer_sc:
            return -1

        self.prev_victorious = 1
        if player_sc == dealer_sc:
            # give back bets
            self.prev_earnings = sum(tuple(self.bets.values()))
            return 0

        # gere money aussi
        winner_vhand = pl_vhand
        earnings = self.bets.copy()
        a = earnings['play']
        earnings['play'] += a
        b = earnings['ante']
        earnings['ante'] += b

        earnings['blind'] = c = WalletModel.comp_blind_payout(self.bets['blind'], winner_vhand)

        d = WalletModel.comp_trips_payout(self.bets['trips'], winner_vhand)
        earnings['trips'] = d

        self.prev_earnings = sum(tuple(earnings.values()))
        self.prev_gain = sum((a, b, c, d))
        return 1

    def impact_fold(self):
        """
        dealers does not qualify if dealer's hand is less than a pair!
        when this happens, the ante bet is "pushed"
        """
        # if not dealer_qualifies:
        #     self._wealth += self.bets['ante']
        self.prev_total_bet = sum(tuple(self.bets.values()))
        self.prev_victorious = 0

        self.reset_bets(0)
        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    def collect_case_victory(self):
        if self.prev_victorious:
            self._wealth += self.prev_earnings
            self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    @staticmethod
    def comp_trips_payout(x, winning_vhand):
        """
        the "Trips" bet
        ---------------
        Royal Flush/Quinte Royale   -> 50:1
        Straight Flush/Quinte       -> 40:1
        Four of a kind/Carré        -> 30:1
        Full/Main pleine            -> 8:1
        Flush/Couleur               -> 7:1
        Straight/Suite              -> 4:1
        Three of a kind/Brelan      -> 3:1
        :return: y
        """
        y = 0
        if winning_vhand.is_royal():
            y += 50 * x
        elif winning_vhand.is_straight() and winning_vhand.is_flush():  # straight Flush
            y += 40 * x
        elif winning_vhand.is_four_oak():
            y += 30 * x
        elif winning_vhand.is_full():
            y += 8 * x
        elif winning_vhand.is_flush():
            y += 7 * x
        elif winning_vhand.is_straight():
            y += 4 * x
        elif winning_vhand.is_trips():
            y += 3 * x
        return y

    @staticmethod
    def comp_blind_payout(x, winning_vhand):
        """
        ---------------the "Blind" bet---------------
        Royal Flush/Quinte Royale   -> 500:1
        Straight Flush/Quinte       -> 50:1
        Four of a kind/Carré        -> 10:1
        Full/Main pleine            -> 3:1 (x3)
        Flush/Couleur               -> 3:2 (x1.5)
        Straight/Suite              -> 1:1
        """
        if winning_vhand.is_royal():
            return 500 * x
        # straight Flush detection
        if winning_vhand.is_straight() and winning_vhand.is_flush():
            return 50 * x
        if winning_vhand.is_four_oak():
            return 10 * x
        if winning_vhand.is_full():
            return 3 * x
        if winning_vhand.is_flush():
            return int(1.5 * x)
        if winning_vhand.is_straight():
            return x
        return 0

    def is_player_broke(self):
        """
        useful method because someone may want to call .pev(EngineEvTypes.GAMEENDS) when player's broke
        :return: True/False
        """
        return self._wealth <= 0
