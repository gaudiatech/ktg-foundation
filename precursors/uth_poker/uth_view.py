import common
from uth_model import PokerStates


# aliases
kengi = common.kengi
pygame = kengi.pygame
MyEvTypes = common.MyEvTypes
Card = kengi.tabletop.StandardCard
PokerHand = kengi.tabletop.PokerHand
StandardCard = kengi.tabletop.StandardCard
wContainer = kengi.gui.WidgetContainer

# constants
CHIP_SIZE_PX = (33, 33)
BACKGROUND_IMG_PATH = 'user_assets/pokerbackground3.png'
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
}
MONEY_POS = {
    'ante': (45, 166),
    'blind': (90, 166),
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


class UthView(kengi.EvListener):
    TEXTCOLOR = kengi.pal.punk['flashypink']
    BG_TEXTCOLOR = (92, 92, 100)
    ASK_SELECTION_MSG = 'SELECT ONE OPTION: '

    def _init_money_labels(self):
        all_lbl = {
            'trips_etq': kengi.gui.Label((0, 0), 'hi bet=trips', 22),
            'ante_etq': kengi.gui.Label((0, 0), 'ante', 22),
            'blind_etq': kengi.gui.Label((0, 0), 'blind', 22),
            'cash_etq': kengi.gui.Label((0, 0), 'cash', 22)
        }
        return wContainer(
            (32, self.midpt[1]+66),
            (128, 128),
            wContainer.FLOW,
            all_lbl,
            spacing=2
        )

    def _build_chips_related_gui(self):
        # -----------------
        # --- cycle right button
        def cb0():
            kengi.get_ev_manager().post(MyEvTypes.ChipCycle, upwards=True)

        cycle_r_button = kengi.gui.Button2(None, '>', (133, 266), callback=cb0)

        # --- cycle left button
        def cb1():
            kengi.get_ev_manager().post(MyEvTypes.ChipCycle, upwards=False)

        cycle_l_button = kengi.gui.Button2(None, '<', (133 - 80, 266), callback=cb1)

        stake_button = kengi.gui.Button2(None, ' __+__ ', (133 - 40, 266), tevent=MyEvTypes.AddChips)
        # -----------------

        chip_related_buttons = [
            cycle_l_button,
            stake_button,
            cycle_r_button,
        ]

        targ_w = 140
        return wContainer(
            (self.midpt[0] - (targ_w// 2), self.midpt[1] + 132),
            (targ_w, 32),
            wContainer.EXPAND,
            chip_related_buttons, spacing=8
        )

    @staticmethod
    def _init_actions_related_gui():
        all_bt = [
            kengi.gui.Button2(None, 'Deal', (330, 128), tevent=MyEvTypes.MatchStart),
            kengi.gui.Button2(None, 'BetSame', (0, 11), tevent=MyEvTypes.BetSame),
            kengi.gui.Button2(None, 'Cancel', (0, 0), tevent=MyEvTypes.UndoBet),
            kengi.gui.Button2(None, 'Clear', (0, 0), tevent=MyEvTypes.ClearBet),
        ]
        return wContainer(
            (320, 244), (133, 250), wContainer.FLOW, all_bt, spacing=16
        )

    def __init__(self, model):
        super().__init__()
        self.bg = None
        self._my_assets = dict()

        self.chip_spr = dict()
        self.chip_adhoc_image = None

        self._assets_rdy = False
        self._mod = model
        self.small_ft = kengi.pygame.font.Font(None, 24)
        self.info_msg0 = None
        self.info_msg1 = None  # will be used to tell the player what he/she has to do!
        self.info_msg2 = None

        self.scrsize = kengi.get_surface().get_size()
        self.midpt = [self.scrsize[0] // 2, self.scrsize[1] // 2]

        self._chips_related_wcontainer = self._build_chips_related_gui()
        self._chips_related_wcontainer.set_debug_flag()  # pr affichage forcé

        self.chip_scr_pos = [
            self._chips_related_wcontainer.get_pos()[0] + 11,
            self._chips_related_wcontainer.get_pos()[1] - 25
        ]

        self._money_labels = self._init_money_labels()
        self._money_labels.set_debug_flag()
        self.on_money_update(None)  # force update

        self.act_deal_cards = None
        self.act_undo_stake = None
        self.act_bet_same = None
        self.act_clear_chips = None
        self._act_related_wcontainer = self._init_actions_related_gui()
        self._act_related_wcontainer.set_debug_flag()  # pr affichage forcé

    def turn_on(self):
        super().turn_on()
        for b in self._chips_related_wcontainer.content:
            b.turn_on()
        for b in self._act_related_wcontainer.content:
            b.turn_on()

    def turn_off(self):
        super().turn_off()
        for b in self._chips_related_wcontainer.content:
            b.turn_off()
        for b in self._act_related_wcontainer.content:
            b.turn_off()

    def on_chip_update(self, ev):
        print('[View] reception chipval update :::', ev.value)
        self.chip_adhoc_image = self.chip_spr[str(ev.value)].image

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

            # no chip rescaling:
            # tempimg = spr_sheet2[y]
            # chip rescaling:
            tempimg = pygame.transform.scale(spr_sheet2[y], CHIP_SIZE_PX)

            # tempimg.set_colorkey((255, 0, 255))
            spr = kengi.pygame.sprite.Sprite()
            spr.image = tempimg
            spr.rect = spr.image.get_rect()
            spr.rect.center = PLAYER_CHIPS[chip_val_info]
            self.chip_spr['2' if chip_val_info in ('2a', '2b') else chip_val_info] = spr

        self.chip_adhoc_image = self.chip_spr['2'].image

        self._assets_rdy = True

    def on_state_changes(self, ev):
        if self._mod.stage == PokerStates.AnteSelection:
            self.info_msg0 = self.small_ft.render('Press BACKSPACE to begin', False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
            self.info_msg1 = None
            self.info_msg2 = None
        else:
            msg = None
            if self._mod.stage == PokerStates.PreFlop:
                msg = ' CHECK, BET x3, BET x4'
            elif self._mod.stage == PokerStates.Flop:
                msg = ' CHECK, BET x2'
            elif self._mod.stage == PokerStates.TurnRiver:
                msg = ' FOLD, BET x1'
            if msg:
                self.info_msg0 = self.small_ft.render(self.ASK_SELECTION_MSG, False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
                self.info_msg1 = self.small_ft.render(msg, False, self.TEXTCOLOR, self.BG_TEXTCOLOR)
            # TODO display the amount lost

    def on_add_chips(self, ev):
        self._mod.wallet.stake_chip()

    def on_money_update(self, ev):  # , fvalue=None):  # RE-draw cash value
        self._refresh_money_labels()

    def on_new_match(self, ev):
        self._refresh_money_labels()

    def _refresh_money_labels(self):
        x = self._mod.get_balance()
        _, antev, blindv, _ = self._mod.get_all_bets()

        self._money_labels['ante_etq'].text = f'%d$ ' % antev
        self._money_labels['blind_etq'].text = f'%d$ ' % blindv
        self._money_labels['cash_etq'].text = f'%d$ ' % x

    def on_match_over(self, ev):
        self.info_msg2 = self.small_ft.render('click once to restart', False, self.TEXTCOLOR)

        if ev.won == 0:  # tie
            self.info_msg0 = self.small_ft.render('Its a Tie.', True, self.TEXTCOLOR)
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            self.info_msg1 = self.small_ft.render(
                f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {0}$",
                True, self.TEXTCOLOR
            )
        elif ev.won == 1:  # won indeed
            result = self._mod.quantify_reward()

            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            msg = f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {result}$"
            self.info_msg0 = self.small_ft.render('Victory!', False, self.TEXTCOLOR)
            self.info_msg1 = self.small_ft.render(msg, False, self.TEXTCOLOR)
        elif ev.won == -1:  # lost
            if self._mod.player_folded:
                msg = 'Player folded.'
            else:
                msg = 'Defeat.'
            self.info_msg0 = self.small_ft.render(msg, True, self.TEXTCOLOR)
            result = self._mod.prev_total_bet

            if self._mod.player_folded:
                self.info_msg1 = self.small_ft.render(f"You lost {result}$", False, self.TEXTCOLOR)
            else:
                infoh_dealer = self._mod.dealer_vhand.description
                infoh_player = self._mod.player_vhand.description
                self.info_msg1 = self.small_ft.render(
                    f"Player: {infoh_player}; Dealer: {infoh_dealer}; You've lost {result}$", False, self.TEXTCOLOR
                )
        else:
            raise ValueError('MatchOver event contains a non-valid value for attrib "won". Received value:', ev.won)

    @staticmethod
    def centerblit(refscr, surf, p):
        w, h = surf.get_size()
        refscr.blit(surf, (p[0] - w // 2, p[1] - h // 2))

    def _paint(self, refscr):
        refscr.fill('darkgreen')
        refscr.blit(self.bg, (0, 0))
        cardback = self._my_assets['card_back']

        # ---------- draw chip value if the phase is still "setante"
        if self._mod.stage == PokerStates.AnteSelection:
            # - draw chips + buttons
            for k, v in enumerate((2, 5, 10, 20)):
                adhoc_spr = self.chip_spr[str(v)]
                if v == 2:
                    adhoc_spr.rect.center = PLAYER_CHIPS['2b']
                refscr.blit(adhoc_spr.image, adhoc_spr.rect.topleft)
            self.chip_spr['2'].rect.center = PLAYER_CHIPS['2a']
            refscr.blit(self.chip_spr['2'].image, self.chip_spr['2'].rect.topleft)

            UthView.centerblit(refscr, self.chip_adhoc_image, self.chip_scr_pos)

            for b in self._act_related_wcontainer.content:
                refscr.blit(b.image, b.get_pos())

        else:
            # draw all cards, unless the state is AnteSelection
            for loc in CARD_SLOTS_POS.keys():
                if self._mod.visibility[loc]:
                    desc = self._mod.get_card_code(loc)
                    x = self._my_assets[desc]
                else:
                    x = cardback
                UthView.centerblit(refscr, x, CARD_SLOTS_POS[loc])

        # - do this for any PokerState!

        # draw ante, blind amounts, & the total cash
        for etq in self._money_labels.content:
            etq.draw()  # get_pos()
        # refscr.blit(self._money_labels['ante_etq'].image, MONEY_POS['ante'])
        # refscr.blit(self._money_labels['blind_etq'].image, MONEY_POS['blind'])
        # refscr.blit(self._money_labels['cash_etq'].image, (self.scrsize[0] + OFFSET_CASH[0], self.scrsize[1] + OFFSET_CASH[1]))

        # display all 3 prompt messages
        for rank, e in enumerate((self.info_msg0, self.info_msg1, self.info_msg2)):
            if e is not None:
                refscr.blit(e, (24, 10 + 50 * rank))

        self._chips_related_wcontainer.draw()
        self._act_related_wcontainer.draw()
        self._money_labels.draw()

    def on_paint(self, ev):
        if not self._assets_rdy:
            self._load_assets()
        self._paint(ev.screen)
