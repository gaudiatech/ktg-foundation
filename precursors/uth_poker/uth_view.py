import common
from uth_model import PokerStates


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
    'trips': (243, 175),
    'play': (231, 246),
    'ante': (214, 215),
    'blind': (258, 215),

    'cash': (10, 170),

    'e_trips': (210, 175),
    'e_play': (231, 234),
    'e_ante': (214, 205),
    'e_blind': (258, 205),
}

DIM_DROPZONES = [
    (70, 30),
    (112, 24)
]

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
        self.debug_drag_n_drop = False

        self._rect_dropzone_li = [
            pygame.Rect(MLABELS_POS['trips'], DIM_DROPZONES[0]),
            pygame.Rect((0, 0), DIM_DROPZONES[1])
        ]
        # adjust drop zones
        self._rect_dropzone_li[0].top -= 10
        self._rect_dropzone_li[0].left -= 8
        self._rect_dropzone_li[1].topleft = MLABELS_POS['ante']
        self._rect_dropzone_li[1].top -= 5
        for dzo in self._rect_dropzone_li:
            dzo.left -= 8

        self.overlay_spr = pygame.image.load('user_assets/overlay0.png')
        self.overlay_spr.set_colorkey((255, 0, 255))

        self.bg = None
        self._my_assets = dict()

        self.chip_spr = dict()
        self.adhoc_chip_spr = None
        self.dragged_chip_pos = None

        self._assets_rdy = False
        self._mod = model

        self.pokergame_ft = kengi.gfx.JsonBasedCfont(
            'user_assets/capello-ft'
        )  # EmbeddedCfont() #kengi.pygame.font.Font(None, 20)
        # if local ctx
        self.pokergame_ft.forcing_transparency = True

        self.info_msg0 = None
        self.info_msg1 = None  # will be used to tell the player what he/she has to do!
        self.info_messages = list()

        self.scrsize = kengi.get_surface().get_size()
        self.midpt = [self.scrsize[0] // 2, self.scrsize[1] // 2]

        self._chips_related_wcontainer = self._build_chips_related_gui()

        # self._chips_related_wcontainer.set_debug_flag()
        self.chip_scr_pos = tuple(PLAYER_CHIPS['2a'])
        self._gui_labels = None
        self._mlabels = None
        self._do_gui_labels()
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

    def _do_gui_labels(self):
        self._gui_labels = {
            'trips_etq': Label(MLABELS_POS['e_trips'], 'Trips', None, replacemt_ft=self.pokergame_ft),
            'ante_etq': Label(MLABELS_POS['e_ante'], 'Ante', None, replacemt_ft=self.pokergame_ft),
            'blind_etq': Label(MLABELS_POS['e_blind'], 'Blind', None, replacemt_ft=self.pokergame_ft),
            'play_etq': Label(MLABELS_POS['e_play'], 'Play', None, replacemt_ft=self.pokergame_ft),
        }

    def _do_set_money_labels(self):
        # ftsize_mlabels = 17
        self._mlabels = {
            # 'trips_etq': Label(MLABELS_POS['trips'], 'trips?', ftsize_mlabels),
            'trips_etq': Label(MLABELS_POS['trips'], 'trips?', None, replacemt_ft=self.pokergame_ft),
            'ante_etq': Label(MLABELS_POS['ante'], 'ante?', None, replacemt_ft=self.pokergame_ft),
            'blind_etq': Label(MLABELS_POS['blind'], 'blind?', None, replacemt_ft=self.pokergame_ft),
            'play_etq': Label(MLABELS_POS['play'], 'play?', None, replacemt_ft=self.pokergame_ft),
            'cash_etq': Label(MLABELS_POS['cash'], 'cash?', None, replacemt_ft=self.pokergame_ft),  # 4+ftsize_mlabels
        }

    def _build_chips_related_gui(self):  # TODO group with other obj so we have 1 panel dedicated to AnteSelection
        # - cycle right button
        def cb0():
            kengi.get_ev_manager().post(MyEvTypes.CycleChipval, upwards=True)

        cycle_r_button = kengi.gui.Button2(None, '>', (0, 0), callback=cb0)

        # - cycle left button
        def cb1():
            kengi.get_ev_manager().post(MyEvTypes.CycleChipval, upwards=False)

        cycle_l_button = kengi.gui.Button2(None, '<', (0, 0), callback=cb1)

        # disabled this, since Drag N Drop is working now
        # stake_button = kengi.gui.Button2(None, ' __+__ ', (0, 0), tevent=MyEvTypes.StackChip)

        chip_related_buttons = [
            cycle_l_button,
            # stake_button,
            cycle_r_button,
        ]
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

    def on_bet_reset(self, ev):
        self._mod.wallet.reset_bets(2)

    def on_chip_update(self, ev):
        # replace image in the sprite
        self.adhoc_chip_spr = self.chip_spr[str(ev.value)]

    def _load_assets(self):
        self.bg = kengi.pygame.image.load(BACKGROUND_IMG_PATH)
        spr_sheet = kengi.gfx.JsonBasedSprSheet('user_assets/pxart-french-cards')
        self._my_assets['card_back'] = spr_sheet['back-blue.png']
        for card_cod in StandardCard.all_card_codes():
            y = PokerHand.adhoc_mapping(card_cod[0]).lstrip('0') + card_cod[1].upper()  # convert card code to path
            self._my_assets[card_cod] = spr_sheet[f'{y}.png']
        spr_sheet2 = kengi.gfx.JsonBasedSprSheet('user_assets/pokerchips')

        for chip_val_info in ('2a', '2b', '5', '10', '20'):
            y = {
                '2a': 'chip02.png',
                '2b': 'chip02.png',
                '5': 'chip05.png',
                '10': 'chip10.png',
                '20': 'chip20.png'
            }[chip_val_info]  # adapt filename

            # no chip rescaling : tempimg = spr_sheet2[y]
            # chip rescaling:
            tempimg = pygame.transform.scale(spr_sheet2[y], CHIP_SIZE_PX)
            tempimg.set_colorkey((255, 0, 255))

            spr = kengi.pygame.sprite.Sprite()
            spr.image = tempimg
            spr.rect = spr.image.get_rect()
            spr.rect.center = PLAYER_CHIPS[chip_val_info]
            self.chip_spr['2' if chip_val_info in ('2a', '2b') else chip_val_info] = spr

        self.adhoc_chip_spr = self.chip_spr[str(self._mod.get_chipvalue())]
        self._assets_rdy = True

    def on_mousedown(self, ev):
        if self.adhoc_chip_spr.rect.collidepoint(
                kengi.vscreen.proj_to_vscreen(ev.pos)
        ):
            self.dragged_chip_pos = list(self.adhoc_chip_spr.rect.center)

    def on_mouseup(self, ev):
        if self.dragged_chip_pos:
            for k, dzo in enumerate(self._rect_dropzone_li):
                if dzo.collidepoint(self.dragged_chip_pos):
                    if k == 0:
                        # if we ever hav a poker backend..
                        # self.pev(MyEvTypes.StackChip, trips=True)

                        # but, until then:
                        if self._mod.wallet.can_stack(True):
                            self._mod.wallet.stack_chip(True)
                    else:
                        # idem ..
                        # self.pev(MyEvTypes.StackChip, trips=False)
                        if self._mod.wallet.can_stack():
                            self._mod.wallet.stack_chip()

            self.dragged_chip_pos = None

    def on_mousemotion(self, ev):
        if self.dragged_chip_pos:
            self.dragged_chip_pos[0], self.dragged_chip_pos[1] = kengi.vscreen.proj_to_vscreen(ev.pos)

    def on_money_update(self, ev):
        if self._act_related_wcontainer.active:
            bv = self._mod.wallet.bets['ante'] > 0
            for i in range(1, 4):  # all buttons except BetIdem
                self._act_related_wcontainer.content[i].set_enabled(bv)
        self._refresh_money_labels()

    def _refresh_money_labels(self):
        tripsv, antev, blindv, playv = self._mod.get_all_bets()
        x = self._mod.get_balance()

        self._mlabels['trips_etq'].text = f'%d CR' % tripsv
        self._mlabels['ante_etq'].text = f'%d CR' % antev
        self._mlabels['blind_etq'].text = f'%d CR' % blindv
        self._mlabels['play_etq'].text = f'%d CR' % playv

        self._mlabels['cash_etq'].text = f'Wealth: %d CR' % x

    def on_match_over(self, ev):
        self.info_msg2 = self.pokergame_ft.render('Click to restart', False, self.TEXTCOLOR)

        if ev.won == 0:  # tie
            self.info_msg0 = self.pokergame_ft.render('Its a Tie.', True, self.TEXTCOLOR)
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            self.info_msg1 = None
            result = self._mod.quantify_reward()  # can win due to Trips, even if its a Tie
            self.info_messages = [
                self.pokergame_ft.render(f"Dealer: {infoh_dealer};", False, self.TEXTCOLOR),
                self.pokergame_ft.render(f"Player: {infoh_player};", False, self.TEXTCOLOR),
                self.pokergame_ft.render(f"Change: {result} CR", False, self.TEXTCOLOR),
            ]

        elif ev.won == 1:  # won indeed
            result = self._mod.quantify_reward()
            infoh_player = self._mod.player_vhand.description
            infoh_dealer = self._mod.dealer_vhand.description
            # msg = f"Player: {infoh_player}; Dealer: {infoh_dealer}; Change {result}$"
            self.info_msg0 = self.pokergame_ft.render('Victory!', False, self.TEXTCOLOR)
            self.info_msg1 = None
            self.info_messages = [
                self.pokergame_ft.render(f"Dealer: {infoh_dealer};", False, self.TEXTCOLOR),
                self.pokergame_ft.render(f"Player: {infoh_player};", False, self.TEXTCOLOR),
                self.pokergame_ft.render(f"Change: {result} CR", False, self.TEXTCOLOR),
            ]

        elif ev.won == -1:  # lost
            if self._mod.player_folded:
                msg = 'Player folded.'
            else:
                msg = 'Defeat.'
            self.info_msg0 = self.pokergame_ft.render(msg, True, self.TEXTCOLOR)
            result = self._mod.wallet.prev_total_bet
            if self._mod.player_folded:
                self.info_msg1 = self.pokergame_ft.render(f"You lost {result} CR", False, self.TEXTCOLOR)
            else:
                infoh_dealer = self._mod.dealer_vhand.description
                infoh_player = self._mod.player_vhand.description
                self.info_messages = [
                    self.pokergame_ft.render(f"Dealer: {infoh_dealer}", False, self.TEXTCOLOR),
                    self.pokergame_ft.render(f"Player: {infoh_player}", False, self.TEXTCOLOR),
                    self.pokergame_ft.render(f"You lost {result} CR", False, self.TEXTCOLOR)
                ]

        else:
            raise ValueError('MatchOver event contains a non-valid value for attrib "won". Received value:', ev.won)

    @staticmethod
    def centerblit(refscr, surf, p):
        w, h = surf.get_size()
        refscr.blit(surf, (p[0] - w // 2, p[1] - h // 2))

    def on_paint(self, ev):
        if not self._assets_rdy:
            self._load_assets()
        refscr = ev.screen

        refscr.fill('darkgreen')
        # affiche mains du dealer +decor casino
        refscr.blit(self.bg, (0, 0))

        # - do this for any PokerState!
        refscr.blit(self.overlay_spr, OVERLAY_POS)

        # draw GUI labels...
        for etq in self._gui_labels.values():
            etq.draw()

        # draw ante, blind amounts, & the total cash
        for etq in self._mlabels.values():
            etq.draw()  # it has its pos inside the Label instance

        cardback = self._my_assets['card_back']

        # ---------- draw chip value if the phase is still "setante"
        if self._mod.stage == PokerStates.AnteSelection:

            self.adhoc_chip_spr.rect.center = PLAYER_CHIPS['2a']
            refscr.blit(self.adhoc_chip_spr.image, self.adhoc_chip_spr.rect.topleft)

            # -- debug chip img & dropzones {{
            if self.debug_drag_n_drop:
                pygame.draw.rect(refscr, 'red', (self.adhoc_chip_spr.rect.topleft, self.adhoc_chip_spr.image.get_size()), 1)
                for dzo in self._rect_dropzone_li:
                    pygame.draw.rect(refscr, 'orange', dzo, 1)
                for b in self._act_related_wcontainer.content:
                    refscr.blit(b.image, b.get_pos())
            # }}

            # draw the drag n drop Chip
            if self.dragged_chip_pos:
                UthView.centerblit(ev.screen, self.adhoc_chip_spr.image, self.dragged_chip_pos)

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
                    refscr.blit(e, (STATUS_MSG_BASEPOS[0], STATUS_MSG_BASEPOS[1] + offsety * (rank + 1)))

        self._chips_related_wcontainer.draw()
        # self._money_labels.draw()
        self._act_related_wcontainer.draw()
        self.generic_wcontainer.draw()  # will be drawn or no, depending on if its active!
