import katagames_sdk as katasdk
katasdk.bootstrap()


kengi = katasdk.kengi
find_best_ph = kengi.tabletop.find_best_ph
Card = kengi.tabletop.StandardCard
CardDeck = kengi.tabletop.CardDeck
PokerHand = kengi.tabletop.PokerHand
StandardCard = kengi.tabletop.StandardCard

MyEvTypes = kengi.game_events_enum((
    'CashChanges',  # contains int "value"
    'StageChanges',
    'EndRoundRequested',
    'Victory',  # contains: amount
    'Tie',
    'Defeat'  # contains: loss
))

WARP_BACK = [2, 'niobepolis']
BACKGROUND_IMG_PATH = 'user_assets/pokerbackground3.png'
CARD_SIZE_PX = (69, 101)
CHIP_SIZE_PX = (40, 40)
OFFSET_CASH = (-48, -24)
CARD_SLOTS_POS = {  # coords in pixel -> where to place cards/chips
    'dealer1': (140, 48),
    'dealer2': (140 + 40, 48),
    'player1': (140, 206),
    'player2': (140 + 40, 206),
    'flop3': (238 - 40 * 2, 115),
    'flop2': (238 - 40 * 1, 115),
    'flop1': (238, 115),
    'river': (110 - 40, 115),
    'turn': (110, 115),
    'ante': (935 / 3, 757 / 3),
    'bet': (935 / 3, 850 / 3),
    'blind': (1040 / 3, 757 / 3),
    'raise1': (955 / 3, 870 / 3),
    'raise2': (961 / 3, 871 / 3),
    'raise3': (967 / 3, 872 / 3),
    'raise4': (973 / 3, 873 / 3),
    'raise5': (980 / 3, 875 / 3),
    'raise6': (986 / 3, 876 / 3)
}
PLAYER_CHIPS = {
    '2a': (825 / 2, 1000 / 2),
    '2b': (905 / 2, 1000 / 2),
    '5': (985 / 2, 1000 / 2),
    '10': (1065 / 2, 1000 / 2),
    '20': (1145 / 2, 1000 / 2)
}


