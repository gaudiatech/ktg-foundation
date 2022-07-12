import json
import random
from collections import defaultdict

import katagames_sdk as katasdk
kengi = katasdk.bootstrap()

# constants
ASSET_ALIASES = {
    'musiquefond': 'tetrav/myassets/chiptronic.ogg',
    'bruitage_menu': 'tetrav/myassets/coinlow.wav',
    'valid_menu': 'tetrav/myassets/coinhigh.wav',
    'explo': 'tetrav/myassets/explo_basique.wav',
    'quake': 'tetrav/myassets/crumble.wav',
    'fond_gameover': 'tetrav/myassets/img_bt_rouge.png'
}

# katapi = katasdk.api
pygame = kengi.pygame
enum_builder = kengi.struct.enum
BaseGameState = kengi.BaseGameState
EngineEvTypes = kengi.event.EngineEvTypes
EventReceiver = kengi.event.EventReceiver
CgmEvent = kengi.event.CgmEvent

# ----------------------------- pseudo glvars module -------------
my_fonts = {
    # 'larger': ('freesansbold.ttf', 27),
    # 'xl': ('freesansbold.ttf', 35),
    # 'display_font': ('freesansbold.ttf', 22),
    # 'basic': ('freesansbold.ttf', 16),
    # 'medium': ('freesansbold.ttf', 21),

    # -multiples de 16 fortement recommandé
    'tiny_monopx': (None, 16),  # normalement: 'monogram.ttf'
    'sm_monopx': (None, 28),
    'moderne': (None, 32),
    'moderne_big': (None, 64)
}
SCR_W = SCR_H = None  # to be set in pgm body


my_colors = {
    'c_black': '#000000',
    'c_white': '#ffffff',
    'c_cherokee': '#924a40',
    'c_oceanblue': '#84c5cc',

    'c_plum': '#9351b6',
    'c_leafgreen': '#72b14b',
    'c_purple': '#483aaa',
    'c_sunny': '#d5df7c',

    'c_brown': '#99692d',
    'c_mud': '#675200',
    'c_skin': '#c18178',
    'c_gray1': '#606060',

    'c_gray2': '#8a8a8a',
    'c_pastelgreen': '#b3ec91',
    'c_lightpurple': '#867ade',
    'c_gray3': '#b3b3b3',
}


# ----------------------
#  CONSTANTS
DEV_MODE = False
SKIP_MINING = False
MAX_FPS = 45
VERSION = '0.20.1a'
RESSOURCE_LOC = ['.']
CHOSEN_LANG = 'fr'
GAME_ID = 5  # tetravalanche


#  GLOBAL VARIABLES
# ----------------------

glvars = katasdk.Objectifier(**{
    'DEV_MODE': True,
    'GAME_ID': 5,  # euhmmm Jen suis mm pas sur!

    'username': None,
    'acc_id': None,
    'song': None,
    'snd_channels': dict(),
    'num_lastchannel': 0,
    'copie_solde': None,
    'colors': dict(),
    'fonts': dict(),

    'num_challenge': None,  # sera un entier
    'chall_seed': None,  # sera un entier déterminant cmt générateur aléatoire va sortir les données du problème d'optim.

    'multiplayer_mode': None,  # sera déterminé en fct de s'il y a des joueurs "remote"
    'server_host': None,  # recevra un str
    'server_port': None,  # recevra un int
    'server_debug': None,
    'solde_gp': None
})


def glvars_init_sound():
    if len(glvars.snd_channels) < 1:
        capital_n = 3
        pygame.mixer.set_num_channels(capital_n)
        for k in range(capital_n):
            glvars.snd_channels[k] = pygame.mixer.Channel(k)


def glvars_is_sfx_playin():
    for cn in range(2):
        if glvars.snd_channels[cn].get_busy():
            return True
    return False


def glvars_playmusic():
    if glvars.song is None:
        pygame.mixer.music.load(ASSET_ALIASES['musiquefond'])
        glvars.song = 1
    pygame.mixer.music.play(-1)


def glvars_playsfx(pygamesound):
    # TODO this is temp fix, for web ctx
    pygamesound.play()


def glvars_init_fonts_n_colors():
    pygame.font.init()
    for name, v in my_colors.items():
        glvars.colors[name] = pygame.Color(v)
    for name, t in my_fonts.items():
        glvars.fonts[name] = pygame.font.Font(None, t[1])

# -------------------fin pseudo glvars mod -----------------------


SCR_W, SCR_H = -1, -1  # will be set when run_game() called

GameStates = enum_builder(
    # avant on utilisait Login defini dans ce mm programme,
    # mais depuis sdk 0.0.7 il est préconisé d' utiliser le
    # Kata bioslike truc et cest ce quon va faire! Voir corps du programme
    # 'Login',
    # il recoit l identifiant -1

    'Menu',
    'Tetris'
)

Labels = enum_builder(
    'PoidsTotal',
    'UtiliteTotale',
    'Minage1',  # titre affiché pr le mode taxe
    'Minage2',  # phrase attente
    'WindowCaption',
    'Utilisateur',
    'Solde',
    'Invite',
    'NomJoueurAnonyme',
    'EndEasyWin',
    'EndEasyLoose',
    'EndChallenge1',
    'EndGameAction',  # pr indiquer ce que lutilisateur doit faire
    'SensLogin',  # titre mode login
    'WordLogin',
    'WordPassword',
    'OpenBrowser',
    'CanCreateAcc',  # phrase pr dire tu peux taper les infos!
    'InciteLudoStore',
    'CannotLogin',
    'Connexion',
    'MenuDefi',
    'MenuGridGame',  # nom bouton pour exec. grid game
    'MenuTuto',
    'MenuEntrainement',
    'MenuQuitter',
    'RetourArr',
    'NoTraining',
    'CompteRequis',
    'CoutDefi'
)

MyEvTypes = kengi.event.enum_ev_types(
    'Drop',  # contains new_level
    'Shake',
    'LevelUp',  # contains level
    'ChoiceChanges',  # contient code
    'LineDestroyed',
    'FlatWorld',  # means the shake effect is over
    'BlocksCrumble',
    'GameLost',
    'DemandeTournoi',
    'ChoixMenuValidation',
    # -------------------
    'ItemGetsPlaced',  # contient cell une paire ij, ref_repr_g la référence sur item cliquable
    'ItemDragged',  # contient ref_item
    'ItemDrops',  # item cliquable déposé contient ref_item
    'PlayerLogsIn',  # contient username, solde
    'LoginModUpdate',  # contient valeurs pr: login, pwd
    'TrigValidCredentials',
    'FakeLogin',
    'LoadingBarMoves',
    'BalanceChanges',  # contiendra value (un int)
    'ContentChanges',  # quand un item est pris/déposé
    'TurnEnds',
    'PlayerSelects',
    'SelectResult',
    'GstateUpdate',
    'AttackResult',
    'PlayerDies',
    'PlayerWins',
    'AddDices',
    'ConquestGameStart',
    'ConquestGameOver',
    'LandValueChanges',  # contient land_id, num_dice
    'LandOwnerChanges',  # contient land_id, owner_pid
    'MapChanges',
    'RemotePlayerPasses',  # grâce à ça, le ctrl réseau peut forcer ctrl RemotePlayer à rendre la main normalement
    'PlayerPasses',  # contient [old_pid, new_pid]
    'ForceEcoute',
    'RequestMap'
)

