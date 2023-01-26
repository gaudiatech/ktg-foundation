"""
Distribution de gains:

--------------------------
the "Ante", et "Play" bets
--------------------------
On double Play en cas de victoire (toujours), On double Ante,
sauf si Ante a été "push" au préalable

---------------
the "Blind" bet
---------------
Royal Flush/Quinte Royale   -> 500:1
Straight Flush/Quinte       -> 50:1
Four of a kind/Carré        -> 10:1
Full/Main pleine            -> 3:1 (x3)
Flush/Couleur               -> 3:2 (x1.5)
Straight/Suite              -> 1:1

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
        print('wallet -> definition of chip val, it is now ...', newvalue)
        self.pev(MyEvTypes.ChipUpdate, value=self.__curr_chip_val)

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

    def reset(self):
        for bslot in self.bets.keys():
            self.bets[bslot] = 0

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

    def _reset_bets(self):
        for bslot in self.bets.keys():
            self.bets[bslot] = 0

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

        if player_sc == dealer_sc:
            result = 0
        elif player_sc > dealer_sc:
            result = 1
        else:
            result = -1

        # gere money aussi
        if result == 1:
            winner_vhand = pl_vhand
            earnings = self.bets.copy()
            earnings['play'] += earnings['play']
            earnings['ante'] += earnings['ante']
            earnings['blind'] += WalletModel.comp_blind_payout(self.bets['blind'], winner_vhand)
            earnings['trips'] = WalletModel.comp_trips_payout(self.bets['trips'], winner_vhand)
            reward = sum(tuple(earnings.values()))
            self.delta_wealth = reward
            self.prev_earnings = earnings
            self._wealth += self.delta_wealth
            self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

        return result

        #     self.wallet.announce_tie()
        #     self.result = 0
        # elif dealrscore > playrscore:
        #     self.wallet.tag_defeat(True)
        #     self.result = -1
        # else:  # victory
        #     self.wallet.pay_for_victory(self.player_vhand)
        #     self.result = 1

    def impact_fold(self):
        """
        dealers does not qualify if dealer's hand is less than a pair!
        when this happens, the ante bet is "pushed"
        """
        # if not dealer_qualifies:
        #     self._wealth += self.bets['ante']
        self._reset_bets()
        self.pev(MyEvTypes.MoneyUpdate, value=self._wealth)

    @staticmethod
    def comp_trips_payout(x, winning_vhand):
        return 0  # TODO fix

    @staticmethod
    def comp_blind_payout(x, winning_vhand):
        """
        Royal Flush/Quinte Royale   -> 500:1
        Straight Flush/Quinte       -> 50:1
        Four of a kind/Carré        -> 10:1
        Full/Main pleine            -> 3:1 (x3)
        Flush/Couleur               -> 3:2 (x1.5)
        Straight/Suite              -> 1:1

        :param x: represents the blind bet
        :param winning_vhand:
        :return: what should be earned
        """
        return x  # TODO fix

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