class MoneyInfo(kengi.Emitter):
    """
    created a 2nd class (model) so it will be easier to manage
    earning & loosing

    earning := prize due to "Ante" + prize due to "Bet" + prize due to "Blind"
    right now this class isnt used, but it should become active

    ------
    * Si le Croupier a la meilleure combinaison, il recupere tt les mises des cases « Blinde »,
    « Mise (Ante) » et « Jouer » (cas particulier pour le Bonus, voir ci-dessous)

    * en cas d’égalité, les mises restent aux joueurs sans gain ni perte
    (cas particulier pour le Bonus, voir ci-dessous)

    * Si un joueur a une meilleure combinaison que le Croupier,
    il récupère l’intégralité de ses mises de départ et ses enjeux seront payés en fct du tableau de paiement...
    Présent dans .compute_blind_multiplier
    """

    def __init__(self, init_amount=200):
        super().__init__()
        self._cash = init_amount  # starting cash
        # TODO complete the implem & use this class!
        self.ante = self.blind = self.playcost = 0
        self._latest_bfactor = None
        self.recorded_outcome = None  # -1 loss, 0 tie, 1 victory
        self.recorded_prize = 0

    def get_cash_amount(self):
        return self._cash

    def init_play(self, value):
        self.ante = self.blind = value
        self._cash -= 2 * value
        self.pev(MyEvTypes.CashChanges, value=self._cash)

    def bet(self, bet_factor):
        self.playcost = bet_factor * self.ante
        self._cash -= self.playcost
        self.pev(MyEvTypes.CashChanges, value=self._cash)
        self._latest_bfactor = bet_factor

    def update_money_info(self):
        if self.recorded_outcome == 1:
            self._cash += self.recorded_prize
        if self.recorded_outcome > -1:
            self._cash += self.ante + self.blind + self.playcost  # recup toutes les mises

        self.ante = self.blind = self.playcost = 0  # reset play
        self.pev(MyEvTypes.CashChanges, value=self._cash)

    @property
    def is_player_broke(self):
        return self._cash <= 0
        # useful method because someone may want to call .pev(EngineEvTypes.GAMEENDS) when player's broke

    # ---------------------
    #  the 4 methods below compute future gain/loss
    #  but without applying it
    # ---------------------
    @staticmethod
    def compute_blind_multiplier(givenhand):
        # calcul gain spécifique & relatif à la blinde
        # -------------------------------------------
        # Royal flush- 500 pour 1
        # Straigth flush- 50 pour 1
        # Four of a kind - 10 pour 1
        # Full house - 3 pour 1
        # Flush - 1.5 pour 1
        # Suite - 1 pour 1
        # autres mains y a pas eu victore mais simple égalité!
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

    def announce_victory(self, winning_hand):
        prize = self.ante + self.playcost  # la banque paye à égalité sur ante & playcost
        blind_multiplier = MoneyInfo.compute_blind_multiplier(winning_hand)
        prize += blind_multiplier * self.blind
        self.recorded_prize = prize
        self.recorded_outcome = 1
        self.pev(MyEvTypes.Victory, amount=prize)

    def announce_tie(self):
        self.recorded_outcome = 0
        self.pev(MyEvTypes.Tie)

    def announce_defeat(self):
        self.recorded_outcome = -1
        self.pev(MyEvTypes.Defeat, loss=-1 * (self.ante + self.blind + self.playcost))


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

    INIT_ST_CODE, DISCOV_ST_CODE, FLOP_ST_CODE, TR_ST_CODE, OUTCOME_ST_CODE, WAIT_STATE = range(1, 6 + 1)

    def __init__(self):
        super().__init__()
        self.wallet = MoneyInfo()
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

        self.folded = False
        self.autoplay_flag = False
        self.dealer_vhand = self.player_vhand = None

        # stored lists of cards
        self.dealer_hand = []
        self.player_hand = []
        self.flop_cards = []
        self.turnriver_cards = []
        self._stage = None
        self.set_stage(self.INIT_ST_CODE)

    @property
    def stage(self):
        return self._stage

    @property
    def cash(self):
        return self.wallet.get_cash_amount()

    @property
    def money_info(self):
        return [
            (self.wallet.ante, 'ante'),
            (self.wallet.blind, 'blind'),
            (self.wallet.playcost, 'bet')
        ]

    def evolve_state(self):  # state transitions
        if self.DISCOV_ST_CODE == self.stage:
            self.go_flop()
        elif self.FLOP_ST_CODE == self.stage:
            self.go_tr_state()
        elif self.TR_ST_CODE == self.stage:
            self.go_outcome_state()
        elif self.OUTCOME_ST_CODE == self.stage:
            self.go_wait_state()

    def set_stage(self, sid):
        assert 1 <= sid <= 6
        self._stage = sid
        print(f' --new state-- >>> {sid}')
        self.pev(MyEvTypes.StageChanges)

    def go_discov(self, ante_val):
        if self.stage != UthModel.INIT_ST_CODE:
            raise ValueError('calling deal_cards while model isnt in the initial state')
        self.revealed['player2'] = self.revealed['player1'] = True
        # TODO should be deck.draw_cards(2) or smth
        self.dealer_hand.extend(self.deck.deal(2))
        self.player_hand.extend(self.deck.deal(2))
        self.wallet.init_play(ante_val)
        self.set_stage(self.DISCOV_ST_CODE)

    def go_flop(self):
        for k in range(1, 3 + 1):
            self.revealed[f'flop{k}'] = True
        self.flop_cards.extend(self.deck.deal(3))
        self.set_stage(self.FLOP_ST_CODE)

    def go_tr_state(self):
        # betting => betx2, or check
        self.turnriver_cards.extend(self.deck.deal(2))
        self.revealed['turn'] = self.revealed['river'] = True
        self.set_stage(self.TR_ST_CODE)

    def describe_pl_hand(self):
        return self.player_vhand.description

    def describe_dealers_hand(self):
        return self.dealer_vhand.description

    def go_outcome_state(self):
        self.set_stage(self.OUTCOME_ST_CODE)

    def go_wait_state(self):
        # state dedicated to blit the type of hand (Two pair, Full house etc) + the outcome
        self.autoplay_flag = False

        if self.folded:
            self.wallet.announce_defeat()
            self.revealed['dealer1'] = self.revealed['dealer2'] = False
        else:  # vhand means virtual hand (contains 7 cards and the program should find the best possible 5-card hand)
            self.dealer_vhand = find_best_ph(self.dealer_hand + self.flop_cards + self.turnriver_cards)
            self.player_vhand = find_best_ph(self.player_hand + self.flop_cards + self.turnriver_cards)
            dealrscore = self.dealer_vhand.value
            playrscore = self.player_vhand.value
            if dealrscore > playrscore:
                self.wallet.announce_defeat()
            elif dealrscore == playrscore:
                self.wallet.announce_tie()
            else:
                self.wallet.announce_victory(self.player_vhand)
            self.revealed['dealer1'] = self.revealed['dealer2'] = True
        self.set_stage(self.WAIT_STATE)

    def new_round(self):
        self.wallet.update_money_info()
        self.deck.reset()
        self.folded = False
        for lname in self.revealed.keys():
            self.revealed[lname] = False
        del self.dealer_hand[:]
        del self.player_hand[:]
        del self.flop_cards[:]
        del self.turnriver_cards[:]
        self.set_stage(self.INIT_ST_CODE)

    def input_bet(self, small_or_big):
        """
        :param small_or_big: accepted values: 0 or 1
        """
        bullish_choice = small_or_big + 1
        if self.stage == self.INIT_ST_CODE:
            self.go_discov(4)  # 4 is the arbitrary val chosen for 'Ante', need to pick a val that can be
            # paid via chips available on the virtual game table. value 5 would'nt work!
        else:
            if self.stage == self.DISCOV_ST_CODE:
                if bullish_choice == 1:
                    self.wallet.bet(3)
                else:
                    self.wallet.bet(4)
            elif self.stage == self.FLOP_ST_CODE:
                self.wallet.bet(2)
            elif self.stage == self.TR_ST_CODE:
                self.wallet.bet(1)
            self.pev(MyEvTypes.EndRoundRequested, folded=False)

    def input_check(self):
        if self.stage == self.DISCOV_ST_CODE:
            self.go_flop()

        elif self.stage == self.FLOP_ST_CODE:
            self.go_tr_state()

        elif self.stage == self.TR_ST_CODE:
            self.folded = True
            self.pev(MyEvTypes.EndRoundRequested)

        elif self.stage == self.WAIT_STATE:
            self.new_round()