_str_repo = dict()
_print_dim = False


def is_user_logged():
    return True
    # disable login/auth procedure
    # return glvars.username is not None


def safe_get_username():
    return 'player1'
    #if not is_user_logged():
    #    return tsl(Labels.NomJoueurAnonyme)
    #return glvars.username


def get_solde():
    if not is_user_logged():
        raise Exception('demande solde alors que _logged_in à False')
    return glvars.solde_gp


def set_solde(val):
    glvars.solde_gp = val
    manager = kengi.get_manager()
    manager.post(
        CgmEvent(MyEvTypes.BalanceChanges, value=val)
    )


class Etiquette:
    ft_obj = None

    def __init__(self, text, pos, rgb_color):
        if self.ft_obj is None:
            raise ValueError('use set_font(...) first! ')
        self._text = text
        self.pos = pos
        self._color = rgb_color
        self.img = self.ft_obj.render(self._text, True, self._color)

    @classmethod
    def set_font(cls, ft_obj):
        cls.ft_obj = ft_obj

    def get_text(self):
        return self._text

    def set_text(self, t):
        self._text = t
        self.img = self.ft_obj.render(self._text, True, self._color)


class MenuModel(kengi.event.CogObj):
    """
    stocke l'info. si le joueur est connecté ou nom
    """
    COUT_PARTIE = 10
    BINF_CHOIX = 134
    CHOIX_LOGIN, CHOIX_START, CHOIX_CRED, CHOIX_QUIT = range(BINF_CHOIX, BINF_CHOIX + 4)

    def __init__(self):
        super().__init__()
        self._curr_choice = None
        self._logged_in = None
        self.reset_choice()

    def reset_choice(self):
        if is_user_logged():
            self._curr_choice = self.CHOIX_START
            self._logged_in = True
        else:
            self._curr_choice = self.CHOIX_LOGIN
            self._logged_in = False
        self.pev(MyEvTypes.ChoiceChanges, code=self._curr_choice)

    def get_curr_choice(self):
        return self._curr_choice

    def set_choice(self, v):
        self._curr_choice = v

    def move(self, direction):
        assert direction in (-1, +1)
        self._curr_choice += direction
        if not is_user_logged():
            if self._curr_choice == self.CHOIX_START:
                self._curr_choice += direction
            if self._curr_choice > self.CHOIX_QUIT:
                self._curr_choice = self.CHOIX_LOGIN
            elif self._curr_choice < self.CHOIX_LOGIN:
                self._curr_choice = self.CHOIX_QUIT
            self.pev(MyEvTypes.ChoiceChanges, code=self._curr_choice)
            return
        # on est connecté
        if self._curr_choice == self.CHOIX_LOGIN:
            self._curr_choice += direction
        if self._curr_choice > self.CHOIX_QUIT:
            self._curr_choice = self.CHOIX_START
        elif self._curr_choice < self.CHOIX_START:
            self._curr_choice = self.CHOIX_QUIT
        self.pev(MyEvTypes.ChoiceChanges, code=self._curr_choice)

    def mark_auth_done(self, user, solde_gp):
        self._logged_in = True
        glvars.username = user
        glvars.solde_gp = solde_gp

    def mark_logout(self):
        self._logged_in = False
        # utility?
        # glvars.cli_logout()

    def can_bet(self):
        print('----- can bet test ----')
        if not self._logged_in:
            return False
        if get_solde() is None:
            return False
        return get_solde() >= self.COUT_PARTIE


