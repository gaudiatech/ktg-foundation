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
Label = kengi.gui.Label

# constants
CST_VSPACING_BT = 4
CST_HSPACING_BT = 10  # buttons that are actual player controls, at every pokerstate

OVERLAY_POS = (85, 35)
CHIP_SIZE_PX = (33, 33)
BACKGROUND_IMG_PATH = 'user_assets/pokerbackground3.png'
OFFSET_CASH = (-48, -24)
BASE_X_CARDS_DR = 326
Y_CARDS_DRAWN = 132
CRD_OFFSET = 43
MLABELS_POS = {
    'trips': (243, 173),

    'ante': (214, 215),
    'blind': (258, 215),
    'play': (231, 243),

    'cash': (10, 170),
}

CARD_SLOTS_POS = {  # coords in pixel -> where to place cards/chips
    'dealer1': (241, 60),
    'dealer2': (241 + CRD_OFFSET, 60),

    'flop3': (BASE_X_CARDS_DR - 2 * CRD_OFFSET, Y_CARDS_DRAWN),
    'flop2': (BASE_X_CARDS_DR - 1 * CRD_OFFSET, Y_CARDS_DRAWN),
    'flop1': (BASE_X_CARDS_DR, Y_CARDS_DRAWN),
    'river': (BASE_X_CARDS_DR - 3 * CRD_OFFSET, Y_CARDS_DRAWN),
    'turn': (BASE_X_CARDS_DR - 4 * CRD_OFFSET, Y_CARDS_DRAWN),

    'player1': (111, 215),
    'player2': (111 + CRD_OFFSET, 215),
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
    '2a': (238, 278),  # the only cst value used rn

    '2b': (905 / 2, 1000 / 2),
    '5': (985 / 2, 1000 / 2),
    '10': (1065 / 2, 1000 / 2),
    '20': (1145 / 2, 1000 / 2)
}
CHIP_SELECTOR_POS = (168, 295)
STATUS_MSG_BASEPOS = (8, 258)