class UthView(kengi.EvListener):
    TEXTCOLOR = kengi.pal.punk['flashypink']  # (5, 58, 7)
    BG_TEXTCOLOR = (92, 92, 100)
    ASK_SELECTION_MSG = 'SELECT ONE OPTION: '

    def __init__(self, model):
        super().__init__()
        self.bg = None
        self._my_assets = dict()
        self.chip_spr = dict()
        self._assets_rdy = False
        self._mod = model
        self.small_ft = kengi.pygame.font.Font(None, 24)
        self.info_msg0 = None
        self.info_msg1 = None  # will be used to tell the player what he/she has to do!
        self.info_msg2 = None

        self.cash_etq = None
        self.on_cash_changes(None, fvalue=self._mod.cash)
        self.scrsize = kengi.get_surface().get_size()

    def _load_assets(self):
        self.bg = kengi.pygame.image.load(BACKGROUND_IMG_PATH)
        spr_sheet = kengi.gfx.JsonBasedSprSheet('user_assets/pxart-french-cards')
        self._my_assets['card_back'] = spr_sheet[
            'back-blue.png']  # pygame.transform.scale(spr_sheet['back-of-card.png'], CARD_SIZE_PX)
        for card_cod in StandardCard.all_card_codes():
            y = PokerHand.adhoc_mapping(card_cod[0]).lstrip('0') + card_cod[1].upper()  # convert card code to path
            self._my_assets[card_cod] = spr_sheet[
                f'{y}.png']  # pygame.transform.scale(spr_sheet[f'{y}.png'], CARD_SIZE_PX)
        spr_sheet2 = kengi.gfx.JsonBasedSprSheet('user_assets/pokerchips')
        for chip_val_info in ('2a', '2b', '5', '10', '20'):
            y = {
                '2a': 'chip02.png',
                '2b': 'chip02.png',
                '5': 'chip05.png',
                '10': 'chip10.png',
                '20': 'chip20.png'
            }[chip_val_info]  # adapt filename
            tempimg = spr_sheet2[y]  # pygame.transform.scale(spr_sheet2[y], CHIP_SIZE_PX)
            # tempimg.set_colorkey((255, 0, 255))
            spr = kengi.pygame.sprite.Sprite()
            spr.image = tempimg
            spr.rect = spr.image.get_rect()
            spr.rect.center = PLAYER_CHIPS[chip_val_info]
            self.chip_spr['2' if chip_val_info in ('2a', '2b') else chip_val_info] = spr
        self._assets_rdy = True

    def on_paint(self, ev):
        if not self._assets_rdy:
            self._load_assets()
        self._paint(ev.screen)

    def on_stage_changes(self, ev):
        if self._mod.stage == UthModel.INIT_ST_CODE:
            self.info_msg0 = self.small_ft.render('Press ENTER to begin', False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
            self.info_msg1 = None
            self.info_msg2 = None
        else:
            msg = None
            if self._mod.stage == UthModel.DISCOV_ST_CODE:
                msg = ' CHECK, BET x3, BET x4'
            elif self._mod.stage == UthModel.FLOP_ST_CODE and (not self._mod.autoplay_flag):
                msg = ' CHECK, BET x2'
            elif self._mod.stage == UthModel.TR_ST_CODE and (not self._mod.autoplay_flag):
                msg = ' FOLD, BET x1'
            if msg:
                self.info_msg0 = self.small_ft.render(self.ASK_SELECTION_MSG, False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
                self.info_msg1 = self.small_ft.render(msg, False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
            # TODO display the amount lost

    def on_cash_changes(self, ev, fvalue=None):  # RE-draw cash value
        x = ev.value if (fvalue is None) else fvalue
        self.cash_etq = self.small_ft.render(f'%d$ ' % x, False, self.TEXTCOLOR)

    def on_victory(self, ev):
        result = ev.amount
        infoh_player = self._mod.player_vhand.description
        infoh_dealer = self._mod.dealer_vhand.description
        msg = f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {result}$"
        self.info_msg0 = self.small_ft.render('Victory!', False, self.TEXTCOLOR)
        self.info_msg1 = self.small_ft.render(msg, False, self.TEXTCOLOR)
        self.info_msg2 = self.small_ft.render('BACKSPACE to restart', False, self.TEXTCOLOR)

    def on_tie(self, ev):
        self.info_msg0 = self.small_ft.render('Its a Tie.', True, self.TEXTCOLOR)
        infoh_player = self._mod.player_vhand.description
        infoh_dealer = self._mod.dealer_vhand.description
        self.info_msg1 = self.small_ft.render(
            f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {0}$",
            True, self.TEXTCOLOR
        )
        self.info_msg2 = self.small_ft.render('BACKSPACE to restart', False, self.TEXTCOLOR)

    def on_defeat(self, ev):
        if self._mod.folded:
            msg = 'Player folded.'
        else:
            msg = 'Defeat.'
        self.info_msg0 = self.small_ft.render(msg, True, self.TEXTCOLOR)
        result = ev.loss
        if self._mod.folded:
            self.info_msg1 = self.small_ft.render(f"You lost {result}$", False, self.TEXTCOLOR)
        else:
            infoh_dealer = self._mod.dealer_vhand.description
            infoh_player = self._mod.player_vhand.description
            self.info_msg1 = self.small_ft.render(
                f"Player: {infoh_player}; Dealer: {infoh_dealer}; You've lost {result}$", False, self.TEXTCOLOR
            )
        self.info_msg2 = self.small_ft.render('BACKSPACE to restart', False, self.TEXTCOLOR)

    @staticmethod
    def centerblit(refscr, surf, p):
        w, h = surf.get_size()
        refscr.blit(surf, (p[0] - w // 2, p[1] - h // 2))

    def _paint(self, refscr):
        refscr.blit(self.bg, (0, 0))
        cardback = self._my_assets['card_back']

        # ---------- draw visible or hidden cards ---------
        if self._mod.stage == UthModel.INIT_ST_CODE:
            # draw hidden cards' back, at adhoc location
            for loc in ('dealer1', 'dealer2', 'player1', 'player2'):
                UthView.centerblit(refscr, cardback, CARD_SLOTS_POS[loc])

        if self._mod.stage >= UthModel.DISCOV_ST_CODE:  # cards revealed
            # draw hidden cards' back, at adhoc location
            for k in range(1, 3 + 1):
                UthView.centerblit(refscr, cardback, CARD_SLOTS_POS['flop' + str(k)])

            for loc in ('dealer1', 'dealer2'):
                UthView.centerblit(refscr, cardback, CARD_SLOTS_POS[loc])
            for k, c in enumerate(self._mod.player_hand):
                slotname = 'player' + str(k + 1)
                UthView.centerblit(refscr, self._my_assets[c.code], CARD_SLOTS_POS[slotname])

        if self._mod.stage >= UthModel.FLOP_ST_CODE:
            # draw hidden cards' back, at adhoc location
            for loc in ('turn', 'river'):
                UthView.centerblit(refscr, cardback, CARD_SLOTS_POS[loc])
            for k, c in enumerate(self._mod.flop_cards):
                slotname = 'flop' + str(k + 1)
                UthView.centerblit(refscr, self._my_assets[c.code], CARD_SLOTS_POS[slotname])

        if self._mod.stage >= UthModel.TR_ST_CODE:
            UthView.centerblit(refscr, self._my_assets[self._mod.turnriver_cards[0].code], CARD_SLOTS_POS['turn'])
            UthView.centerblit(refscr, self._my_assets[self._mod.turnriver_cards[1].code], CARD_SLOTS_POS['river'])

        if self._mod.revealed['dealer1'] and self._mod.revealed['dealer2']:
            # show what the dealer has
            UthView.centerblit(refscr, self._my_assets[self._mod.dealer_hand[0].code], CARD_SLOTS_POS['dealer1'])
            UthView.centerblit(refscr, self._my_assets[self._mod.dealer_hand[1].code], CARD_SLOTS_POS['dealer2'])

        # -- draw amounts for ante, blind and the bet
        for info_e in self._mod.money_info:
            x, name = info_e
            lbl_surf = self.small_ft.render(f'{x}', True, self.TEXTCOLOR, self.BG_TEXTCOLOR)
            refscr.blit(lbl_surf, CARD_SLOTS_POS[name])

        # -- draw chips & the total cash amount
        for k, v in enumerate((2, 5, 10, 20)):
            adhoc_spr = self.chip_spr[str(v)]
            if v == 2:
                adhoc_spr.rect.center = PLAYER_CHIPS['2b']
            refscr.blit(adhoc_spr.image, adhoc_spr.rect.topleft)
        self.chip_spr['2'].rect.center = PLAYER_CHIPS['2a']
        refscr.blit(self.chip_spr['2'].image, self.chip_spr['2'].rect.topleft)
        refscr.blit(self.cash_etq, (self.scrsize[0]+OFFSET_CASH[0], self.scrsize[1]+OFFSET_CASH[1]))

        # -- display all 3 prompt messages
        for rank, e in enumerate((self.info_msg0, self.info_msg1, self.info_msg2)):
            if e is not None:
                refscr.blit(e, (24, 10 + 50 * rank))


class UthCtrl(kengi.EvListener):
    AUTOPLAY_DELAY = 0.8  # sec

    def __init__(self, model, refgame):
        super().__init__()
        self._mod = model
        self._last_t = None
        self.elapsed = 0
        self.recent_date = None
        self.refgame = refgame

    def on_keydown(self, ev):
        if ev.key == kengi.pygame.K_ESCAPE:
            self.refgame.gameover = True

        elif not self._mod.autoplay_flag:
            # backspace will be used to CHECK / FOLD
            if ev.key == kengi.pygame.K_BACKSPACE:
                self._mod.input_check()
            # enter will be used to select the regular BET option, x3, x2 or x1 depends on the stage
            elif ev.key == kengi.pygame.K_RETURN:
                self._mod.input_bet(0)
            # case: at the beginning of the game the player can select the MEGA-BET x4 lets use space for that
            # we'll also use space to begin the game. State transition: init -> discov
            elif ev.key == kengi.pygame.K_SPACE:
                if self._mod.stage != UthModel.INIT_ST_CODE:
                    if self._mod.stage == UthModel.DISCOV_ST_CODE:
                        self._mod.input_bet(1)

    def on_update(self, ev):
        self.recent_date = ev.curr_t
        if self._mod.autoplay_flag:
            elapsed = ev.curr_t - self._last_t
            if elapsed > self.AUTOPLAY_DELAY:
                self._mod.evolve_state()
                self._last_t = ev.curr_t

    def on_end_round_requested(self, ev):
        self._mod.autoplay_flag = True
        self._mod.evolve_state()
        self._last_t = self.recent_date


class PokerUth(kengi.GameTpl):

    def __init__(self):
        self._manager = None
        super().__init__()
        self.m = None
        self.evli_li = list()

    def enter(self, vms):
        kengi.init(3)
        self._manager = kengi.get_ev_manager()
        self._manager.setup(MyEvTypes)
        self.m = UthModel()
        for e in (
            UthView(self.m),
            UthCtrl(self.m, self)
        ):
            e.turn_on()

    def update(self, infot):
        super().update(infot)
        if self.gameover:
            return WARP_BACK


game_obj = PokerUth()
katasdk.gkart_activation(game_obj)


# -----------------
# local ctx run
# -----------------
import time


if __name__ == '__main__':
    game_obj.enter(None)

    while not game_obj.gameover:
        tmp = game_obj.update(time.time() )
        if tmp and tmp[0] == 2:
            game_obj.gameover = True
    game_obj.exit(None)
    print('sortie clean')