class MenuView(EventReceiver):
    """
    se basera sur un modèle pouvant alterner entre DEUX etats:
    (1) guest, et (2) player_known
    le choix "start" ne sera dévérouillé que dans le cas 2
    """
    TXT_COLOR_HL = (217, 25, 84)
    TXT_COLOR = (110, 80, 90)
    BASE_X_MENU = 175
    TAQUET_VERT = 505
    # constantes etiquette txt
    LABEL_USER_POS = (TAQUET_VERT, 165)
    LABEL_SOLDE_POS = (TAQUET_VERT, 215)
    # constantes pr placement des boutons
    BT_LOGIN_POS = (TAQUET_VERT, BASE_X_MENU + 100)
    BT_TRAINING_POS = (TAQUET_VERT, BASE_X_MENU + 170)
    BT_CHALL_POS = (TAQUET_VERT, BASE_X_MENU + 285)
    BT_EXIT_POS = (TAQUET_VERT, BASE_X_MENU + 350)
    ICON_POS = (TAQUET_VERT - 52, BT_CHALL_POS[1] - 4)
    REAL_TITLE = '_Tetravalanche_'
    BROKEN_TIT = '-T3trava|a~ch3+'

    def __init__(self, ref_mod):
        super().__init__()
        self.__class__.POS_ETQ_VER = (8, SCR_H - 24)
        self.FG_COLOR = glvars.colors['c_lightpurple']
        self.TITLE_COLOR = glvars.colors['c_skin']
        self.BG_COLOR = glvars.colors['c_purple']
        self.SELEC_COLOR = glvars.colors['c_oceanblue']
        # - son
        self.sfx_low = pygame.mixer.Sound(ASSET_ALIASES['bruitage_menu'])
        self.sfx_high = pygame.mixer.Sound(ASSET_ALIASES['valid_menu'])
        # - polices de car.
        self._bigfont = glvars.fonts['moderne_big']
        self._medfont = glvars.fonts['moderne']
        # ****************** creation etiquettes pr le menu ******************
        self._options_menu = {
            MenuModel.CHOIX_LOGIN: 'Se connecter',
            MenuModel.CHOIX_START: 'Start challenge',
            MenuModel.CHOIX_CRED: 'Misc info',
            MenuModel.CHOIX_QUIT: 'Exit'
        }
        self._codeselection_to_img = dict()
        self._codeselection_to_rect = dict()
        self._codeselection_to_pos = dict()

        for code in self._options_menu.keys():
            self._reset_label_option(code)

        self._mem_option_active = None
        self.activation_option(ref_mod.get_curr_choice())
        # ****************** prepa pour effets particules ******************
        self._allwalker_pos = list()
        self._walker_speed = dict()
        for k in range(20):
            self._walker_speed[k] = random.randint(1, 6)
            i, j = random.randint(0, SCR_W - 1), random.randint(0, SCR_H - 1)
            self._allwalker_pos.append([i, j])
        self._label_titre = self._bigfont.render(
            self.REAL_TITLE, False, self.TITLE_COLOR
        )
        self._pos_titre = (SCR_W // 2 - (self._label_titre.get_size()[0] // 2), 50)
        self.mod = ref_mod
        self._hugefont = glvars.fonts['moderne']
        self._font = glvars.fonts['tiny_monopx']
        self._smallfont = glvars.fonts['tiny_monopx']
        self._boutons = list()
        self.bt_chall = None
        self.bt_login = None
        self.bt_exit = None
        # - crea etiquettes qui habillent bouton challenge
        Etiquette.set_font(glvars.fonts['moderne'])
        self._etq_user = None
        self._etq_solde = None
        self.refresh_graphic_state()

    @staticmethod
    def prettify(txt):
        return '/\\----[__' + txt + '__]----\\/'

    def _reset_label_option(self, code):
        txt = self._options_menu[code]
        adhoc_label = self._medfont.render(txt, False, self.FG_COLOR)
        self._codeselection_to_img[code] = adhoc_label
        self._refresh_rect(code, adhoc_label)

    def _refresh_rect(self, code, adhoc_label):
        tmp_rect = adhoc_label.get_rect()
        base_y = 128
        base_x = SCR_W // 2
        offset = 40
        tmp = (MenuModel.CHOIX_LOGIN, MenuModel.CHOIX_START, MenuModel.CHOIX_CRED, MenuModel.CHOIX_QUIT)

        if code not in tmp:
            raise ValueError('code ds _refresh_rect nest pas correct!')
        i = tmp.index(code)

        pos = (base_x - (adhoc_label.get_size()[0] // 2), base_y + i * offset)
        self._codeselection_to_pos[code] = pos
        tmp_rect.topleft = pos
        self._codeselection_to_rect[code] = tmp_rect

    def activation_option(self, code):
        if self._mem_option_active != code:
            if self._mem_option_active is not None:
                glvars_playsfx(self.sfx_low)
                self._reset_label_option(self._mem_option_active)
            tmp = self._options_menu[code]
            txt = MenuView.prettify(tmp)
            adhoc_label = self._medfont.render(txt, False, self.SELEC_COLOR)
            self._codeselection_to_img[code] = adhoc_label
            self._refresh_rect(code, adhoc_label)
            self._mem_option_active = code

    def validate_effect(self):
        glvars_playsfx(self.sfx_high)

    def refresh_graphic_state(self):
        label_user = tsl(Labels.Utilisateur)
        label_solde = tsl(Labels.Solde)
        txt = '{}= {}'.format(label_user, safe_get_username())
        self._etq_user = self._hugefont.render(txt, True, self.FG_COLOR)
        if is_user_logged():
            wtxt = '{}= {} mGold'.format(label_solde, get_solde())
            self._etq_solde = self._hugefont.render(wtxt, True, self.FG_COLOR)
        else:
            self._etq_solde = None

    def proc_event(self, ev, source):
        if ev.type == pygame.MOUSEMOTION:
            # self._options_menu.keys():
            for givcod in (MenuModel.CHOIX_START, MenuModel.CHOIX_QUIT, MenuModel.CHOIX_CRED):
                if self._codeselection_to_rect[givcod].collidepoint(ev.pos):
                    self.activation_option(givcod)
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            for givcod in (MenuModel.CHOIX_START, MenuModel.CHOIX_QUIT, MenuModel.CHOIX_CRED):
                if self._codeselection_to_rect[givcod].collidepoint(ev.pos):
                    self.mod.set_choice(givcod)
                    self.pev(MyEvTypes.ChoixMenuValidation)
        elif ev.type == MyEvTypes.ChoiceChanges:
            self.activation_option(ev.code)
        elif ev.type == EngineEvTypes.PAINT:
            self.draw_content(ev.screen)
            # pygame.draw.rect(ev.screen,(255,0,0), self._codeselection_to_rect[MenuModel.CHOIX_START], 2)
        elif ev.type == MyEvTypes.BalanceChanges:
            self.refresh_graphic_state()
        # -- cétait pour tester
        # elif ev.type == MyEvTypes.FakeLogin:
        #     self.mod.mark_auth_done('Roger', 997)
        #     self.bt_login.turn_off()
        #     self.refresh_graphic_state()

    def dessin_boutons(self, screen):
        if is_user_logged():
            omega_choix = (MenuModel.CHOIX_START, MenuModel.CHOIX_CRED, MenuModel.CHOIX_QUIT)
        else:
            omega_choix = (MenuModel.CHOIX_LOGIN, MenuModel.CHOIX_CRED, MenuModel.CHOIX_QUIT)
        for c in omega_choix:
            label = self._codeselection_to_img[c]
            pos = self._codeselection_to_pos[c]
            screen.blit(label, pos)

    def draw_content(self, screen):
        screen.fill(self.BG_COLOR)
        # - dessin bonhommes
        for k, pos in enumerate(self._allwalker_pos):
            spd = self._walker_speed[k]
            pos[1] += spd
            if spd in (1, 2):
                spd_based_color = glvars.colors['c_mud']
            elif spd in (3, 4):
                spd_based_color = glvars.colors['c_brown']
            else:
                spd_based_color = glvars.colors['c_gray1']
            pos[1] = pos[1] % SCR_H
            pygame.draw.rect(screen, spd_based_color, (pos[0], pos[1], 4, 6))
        # - dessin titre
        if random.random() < 0.1:
            if random.random() > 0.5:
                txt = self.REAL_TITLE
            else:
                txt = self.BROKEN_TIT
            self._label_titre = self._bigfont.render(txt, False, self.TITLE_COLOR)
        screen.blit(self._label_titre, self._pos_titre)
        # -- menu --
        self.dessin_boutons(screen)
        # pygame.transform.scale(self._vscreen, glvars.SCREEN_SIZE, screen)

    # association état avec ceux des boutons
    def turn_on(self, prio=None):
        super().turn_on()
        for bt in self._boutons:
            bt.turn_on()
        self.refresh_graphic_state()

    def turn_off(self):
        super().turn_off()
        for bt in self._boutons:
            bt.turn_off()


class MenuCtrl(EventReceiver):
    """
    possède un attribut
     self.nextmode_buffer pour signaler dans quel etat on va passer
    """
    POLLING_FREQ = 4  # sec. de délai entre deux appels serveur

    def __init__(self, mod, view):
        super().__init__()
        self.ref_mod = mod
        self.ref_view = view
        # - prepa de quoi changer de mode de jeu...
        self.nextmode_buffer = None
        self._assoc_cchoix_event = {
            MenuModel.CHOIX_QUIT: CgmEvent(pygame.QUIT),
            MenuModel.CHOIX_CRED: None,  # kengi.CgmEvent(EngineEvTypes.PUSHSTATE, state_ident=GameStates.Credits),
            MenuModel.CHOIX_START: None,  # celui-ci est géré via un evenement MyEvTypes.DemandeTournoi !
            MenuModel.CHOIX_LOGIN: None  # CgmEvent(EngineEvTypes.PUSHSTATE, state_ident=defs.GameStates.Login)
        }
        # - misc
        self.last_pol = None
        self.polling_mode = True

        # self.serv = kengi.network.HttpServer.instance()

    def pause_polling(self):
        self.polling_mode = False

    def resume_polling(self):
        self.polling_mode = True

    def __handlelogic(self, ev):
        if self.nextmode_buffer is None:
            if is_user_logged():
                if self.polling_mode:
                    if (self.last_pol is None) or (ev.curr_t - self.last_pol > self.POLLING_FREQ):
                        self.last_pol = ev.curr_t
                        nouv_solde = self._recup_solde_serveur()
                        set_solde(nouv_solde)

        else:  # -----------------------------------------------
            if glvars_is_sfx_playin():
                pass
            else:
                # traitement du nextmode_buffer
                if self.nextmode_buffer == MenuModel.CHOIX_LOGIN:
                    self.pev(EngineEvTypes.PUSHSTATE, state_ident=GameStates.Login)

                elif self.nextmode_buffer == MenuModel.CHOIX_START:
                    self.pev(MyEvTypes.DemandeTournoi)
                else:
                    ev = self._assoc_cchoix_event[self.nextmode_buffer]
                    if ev is not None:
                        kengi.event.EventManager.instance().post(ev)
                # reset du champ concerné
                self.nextmode_buffer = None

    def _procedure_debut_challenge(self):
        """
        :return: bool disant si oui ou non, la procédure s'est déroulé correctement
        """
        return True

        if glvars.DEV_MODE:
            print('DEBUG:  _procedure_debut_challenge')
        # - on récupère n° seed et de tournoi
        target = self.serv.get_ludo_app_url() + 'tournois.php'
        params = {
            'fct': 'play_it',
            'game_id': str(glvars.GAME_ID)  # identifie le jeu ds le système du ludo.store
        }
        res = self.serv.proxied_get(target, params)
        tmp = json.loads(res)
        if glvars.DEV_MODE:
            print('DEBUG:  appel sur tournois.php donne...')
            print(str(tmp))
        glvars.num_challenge = int(tmp[0])
        glvars.chall_seed = int(tmp[1])
        # - on paye le droit d'entrée et c'est parti
        params = {
            'fct': 'pay_due',
            'price': str(MenuModel.COUT_PARTIE),
            'cid': str(glvars.num_challenge),
            'id_perso': str(glvars.acc_id)
        }
        res = self.serv.proxied_get(target, params)
        tmp = json.loads(res)
        return tmp

    def _recup_solde_serveur(self):
        return 100
        if glvars.DEV_MODE:
            print('envoi serveur...')
        target = self.serv.get_gtm_app_url() + 'maj_solde.php'
        params = {
            'id_perso': glvars.acc_id,
            'updating': 0
        }
        res = self.serv.proxied_get(target, params)
        tmp = json.loads(res)
        if tmp is None:
            raise Exception('cannot retrieve players balance!')
        return int(tmp)

    def impacte_retour_login(self):
        if glvars.username:
            self.ref_mod.mark_auth_done(glvars.username, glvars.copie_solde)
            self.ref_view.refresh_graphic_state()

    # --------------------------------------
    #  Gestion des évènements
    # --------------------------------------
    def _validation_choix_opt(self):
        choix = self.ref_mod.get_curr_choice()
        print(' Le gars a choisi', choix)
        self.ref_view.validate_effect()  # play sfx
        self.nextmode_buffer = self.ref_mod.get_curr_choice()

    def proc_event(self, ev, source):
        if ev.type == EngineEvTypes.LOGICUPDATE:
            self.__handlelogic(ev)

        elif ev.type == MyEvTypes.DemandeTournoi:
            if self.ref_mod.can_bet() and self._procedure_debut_challenge():
                self.pev(EngineEvTypes.PUSHSTATE, state_ident=GameStates.Tetris)

        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_UP:
                self.ref_mod.move(-1)
            elif ev.key == pygame.K_DOWN:
                self.ref_mod.move(1)
            elif ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
                self._validation_choix_opt()

        elif ev.type == MyEvTypes.ChoixMenuValidation:  # SUITE A UN CLIC
            self._validation_choix_opt()


class MenuState(BaseGameState):
    def __init__(self, gs_id):
        super().__init__(gs_id)
        self.v = self.m = self.c = None
        self.der_lstate = None

    def enter(self):
        print('enter in Menu State')
        if self.m is None:
            self.m = MenuModel()
        self.v = MenuView(self.m)
        self.v.turn_on()
        if self.c is None:
            self.c = MenuCtrl(self.m, self.v)
            self.c.impacte_retour_login()
        self.c.turn_on()
        glvars_init_sound()

        glvars_playmusic()

    def resume(self):
        self.c.impacte_retour_login()
        self.v.turn_on()
        if self.der_lstate != (glvars.username is None):
            self.m.reset_choice()
        self.c.turn_on()

    def release(self):
        self.c.turn_off()
        self.v.turn_off()
        pygame.mixer.music.fadeout(750)
        while pygame.mixer.music.get_busy():
            pass
        if glvars.DEV_MODE:
            print('--- Sortie propre OK ---')

    def pause(self):
        self.der_lstate = (glvars.username is None)
        self.c.turn_off()
        self.v.turn_off()


class TetColor:
    CLEAR = "clear"
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    MAGENTA = "magenta"
    CYAN = "cyan"
    ORANGE = "orange"

    @staticmethod
    def colors():
        return (
            TetColor.RED,
            TetColor.BLUE,
            TetColor.GREEN,
            TetColor.YELLOW,
            TetColor.MAGENTA,
            TetColor.CYAN,
            TetColor.ORANGE
        )


class Piece:
    L_SHAPE = {"tiles": ((0, 0), (0, 1), (0, 2), (1, 2)),
               "x_adj": 1,
               "y_adj": 2,
               "color": TetColor.YELLOW}
    R_SHAPE = {"tiles": ((0, 0), (1, 0), (0, 1), (0, 2)),
               "x_adj": 1,
               "y_adj": 2,
               "color": TetColor.ORANGE}
    # carré
    # O_SHAPE = {"tiles": ((0, 0), (0, 1), (1, 0), (1, 1)),
    O_SHAPE = {"tiles": ((0, 0), (1, 0), (2, 1), (1, 2), (0, 2)),
               "x_adj": 2,  # 1,
               "y_adj": 2,  # 1,
               "color": TetColor.CYAN}
    T_SHAPE = {"tiles": ((0, 0), (1, 0), (1, 1), (2, 0)),
               "x_adj": 2,
               "y_adj": 1,
               "color": TetColor.MAGENTA}
    S_SHAPE = {"tiles": ((0, 0), (0, 1), (1, 1), (1, 2)),
               "x_adj": 1,
               "y_adj": 2,
               "color": TetColor.BLUE}
    Z_SHAPE = {"tiles": ((0, 0), (1, 0), (1, 1), (2, 1)),
               "x_adj": 2,
               "y_adj": 1,
               "color": TetColor.GREEN}
    I_SHAPE = {"tiles": ((0, 0), (1, 0), (2, 0), (3, 0)),
               "x_adj": 3,
               "y_adj": 0,
               "color": TetColor.RED}
    SHAPES = (L_SHAPE, R_SHAPE, O_SHAPE, T_SHAPE, S_SHAPE, Z_SHAPE, I_SHAPE)

    def __init__(self, x, y, shape, color, rot=0):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = color
        self.rotation = rot

    def move(self, x, y):
        self.x += x
        self.y += y

    def __iter__(self):
        for x_offset, y_offset in self.shape["tiles"]:
            if self.rotation == 0:
                yield self.x + x_offset, self.y + y_offset
            elif self.rotation == 1:
                yield (self.x - y_offset + self.shape["y_adj"],
                       self.y + x_offset)
            elif self.rotation == 2:
                yield (self.x - x_offset + self.shape["x_adj"],
                       self.y - y_offset + self.shape["y_adj"])
            elif self.rotation == 3:
                yield (self.x + y_offset,
                       self.y - x_offset + self.shape["x_adj"])

    def render(self, v):
        for x, y in self:
            v.render_tile(x, y, self.color)

    def rotate(self, clockwise=True):
        if clockwise:
            self.rotation = (self.rotation + 1) % 4
        else:
            self.rotation = (self.rotation - 1) % 4

    def rotated(self, clockwise=True):
        p = Piece(self.x, self.y, self.shape, self.color, self.rotation)
        p.rotate(clockwise)
        return p


class Board(kengi.event.CogObj):
    def __init__(self, n_columns, n_rows, autogen=True):
        super().__init__()
        self.height = n_rows
        self.width = n_columns
        self.columns = [self.height] * n_columns
        self.rand = random.Random()
        self.autogen = autogen
        self.level = self.piece = self.finalize_ready = None
        self.tiles = self.score = self.lines = self.game_over = None
        self.quake_effect = False
        self.reset()

    def reset(self):
        self.piece = None
        self.finalize_ready = False
        self.tiles = defaultdict(lambda: TetColor.CLEAR)
        self.score = 0
        self.level = 1
        self.lines = 0
        self.game_over = False

    def more_quake(self):
        tomba = False
        for y in range(self.height - 2, -1, -1):
            for x in range(0, self.width + 1):
                if not self.is_tile_empty(x, y):
                    c = self.tiles[(x, y)]
                    if self.is_tile_empty(x, y + 1):
                        self.set_tile_color(x, y, TetColor.CLEAR)
                        self.set_tile_color(x, y + 1, c)
                        tomba = True
            if tomba:
                self.pev(MyEvTypes.BlocksCrumble)
                return
        if not tomba:
            self.pev(MyEvTypes.FlatWorld)
            self.accu_score()

    def clear_tile(self, x, y):
        self.tiles[(x, y)] = TetColor.CLEAR
        # Move all the tiles above this row down one space
        for y_tile in range(y, self.columns[x] - 1, -1):
            self.tiles[(x, y_tile)] = self.tiles[(x, y_tile - 1)]
        # And reset the top of of the columns
        while (self.columns[x] < self.height and
               self.tiles[(x, self.columns[x])] == TetColor.CLEAR):
            self.columns[x] += 1

    def clear_row(self, row):
        for col in range(len(self.columns)):
            self.clear_tile(col, row)

    def row_full(self, row):
        for col in range(len(self.columns)):
            if self.tiles[(col, row)] == TetColor.CLEAR:
                return False
        return True

    def set_tile_color(self, x, y, color):
        # assert color != TetColor.CLEAR
        self.tiles[(x, y)] = color
        if color == TetColor.CLEAR:
            return
        if self.columns[x] > y:
            self.columns[x] = y

    def is_tile_empty(self, x, y):
        return self.tiles[(x, y)] == TetColor.CLEAR

    def piece_can_move(self, x_move, y_move):
        """Returns True if a piece can move, False otherwise."""
        assert self.piece is not None
        # for base_x, base_y in self.piece:
        #     x = x_move + base_x
        #     y = y_move + base_y
        #     if not 0 <= x < len(self.columns) or y >= self.columns[x]:
        #         return False
        for basex, basey in self.piece:
            x = basex + x_move
            y = basey + y_move
            if not (0 <= x < len(self.columns)):
                return False
            if y >= self.height:
                return False
            if not self.is_tile_empty(x, y):
                return False
        return True

    def drop_piece(self):
        """Either drops a piece down one level, or finalizes it and creates another piece."""
        if self.piece is not None:
            if self.piece_can_move(0, 1):
                self.piece.move(0, 1)
                self.finalize_ready = False
                return
            # piece cannot move down => has hit the bottom...
            if not self.finalize_ready:  # gives a short delay to move the piece, even if it has hit the bottom
                self.finalize_ready = True
            else:
                self.finalize_piece()
                self.generate_piece()

    def full_drop_piece(self):
        """Either drops a piece down one level, or finalizes it and creates another piece."""
        if self.piece is not None:
            while self.piece_can_move(0, 1):
                self.piece.move(0, 1)
            self.finalize_piece()
            self.generate_piece()

    def move_piece(self, x_move, y_move):
        """Move a piece some number of spaces in any direction"""
        if self.piece is not None:
            if self.piece_can_move(x_move, y_move):
                self.piece.move(x_move, y_move)

    def rotate_piece(self, clockwise=True):
        if self.piece is None:
            return
        if self.piece_can_rotate(clockwise):
            self.piece.rotate(clockwise)

    def piece_can_rotate(self, clockwise):
        """Returns True if a piece can drop, False otherwise."""
        p = self.piece.rotated(clockwise)
        for x, y in p:
            if not 0 <= x < len(self.columns) or y >= self.columns[x]:
                return False
        return True

    def generate_piece(self):
        """Creates a new piece at random and places it at the top of the board."""
        if self.game_over:
            return
        middle = len(self.columns) // 2
        shape = self.rand.choice(Piece.SHAPES)
        self.piece = Piece(middle - shape["x_adj"], 0, shape, shape["color"])
        if not self.piece_can_move(0, 0):
            # Show piece on the board
            self.finalize_piece()
            # And mark the game as over
            self.game_over = True
            self.piece = None
            self.pev(MyEvTypes.GameLost)

    def accu_score(self):
        old_level = self.level
        rows_cleared = 0
        for y in range(0, self.height + 1):
            if self.row_full(y):
                self.clear_row(y)
                rows_cleared += 1
        if rows_cleared:
            self.score += (rows_cleared * rows_cleared) * 10
            self.lines += rows_cleared
            self.level = 1 + (self.lines // 8)
            self.pev(MyEvTypes.LineDestroyed)
            if self.level != old_level:
                # pygame.event.post(pygame.event.Event(self.LEVELUP_EV_TYPE, level=self.level))
                self.pev(MyEvTypes.LevelUp, level=self.level)

    def finalize_piece(self):
        for x, y in self.piece:
            self.set_tile_color(x, y, self.piece.color)
        self.accu_score()
        self.piece = None

    def met_a_jour_vue(self, v):
        v.clear()
        v.set_size(len(self.columns), self.height)
        for (x, y), color in self.tiles.items():
            v.render_tile(x, y, color)
        if self.piece is not None:
            self.piece.render(v)
        v.set_score(self.score)
        v.set_level(self.level)


class TetrisCtrl(EventReceiver):
    def __init__(self, ref_mod, ref_view):
        super().__init__()
        self.boardmodel = ref_mod
        self.boardmodel.generate_piece()
        self.view = ref_view
        self.game_over = False
        # if view_type == TextView:
        #     def cls():
        #         os.system('cls')
        #     self.show_action = cls
        #     self.max_fps = 5
        # else:
        self.show_action = None
        self.max_fps = 50
        self.clock = pygame.time.Clock()
        self.__ready_to_exit = False

    @staticmethod
    def commit_score(valeur_score):
        return  # the commit has been disabled for now
        # envoir vers le SERVEUR
        serv = kengi.network.HttpServer.instance()
        url = serv.get_ludo_app_url() + 'tournois.php'
        params = {
            'fct': 'pushscore',
            'cid': str(glvars.num_challenge),
            'id_perso': str(glvars.acc_id),
            'name': str(glvars.username),
            'score': str(valeur_score)
        }
        if glvars.DEV_MODE:
            print('URL= {}'.format(url))
            print('params below:')
            print(str(params))
        res = serv.proxied_get(url, params)
        if glvars.DEV_MODE:
            print('commit server done [xxxxxxxxxxxxxxxxxxxxxxx]  ')
            print(str(res))

    def flag_games_over(self):
        self.game_over = True
        self.__ready_to_exit = False

    # ---------------------------------------
    #  GESTION EV. COREMON ENG.
    # ---------------------------------------
    def proc_event(self, ev, source):
        if ev.type == EngineEvTypes.PAINT:
            self.render_frame(ev.screen)
        elif ev.type == EngineEvTypes.LOGICUPDATE:
            if self.game_over:
                if not self.__ready_to_exit:
                    TetrisCtrl.commit_score(self.boardmodel.score)
                    self.__ready_to_exit = True
        elif ev.type == MyEvTypes.GameLost:
            self.flag_games_over()
            pygame.time.set_timer(MyEvTypes.Drop, 0)
            pygame.time.set_timer(MyEvTypes.Shake, 0)
            # kengi.get_manager().xtimer_set_timer(MyEvTypes.Drop, 0)
            # kengi.get_manager().xtimer_set_timer(MyEvTypes.Shake, 0)
        elif ev.type == pygame.KEYDOWN:
            self.key_handler(ev.key)
        # elif ev.type == self.DROP_EV:
        elif ev.type == MyEvTypes.Drop:
            self.boardmodel.drop_piece()
        # elif ev.type == self.SHAKE_EV:
        elif ev.type == MyEvTypes.Shake:
            self.boardmodel.more_quake()
        elif ev.type == MyEvTypes.FlatWorld:
            pygame.time.set_timer(MyEvTypes.Shake, 0)
            # kengi.get_manager().xtimer_set_timer(MyEvTypes.Shake, 0)
        elif ev.type == MyEvTypes.LevelUp:
            pygame.time.set_timer(MyEvTypes.Drop, TetrisCtrl.get_level_speed(ev.level))
            pygame.time.set_timer(MyEvTypes.Shake, 50)
            # kengi.get_manager().xtimer_set_timer(MyEvTypes.Drop, TetrisCtrl.get_level_speed(ev.level))
            # kengi.get_manager().xtimer_set_timer(MyEvTypes.Shake, 50)

    def key_handler(self, key):
        if key == pygame.K_ESCAPE:
            self.pev(EngineEvTypes.POPSTATE)
        elif key == pygame.K_LEFT:
            self.boardmodel.move_piece(-1, 0)
        elif key == pygame.K_RIGHT:
            self.boardmodel.move_piece(1, 0)
        elif key == pygame.K_UP:
            self.boardmodel.rotate_piece()
        elif key == pygame.K_DOWN:
            self.boardmodel.move_piece(0, 1)
        elif key == pygame.K_a:
            self.boardmodel.rotate_piece(clockwise=False)
        elif key == pygame.K_s:
            self.boardmodel.rotate_piece()
        elif key == pygame.K_SPACE:
            self.boardmodel.full_drop_piece()
        elif key == pygame.K_RETURN:
            if self.__ready_to_exit:
                self.pev(EngineEvTypes.POPSTATE)
            elif glvars.DEV_MODE:  # activation manuelle possible en dev...
                pygame.time.set_timer(MyEvTypes.Shake, 75)

    @staticmethod
    def get_level_speed(level):
        given_spd = {
            1: 1000,
            2: 750,
            3: 563,
            4: 422,
            5: 316,
            6: 237,
            7: 180,
            8: 170,
            9: 160
        }
        if level < 1:
            raise ValueError('level must be greater than 1')
        try:
            return given_spd[level]
        except KeyError:
            superlvl = level - 10
            delta = 50.0 / (1 + superlvl)
            return 100 + int(delta)

    def render_frame(self, ref_screen):
        self.boardmodel.met_a_jour_vue(self.view)  # TODO faire en sorte que vue tjr à jour
        # TODO faire en sorte que la vue se dessine tt seule (et pas quil faille que le ctrl lui dise quand le faire)
        if self.show_action is not None:
            self.show_action()
        self.view.draw_content(ref_screen)
        if self.game_over:
            self.view.show_game_over(ref_screen)

    @staticmethod
    def setup_ctrl():
        pygame.time.set_timer(MyEvTypes.Drop, TetrisCtrl.get_level_speed(1))
        # kengi.get_manager().xtimer_set_timer(MyEvTypes.Drop, TetrisCtrl.get_level_speed(1))


class TetrisView(EventReceiver):
    def proc_event(self, ev, source):
        if ev.type == MyEvTypes.LineDestroyed:
            glvars_playsfx(self.sfx_crumble)
        elif ev.type == MyEvTypes.BlocksCrumble:
            glvars_playsfx(self.sfx_explo)

    BOARD_BORDER_SIZE = 5
    SCORE_PADDING = 5
    BORDER_SIZE = 4
    BORDER_FADE = pygame.Color(50, 50, 50, 0)
    COLOR_MAP = dict()  # init in constructor

    def __init__(self, scr_size, bgcolor, fgcolor):
        super().__init__()
        # - couleurs C64
        new_palette = {
            TetColor.CLEAR: glvars.colors['c_lightpurple'],
            TetColor.RED: glvars.colors['c_skin'],
            TetColor.BLUE: glvars.colors['c_brown'],
            TetColor.GREEN: glvars.colors['c_leafgreen'],
            TetColor.YELLOW: glvars.colors['c_sunny'],
            TetColor.MAGENTA: glvars.colors['c_cherokee'],
            TetColor.CYAN: glvars.colors['c_oceanblue'],
            TetColor.ORANGE: glvars.colors['c_gray2']
        }
        self.COLOR_MAP.update(new_palette)
        # - base
        self.rows = []
        self.width = 0
        self.height = 0
        # - ext
        self.view_width, self.view_height = scr_size
        self.box_size = 10
        self.padding = (0, 0)
        self.go_font = glvars.fonts['moderne_big']
        self.sc_font = glvars.fonts['sm_monopx']
        self.font_color = fgcolor
        self.bgcolor = bgcolor
        self.score = None
        self.level = None
        self.__fond_gameover = None
        self.__label_gameover = None

        # sons
        self.sfx_explo = pygame.mixer.Sound(ASSET_ALIASES['explo'])
        self.sfx_crumble = pygame.mixer.Sound(ASSET_ALIASES['quake'])

    def clear(self):
        self.rows = [[TetColor.CLEAR] * self.width for _ in range(self.height)]

    def render_tile(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.rows[y][x] = color

    # Public interface to views
    def set_size(self, cols, rows):
        self.width = cols
        self.height = rows
        self.clear()
        self.calc_dimensions()

    def set_score(self, score):
        self.score = score

    def set_level(self, level):
        self.level = level

    def draw_content(self, screen):
        screen.fill(self.bgcolor)
        self.draw_board(screen)
        self.show_score(screen)

    def show_score(self, ecran):
        score_height = 0
        if self.score is not None:
            score_surf = self.sc_font.render("{:06d}".format(self.score), True, self.font_color)
            ecran.blit(score_surf, (self.BOARD_BORDER_SIZE, self.BOARD_BORDER_SIZE))
            score_height = score_surf.get_height()
        if self.level is not None:
            level_surf = self.sc_font.render("Niveau {:02d}".format(self.level), True, self.font_color)
            level_pos = (self.BOARD_BORDER_SIZE,
                         self.BOARD_BORDER_SIZE + score_height + self.SCORE_PADDING)
            ecran.blit(level_surf, level_pos)

    def show_game_over(self, ecran):
        # -- affiche simili -popup
        if not self.__fond_gameover:
            self.__fond_gameover = pygame.image.load(ASSET_ALIASES['fond_gameover'])
        targetp = [self.view_width // 2, self.view_height // 2]
        targetp[0] -= self.__fond_gameover.get_size()[0] // 2
        targetp[1] -= self.__fond_gameover.get_size()[1] // 2
        ecran.blit(self.__fond_gameover, targetp)
        # -- affiche msg
        if not self.__label_gameover:
            self.__label_gameover = self.go_font.render("Jeu termine, ENTREE pr sortir", False, self.font_color)
        r = self.__label_gameover.get_rect()
        targetpos = (
            (self.view_width // 2) - (r.width // 2),
            (self.view_height // 2) - (r.height // 2)
        )
        ecran.blit(self.__label_gameover, targetpos)

    # -- Helper methods
    def get_score_size(self):
        (sw, sh) = self.sc_font.size("000000")
        (lw, lh) = self.sc_font.size("LEVEL 00")
        return max(sw, lw) + self.BOARD_BORDER_SIZE, sh + lh + self.SCORE_PADDING

    def calc_dimensions(self):
        horiz_size = (self.view_width - (self.BOARD_BORDER_SIZE * 2)) // self.width
        vert_size = (self.view_height - (self.BOARD_BORDER_SIZE * 2)) // self.height
        if vert_size > horiz_size:
            self.box_size = horiz_size
            self.padding = (self.get_score_size()[0] * 2,
                            (self.view_height
                             - self.BOARD_BORDER_SIZE
                             - (self.height * horiz_size)))
        else:
            self.box_size = vert_size
            left_padding = max(self.get_score_size()[0] * 2,
                               (self.view_width
                                - self.BOARD_BORDER_SIZE
                                - (self.width * vert_size)))
            self.padding = (left_padding, 0)
        global _print_dim
        if _print_dim:
            print(self.width, self.height)
            print(self.view_width, self.view_height)
            print(horiz_size, vert_size)
            print(self.box_size)
            print(self.padding)
            _print_dim = True

    def draw_board(self, ecran):
        board_color = self.COLOR_MAP[TetColor.CLEAR]
        x_start = self.BOARD_BORDER_SIZE + (self.padding[1] // 2)
        y_start = self.BOARD_BORDER_SIZE + (self.padding[0] // 2)
        x, y = x_start, y_start
        board_rect = (y, x, self.width * self.box_size, self.height * self.box_size)
        pygame.draw.rect(ecran, board_color, board_rect)
        for col in self.rows:
            for item in col:
                self.draw_box(ecran, x, y, item)
                y += self.box_size
            x += self.box_size
            y = y_start

    def draw_box(self, ecran, x, y, color):
        if color == TetColor.CLEAR:
            return
        pg_color = self.COLOR_MAP[color]
        bd_size = self.BORDER_SIZE
        # print( ' ~ k~k ~~_~')
        # print(str(pg_color))
        # print(str(self.BORDER_FADE))
        bd_color = pg_color - self.BORDER_FADE
        # print(str(bd_color))
        outer_rect = (y, x, self.box_size, self.box_size)
        inner_rect = (y + bd_size, x + bd_size,
                      self.box_size - bd_size * 2, self.box_size - bd_size * 2)
        pygame.draw.rect(ecran, bd_color, outer_rect)
        pygame.draw.rect(ecran, pg_color, inner_rect)


class TetrisState(BaseGameState):
    def __init__(self, state_ident):
        super().__init__(state_ident)
        self._ctrl = None
        self.ma_vue = None

    def enter(self):
        damod = Board(10, 20)
        damod.rand.seed(glvars.chall_seed)
        da_cfonts = {}
        if pygame.font.get_init():
            # before :
            # da_cfonts["game_over"] = pygame.font.SysFont("ni7seg", 60)
            # da_cfonts["score"] = pygame.font.SysFont("ni7seg", 18)
            # TODO fix this temp patch for web ctx
            da_cfonts["game_over"] = pygame.font.Font(None, 66)
            da_cfonts["score"] = pygame.font.Font(None, 18)

        # - view creation
        self.ma_vue = TetrisView(
            (SCR_W,SCR_H), glvars.colors['c_purple'], glvars.colors['c_lightpurple']
        )
        self.ma_vue.turn_on()
        # - ctrl
        self._ctrl = TetrisCtrl(damod, self.ma_vue)
        # -launch
        TetrisCtrl.setup_ctrl()
        self._ctrl.turn_on()

    def release(self):
        self._ctrl.turn_off()
        self.ma_vue.turn_off()


def init_repo_strings(lang):
    global _str_repo, Labels
    # ---------------------------
    #  Version anglaise
    # ---------------------------
    if lang == 'en':
        _str_repo[Labels.PoidsTotal] = 'TOTAL WEIGHT'
        _str_repo[Labels.UtiliteTotale] = 'UTILITY'
        _str_repo[Labels.Minage1] = 'Donating hashpower to the ludo.store'
        _str_repo[Labels.Minage2] = 'Please wait for a short moment...'
        _str_repo[Labels.NomJoueurAnonyme] = 'Guest'
        _str_repo[Labels.SensLogin] = 'Please identify yourself'
        _str_repo[Labels.CanCreateAcc] = "No account yet? Sign up via http://ludo.store"
        _str_repo[Labels.InciteLudoStore] = "It's easy, fast and 100% free!"
        _str_repo[Labels.Utilisateur] = 'User'
        _str_repo[Labels.Invite] = 'Guest'
        _str_repo[Labels.Solde] = 'Balance'
        _str_repo[Labels.OpenBrowser] = 'Open in default browser'
        _str_repo[Labels.WindowCaption] = 'Bag&Win: the game'
        _str_repo[Labels.Connexion] = 'Do login'
        _str_repo[Labels.MenuGridGame] = 'Easy mode'
        _str_repo[Labels.MenuDefi] = 'Take the challenge'
        _str_repo[Labels.MenuTuto] = 'Tutorial'
        _str_repo[Labels.MenuEntrainement] = 'Training'
        _str_repo[Labels.MenuQuitter] = 'Quit'
        _str_repo[Labels.NoTraining] = 'Training mode\'s unavailable in this prototype. ESC to go back to the menu'
        _str_repo[Labels.CompteRequis] = 'You need to login first'
        _str_repo[Labels.CoutDefi] = 'costs 10 mGold per try'
        _str_repo[Labels.RetourArr] = 'Go back'
        _str_repo[Labels.CannotLogin] = "ERROR: Credentials are not accepted by the server!"
        _str_repo[Labels.WordLogin] = 'ACCOUNT NAME-'
        _str_repo[Labels.WordPassword] = 'PASSWORD-'
        _str_repo[Labels.EndEasyWin] = 'Congratulations! You win'
        _str_repo[Labels.EndEasyLoose] = 'Game over! You loose'
        _str_repo[Labels.EndChallenge1] = 'Time elapsed'
        _str_repo[Labels.EndGameAction] = "Press [ENTER] to go back to the menu"
        return
    # ---------------------------
    #  Version française
    # ---------------------------
    _str_repo[Labels.PoidsTotal] = 'POIDS TOTAL'
    _str_repo[Labels.UtiliteTotale] = 'UTILITE'
    _str_repo[Labels.Minage1] = 'Contribution ludo.store'
    _str_repo[Labels.Minage2] = 'Veuillez patienter durant le minage...'
    _str_repo[Labels.NomJoueurAnonyme] = 'Invite(e)'
    _str_repo[Labels.SensLogin] = 'Selection du compte-joueur'
    _str_repo[Labels.CanCreateAcc] = "Si besoin de creer compte: http://ludo.store"
    _str_repo[Labels.InciteLudoStore] = "Facile, rapide, 100% gratuit!"
    _str_repo[Labels.Utilisateur] = 'Profil'
    _str_repo[Labels.Invite] = 'Invite'
    _str_repo[Labels.Solde] = 'Solde'
    _str_repo[Labels.OpenBrowser] = 'Ouvrir dans votre navigateur'
    _str_repo[Labels.WindowCaption] = 'Bag&Win: le jeu'
    _str_repo[Labels.Connexion] = 'S\'authentifier'
    _str_repo[Labels.MenuDefi] = 'Jouer en tournoi'
    _str_repo[Labels.MenuGridGame] = 'Mode facile'
    _str_repo[Labels.MenuTuto] = 'Tutoriel'
    _str_repo[Labels.MenuEntrainement] = 'Entrainement'
    _str_repo[Labels.MenuQuitter] = 'Quitter'
    _str_repo[Labels.NoTraining] = 'mode Entrainement indisponible dans cette maquette. ESC pour revenir au menu'
    _str_repo[Labels.CompteRequis] = 'Il te faut un compte'
    _str_repo[Labels.CoutDefi] = 'coute 10 mGold par essai'
    _str_repo[Labels.RetourArr] = 'Retour arriere'
    _str_repo[Labels.CannotLogin] = 'ERREUR: Identifiants refuses par le serveur!'
    _str_repo[Labels.WordLogin] = 'NOM COMPTE-'
    _str_repo[Labels.WordPassword] = 'MOT DE PASSE-'
    _str_repo[Labels.EndEasyWin] = 'Bravo! Vous gagnez'
    _str_repo[Labels.EndEasyLoose] = 'Game over! Vous perdez'
    _str_repo[Labels.EndChallenge1] = 'Temps ecoule'
    _str_repo[Labels.EndGameAction] = "Pressez [ENTREE] pour revenir au menu"


def tsl(cle):
    global _str_repo
    return _str_repo[cle]


if __name__ == "__main__":
    kengi.init(1)
    SCR_W, SCR_H = kengi.get_surface().get_size()

    glvars.CHOSEN_LANG = 'en'
    init_repo_strings(glvars.CHOSEN_LANG)
    glvars_init_fonts_n_colors()

    kengi.declare_states(
        GameStates,
        {
            # disable login/auth
            # -1: katasdk.bios.KataFrameState,
            GameStates.Menu: MenuState,
            GameStates.Tetris: TetrisState
        },
        glvars
    )
    game_ctrl = kengi.get_game_ctrl()

    # start game
    game_ctrl.turn_on()
    game_ctrl.loop()

    # clean exit
    pygame.mixer.stop()
    kengi.quit()