class UthView(kengi.EvListener):
    TEXTCOLOR = kengi.pal.punk['flashypink']
    BG_TEXTCOLOR = (92, 92, 100)
    ASK_SELECTION_MSG = 'SELECT ONE OPTION: '

    def __init__(self, model):
        super().__init__()
        self.overlay_spr = pygame.image.load('user_assets/overlay0.png')
        self.overlay_spr.set_colorkey((255, 0, 255))

        self.bg = None
        self._my_assets = dict()

        self.chip_spr = dict()
        self.chip_adhoc_image = None

        self._assets_rdy = False
        self._mod = model
        self.small_ft = kengi.pygame.font.Font(None, 20)
        self.info_msg0 = None
        self.info_msg1 = None  # will be used to tell the player what he/she has to do!
        self.info_messages = list()

        self.scrsize = kengi.get_surface().get_size()
        self.midpt = [self.scrsize[0] // 2, self.scrsize[1] // 2]

        self._chips_related_wcontainer = self._build_chips_related_gui()

        # self._chips_related_wcontainer.set_debug_flag()

        self.chip_scr_pos = tuple(PLAYER_CHIPS['2a'])

        self._mlabels = None
        self._do_set_money_labels()  # replace prev. line by a meaningful dict

        self.act_deal_cards = None
        self.act_undo_stake = None
        self.act_bet_same = None
        self.act_clear_chips = None
        self._act_related_wcontainer = self._init_actions_related_gui()
        # force affichage du W. container
        # self._act_related_wcontainer.set_debug_flag()

        self.generic_wcontainer = wContainer(
            (320, 244), (133, 250), wContainer.FLOW,
            [
                kengi.gui.Button2(None, 'Bet x4', (0, 0), tevent=MyEvTypes.BetHighDecision),
                kengi.gui.Button2(None, 'Bet x3', (0, 0), tevent=MyEvTypes.BetDecision),
                kengi.gui.Button2(None, 'Check', (0, 0), tevent=MyEvTypes.CheckDecision)
            ],
            spacing=CST_HSPACING_BT,
            vspacing=CST_VSPACING_BT
        )

        self.on_money_update(None)  # force a 1st money update

    def _do_set_money_labels(self):
        ftsize_mlabels = 17
        self._mlabels = {
            'trips_etq': Label(MLABELS_POS['trips'], 'trips?', ftsize_mlabels),
            'ante_etq': Label(MLABELS_POS['ante'], 'ante?', ftsize_mlabels),
            'blind_etq': Label(MLABELS_POS['blind'], 'blind?', ftsize_mlabels),
            'play_etq': Label(MLABELS_POS['play'], 'play?', ftsize_mlabels),
            'cash_etq': Label(MLABELS_POS['cash'], 'cash?', 4+ftsize_mlabels)
        }
        # return wContainer(
        #     (32, self.midpt[1] + 66),
        #     (128, 128),
        #     wContainer.FLOW,
        #     all_lbl,
        #     spacing=2
        # )

    def _build_chips_related_gui(self):  # TODO group with other obj so we have 1 panel dedicated to AnteSelection
        # -----------------
        # --- cycle right button
        def cb0():
            kengi.get_ev_manager().post(MyEvTypes.CycleChipval, upwards=True)

        cycle_r_button = kengi.gui.Button2(None, '>', (0, 0), callback=cb0)

        # --- cycle left button
        def cb1():
            kengi.get_ev_manager().post(MyEvTypes.CycleChipval, upwards=False)

        cycle_l_button = kengi.gui.Button2(None, '<', (0, 0), callback=cb1)

        stake_button = kengi.gui.Button2(None, ' __+__ ', (0, 0), tevent=MyEvTypes.StackChip)
        # -----------------

        chip_related_buttons = [
            cycle_l_button,
            stake_button,
            cycle_r_button,
        ]
        # for b in chip_related_buttons:
        #    b.set_active()

        targ_w = 140
        return wContainer(
            CHIP_SELECTOR_POS,
            (targ_w, 32),
            wContainer.EXPAND,
            chip_related_buttons, spacing=8
        )

    @staticmethod
    def _init_actions_related_gui():
        all_bt = [
            kengi.gui.Button2(None, 'Bet_Same', (0, 11), tevent=MyEvTypes.BetIdem),  # bet same action is Bt #0

            kengi.gui.Button2(None, 'Deal', (330, 128), tevent=MyEvTypes.DealCards),
            kengi.gui.Button2(None, 'Undo', (0, 0), tevent=MyEvTypes.BetUndo),
            kengi.gui.Button2(None, 'Reset_Bet', (0, 0), tevent=MyEvTypes.BetReset),
        ]

        return wContainer(
            (390, 170),
            (60, 170),
            wContainer.FLOW, all_bt, spacing=CST_HSPACING_BT, vspacing=CST_VSPACING_BT
        )

    def show_anteselection(self):
        # ensure everything is reset
        del self.info_messages[:]

        self._chips_related_wcontainer.set_active()

        self._act_related_wcontainer.set_active()
        self._act_related_wcontainer.content[0].set_enabled(False)
        self._act_related_wcontainer.content[1].set_enabled(False)
        self._act_related_wcontainer.content[2].set_enabled(False)
        self._act_related_wcontainer.content[3].set_enabled(False)

    def hide_anteselection(self):
        # if self._chips_related_wcontainer.active:
        self._chips_related_wcontainer.set_active(False)
        # if self._act_related_wcontainer.active:
        self._act_related_wcontainer.set_active(False)

    def show_generic_gui(self):
        self.generic_wcontainer.set_active()
        # For extra- practicity, add custom getters to the object WidgetContainer that we use
        self.generic_wcontainer.bethigh_button = self.generic_wcontainer.content[0]
        self.generic_wcontainer.bet_button = self.generic_wcontainer.content[1]
        self.generic_wcontainer.check_button = self.generic_wcontainer.content[2]

    def hide_generic_gui(self):
        self.generic_wcontainer.set_active(False)

    # def turn_on(self):
    #     super().turn_on()
    #     for b in self._chips_related_wcontainer.content:
    #         b.turn_on()
    #     for b in self._act_related_wcontainer.content:
    #         b.turn_on()

    # def turn_off(self):
    #     super().turn_off()
    #     for b in self._chips_related_wcontainer.content:
    #         b.turn_off()
    #     for b in self._act_related_wcontainer.content:
    #         b.turn_off()

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
            tempimg.set_colorkey((255, 0, 255))

            spr = kengi.pygame.sprite.Sprite()
            spr.image = tempimg
            spr.rect = spr.image.get_rect()
            spr.rect.center = PLAYER_CHIPS[chip_val_info]
            self.chip_spr['2' if chip_val_info in ('2a', '2b') else chip_val_info] = spr

        self.chip_adhoc_image = self.chip_spr[str(self._mod.get_chipvalue())].image

        self._assets_rdy = True

    def on_money_update(self, ev):
        if self._act_related_wcontainer.active:
            bv = self._mod.wallet.bets['ante'] > 0
            for i in range(1, 4):
                self._act_related_wcontainer.content[i].set_enabled(bv)  # all buttons except BetIdem
        self._refresh_money_labels()

    # def on_new_match(self, ev):
    #     self._refresh_money_labels()

    def _refresh_money_labels(self):
        tripsv, antev, blindv, playv = self._mod.get_all_bets()
        x = self._mod.get_balance()

        self._mlabels['trips_etq'].text = f'%d CR' % tripsv
        self._mlabels['ante_etq'].text = f'%d CR' % antev
        self._mlabels['blind_etq'].text = f'%d CR' % blindv
        self._mlabels['play_etq'].text = f'%d CR' % playv

        self._mlabels['cash_etq'].text = f'wealth: %d CR' % x

    def on_match_over(self, ev):
        self.info_msg2 = self.small_ft.render('click once to restart', False, self.TEXTCOLOR)

        if ev.won == 0:  # tie
            self.info_msg0 = self.small_ft.render('Its a Tie.', True, self.TEXTCOLOR)
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            self.info_msg1 = None
            self.info_messages = [
                self.small_ft.render(f"Dealer: {infoh_dealer};", False, self.TEXTCOLOR),
                self.small_ft.render(f"Player: {infoh_player};", False, self.TEXTCOLOR),
                self.small_ft.render("Change: 0 CR", False, self.TEXTCOLOR),
            ]

        elif ev.won == 1:  # won indeed
            result = self._mod.quantify_reward()
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            # msg = f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {result}$"
            self.info_msg0 = self.small_ft.render('Victory!', False, self.TEXTCOLOR)
            self.info_msg1 = None
            self.info_messages = [
                self.small_ft.render(f"Dealer: {infoh_dealer};", False, self.TEXTCOLOR),
                self.small_ft.render(f"Player: {infoh_player};", False, self.TEXTCOLOR),
                self.small_ft.render(f"Change: {result} CR", False, self.TEXTCOLOR),
            ]

        elif ev.won == -1:  # lost
            if self._mod.player_folded:
                msg = 'Player folded.'
            else:
                msg = 'Defeat.'
            self.info_msg0 = self.small_ft.render(msg, True, self.TEXTCOLOR)
            result = self._mod.wallet.prev_total_bet
            if self._mod.player_folded:
                self.info_msg1 = self.small_ft.render(f"You lost {result} CR", False, self.TEXTCOLOR)
            else:
                infoh_dealer = self._mod.dealer_vhand.description
                infoh_player = self._mod.player_vhand.description
                self.info_messages = [
                    self.small_ft.render(f"Dealer: {infoh_dealer}", False, self.TEXTCOLOR),
                    self.small_ft.render(f"Player: {infoh_player}", False, self.TEXTCOLOR),
                    self.small_ft.render(f"You lost {result} CR", False, self.TEXTCOLOR)
                ]

        else:
            raise ValueError('MatchOver event contains a non-valid value for attrib "won". Received value:', ev.won)

    @staticmethod
    def centerblit(refscr, surf, p):
        w, h = surf.get_size()
        refscr.blit(surf, (p[0] - w // 2, p[1] - h // 2))

    def _paint(self, refscr):
        refscr.fill('darkgreen')

        # affiche mains du dealer +decor casino
        refscr.blit(self.bg, (0, 0))

        # - do this for any PokerState!
        refscr.blit(self.overlay_spr, OVERLAY_POS)
        # draw ante, blind amounts, & the total cash
        for etq in self._mlabels.values():
            etq.draw()  # it has its pos inside the Label instance

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
            # ----------------
            #  draw all cards
            # ----------------
            for loc in CARD_SLOTS_POS.keys():
                if self._mod.visibility[loc]:
                    desc = self._mod.get_card_code(loc)
                    x = self._my_assets[desc]
                else:
                    x = cardback
                UthView.centerblit(refscr, x, CARD_SLOTS_POS[loc])

        # display all 3 prompt messages
        offsety = 24
        if self.info_msg0:
            refscr.blit(self.info_msg0, STATUS_MSG_BASEPOS)
        if self.info_msg1:
            rank = 1
            refscr.blit(self.info_msg1, (STATUS_MSG_BASEPOS[0], STATUS_MSG_BASEPOS[1] + offsety * rank))
        else:
            if len(self.info_messages):
                for rank, e in enumerate(self.info_messages):
                    refscr.blit(e, (STATUS_MSG_BASEPOS[0], STATUS_MSG_BASEPOS[1] + offsety * (rank+1)))

        self._chips_related_wcontainer.draw()
        # self._money_labels.draw()
        self._act_related_wcontainer.draw()
        self.generic_wcontainer.draw()  # will be drawn or no, depending on if its active!

    def on_paint(self, ev):
        if not self._assets_rdy:
            self._load_assets()
        self._paint(ev.screen)
