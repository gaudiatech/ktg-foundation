import math
import random
import time
import katagames_sdk as katasdk
kengi = katasdk.bootstrap('old_school')

# ---------------------------

#  not a real game, this is used for debug/test purpose
#  as it can tell whether
#  the Niobe-polis WebApp works properly or not...

# ---------------------------
FROM_ARCHIVE = '__BRYTHON__' in globals()

NEXT_GAME_LOADED = 'niobepolis'  # 'main1'


pygame = kengi.pygame
CogObject = kengi.event.CogObj
EventReceiver = kengi.event.EventReceiver
EngineEvTypes = kengi.event.EngineEvTypes
SCR_SIZE = [0, 0]
NB_ROCKS = 3
bullets = list()
FG_COLOR = (119, 255, 0)
music_snd = None
view = ctrl = None
Vector2 = pygame.math.Vector2
MyEvTypes = kengi.event.enum_ev_types(
    'PlayerChanges',  # contains: new_pos, angle
)
update_func_sig = None
lu_event = p_event = None
clockk = pygame.time.Clock()
CgmEvent = kengi.event.CgmEvent
e_manager = None


def img_load(img_name):
##    global bundle_ptr
##    if FROM_ARCHIVE:
##        bytes_io = assets_datatable[img_name]
##        surface = pygame.image.load(bytes_io)
##        return surface
    return pygame.image.load(img_name)


def snd_load(path):
##    global bundle_ptr
##    if FROM_ARCHIVE:
##        bytes_io = assets_datatable[path]
##        snd = pygame.mixer.Sound(bytes_io)
##        return snd
    return pygame.mixer.Sound(path)


def deg(radvalue):
    return radvalue * (180 / math.pi)


class RockSprite(pygame.sprite.Sprite):
    snd = None

    def __init__(self):
        super().__init__()
        if self.__class__.snd:
            pass
        else:
            self.__class__.snd = snd_load('astero/myassets/explosion_002.wav')
            self.__class__.snd.set_volume(0.66)
        self.image = img_load('astero/myassets/rock.png')
        self.image.set_colorkey((0xff, 0, 0xff))
        pos = [random.randint(0, SCR_SIZE[0] - 1), random.randint(0, SCR_SIZE[1] - 1)]
        self.rect = self.image.get_rect()
        self.rect.topleft = pos
        self.vx = random.choice((1, -1)) * random.randint(1, 3)
        self.vy = random.choice((1, -1)) * random.randint(1, 3)
        self.cpt = 1
        self.zombie = False
        self.immunity = 0

    def destroyed(self):
        self.__class__.snd.play(0)

    def update(self):
        if self.immunity:
            self.immunity -= 1
        if self.cpt == 0:
            x, y = self.rect.topleft
            x += self.vx
            y += self.vy
            self.rect.topleft = x, y
            if self.rect.left >= SCR_SIZE[0]:
                self.rect.right = 0
            elif self.rect.right < 0:
                self.rect.left = SCR_SIZE[0] - 2
            if self.rect.top >= SCR_SIZE[1]:
                self.rect.bottom = 0
            elif self.rect.bottom < 0:
                self.rect.top = SCR_SIZE[1] - 2
        self.cpt = (self.cpt + 1) % 3

    def inv_speed(self):
        self.immunity = 128
        self.vx *= -1
        self.vy *= -1


class ShipModel(CogObject):
    DASH_DISTANCE = 55
    DELTA_ANGLE = 0.04
    SPEED_CAP = 192

    def __init__(self):
        super().__init__()
        self.scr_size = kengi.core.get_screen().get_size()
        rand_pos = (random.randint(0, self.scr_size[0] - 1), random.randint(0, self.scr_size[1] - 1))
        self._position = Vector2(*rand_pos)
        self._angle = 0
        self._speed = Vector2()

    @property
    def pos(self):
        return self._position

    def _commit_new_pos(self):
        tmpsize = self.scr_size
        if self._position.x < 0:
            self._position.x += tmpsize[0]
        elif self._position.x >= tmpsize[0]:
            self._position.x -= tmpsize[0]
        if self._position.y < 0:
            self._position.y += tmpsize[1]
        elif self._position.y >= tmpsize[1]:
            self._position.y -= tmpsize[1]
        self.pev(MyEvTypes.PlayerChanges, new_pos=self._position, angle=self._angle)

    def _update_speed_vect(self):
        lg = self._speed.length()
        self._speed = Vector2()
        self._speed.from_polar((lg, deg(self._angle)))

    def ccw_rotate(self):
        self._angle -= self.__class__.DELTA_ANGLE
        self._update_speed_vect()

    def cw_rotate(self):
        self._angle += self.__class__.DELTA_ANGLE
        self._update_speed_vect()

    def get_orientation(self):
        return self._angle

    def accel(self):
        if self._speed.length() == 0:
            self._speed = Vector2()
            self._speed.from_polar((5, deg(self._angle)))
        else:
            speedv_now = self._speed.length()
            speedv_now += 1
            if speedv_now > self.SPEED_CAP:
                speedv_now = self.SPEED_CAP
            self._speed = Vector2()
            self._speed.from_polar((speedv_now, deg(self._angle)))

    def brake(self):
        speedv_now = self._speed.length()
        speedv_now = speedv_now * 0.96
        if speedv_now < 5:
            self._speed = Vector2()
        else:
            self._speed = Vector2()
            self._speed.from_polar((speedv_now, deg(self._angle)))

    def shoot(self):
        sh_pos = Vector2(self._position)
        b_speed = Vector2()
        b_speed.from_polar((3, deg(self._angle)))
        return sh_pos, b_speed

    def get_position(self):
        return self._position

    def get_scr_pos(self):
        return int(self._position.x), int(self._position.y)

    def set_position(self, new_pos):
        self._position.x, self._position.y = new_pos
        self._commit_new_pos()

    def update(self, temps_passe):
        self._position.x += temps_passe * self._speed.x
        self._position.y += temps_passe * self._speed.y
        self._commit_new_pos()

    def dash(self):
        tmp = Vector2()
        tmp.from_polar((self.DASH_DISTANCE, deg(self._angle)))
        self._position += tmp
        self._commit_new_pos()

    def reset(self):
        initpos = (SCR_SIZE[0] // 2, SCR_SIZE[1] // 2)
        self._position = Vector2(*initpos)
        self._angle = 0
        self._speed = Vector2()


class ShipCtrl(EventReceiver):
    def __init__(self, ref_mod, rocksm):
        super().__init__()
        self._ref_ship = ref_mod
        self._ref_rocks = rocksm
        self.last_tick = None

    def proc_event(self, ev, source):
        global update_func_sig, music_snd
        if ev.type == EngineEvTypes.LOGICUPDATE:
            ba = pygame.key.get_pressed()
            if ba[pygame.K_UP]:
                self._ref_ship.accel()
            if ba[pygame.K_DOWN]:
                self._ref_ship.brake()
            if ba[pygame.K_RIGHT]:
                self._ref_ship.cw_rotate()
            if ba[pygame.K_LEFT]:
                self._ref_ship.ccw_rotate()
            if self.last_tick:
                tmp = ev.curr_t - self.last_tick
            else:
                tmp = 0
            self.last_tick = ev.curr_t
            self._ref_ship.update(tmp)

            if len(self._ref_rocks) == 0:
                # clean de-pop game
                music_snd.stop()
                kengi.event.EventManager.instance().hard_reset()
                update_func_sig = [2, NEXT_GAME_LOADED]
                # FOR THE 1ST arg:
                # 2 means: go load another game (next arg is gametag)
                # 1 means: stop anim (next arg can be anythin)
                return update_func_sig

            for b in bullets:
                b[0].x += b[1].x
                b[0].y += b[1].y
            remove = set()
            rb = set()
            for elt in self._ref_rocks:
                for idx, b in enumerate(bullets):
                    if elt.rect.collidepoint((b[0].x, b[0].y)):
                        remove.add(elt)
                        elt.zombie = True
                        rb.add(idx)
                        break
                if not elt.zombie and not elt.immunity:
                    if elt.rect.collidepoint(self._ref_ship.pos):
                        elt.inv_speed()
                        self._ref_ship.reset()
                elt.update()
            if len(remove):
                for tmp in remove:
                    tmp.destroyed()
                    self._ref_rocks.remove(tmp)
                rbplus = list(rb)
                rbplus.sort(reverse=True)
                while len(rbplus) > 0:
                    del bullets[rbplus.pop()]
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_SPACE:
                bullets.append(self._ref_ship.shoot())


class TinyWorldView(EventReceiver):
    BG_COLOR = (0, 25, 0)
    RAD = 5
    LINE_COLOR = (119, 255, 0)

    def __init__(self, ref_mod, rocksm):
        super().__init__()
        self.curr_pos = ref_mod.get_scr_pos()
        self.curr_angle = ref_mod.get_orientation()
        self.ref_rocksm = rocksm

    def proc_event(self, ev, source):
        if ev.type == EngineEvTypes.PAINT:
            ev.screen.fill(self.BG_COLOR)
            for rock_spr in self.ref_rocksm:
                ev.screen.blit(rock_spr.image, rock_spr.rect.topleft)
            for b in bullets:
                pygame.draw.circle(ev.screen, FG_COLOR, (b[0].x, b[0].y), 3, 0)

            self._draw_player(ev.screen)

        elif ev.type == MyEvTypes.PlayerChanges:
            self.curr_angle = ev.angle
            self.curr_pos = ev.new_pos.x, ev.new_pos.y

    def _draw_rocks(self, refscreen):
        for rockinfo in self.ref_rocksm:
            pos = rockinfo.rect.topleft
            pygame.draw.circle(refscreen, self.LINE_COLOR, pos, 25, 2)

    def _draw_player(self, surf):
        orientation = -self.curr_angle
        pt_central = self.curr_pos
        a, b, c = Vector2(), Vector2(), Vector2()
        a.from_polar((1, deg(orientation - (2.0 * math.pi / 3))))
        b.from_polar((1, deg(orientation)))
        c.from_polar((1, deg(orientation + (2.0 * math.pi / 3))))
        a.y *= -1
        b.y *= -1
        c.y *= -1
        temp = [a, b, c]
        temp[0] *= self.RAD * 1.2
        temp[1] *= 3 * self.RAD
        temp[2] *= 1.2 * self.RAD
        pt_li = [Vector2(*pt_central),
                 Vector2(*pt_central),
                 Vector2(*pt_central)]
        for i in range(3):
            pt_li[i] += temp[i]
        for pt in pt_li:
            pt.x = round(pt.x)
            pt.y = round(pt.y)
        pt_li.reverse()
        pygame.draw.polygon(surf, self.LINE_COLOR, pt_li, 2)


def print_mini_tutorial():
    howto_infos = """HOW TO PLAY:
    * use arrows to move
    * use SPACE to shoot"""
    print('-' * 32)
    for line in howto_infos.split('\n'):
        print(line)
    print('-' * 32)


gameover = False


class IntroV(EventReceiver):
    def __init__(self):
        super().__init__()
        self.img = img_load('astero/myassets/enter_start.png')
        self.dim = self.img.get_size()
        self.painting = True

    def proc_event(self, ev, source):
        global view, ctrl, music_snd, gameover

        if self.painting:
            if ev.type == EngineEvTypes.PAINT:
                ev.screen.fill((0, 0, 0))
                ev.screen.blit(self.img, ((SCR_SIZE[0] - self.dim[0]) // 2, (SCR_SIZE[1] - self.dim[1]) // 2))

            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                self.painting = False
                print_mini_tutorial()
                pygame.mixer.init()
                music_snd = snd_load('astero/myassets/ndimensions-zik.ogg')
                music_snd.set_volume(0.25)
                music_snd.play(-1)

        if ev.type == pygame.QUIT:
            gameover = True


def game_enter(vmstate=None):
    global SCR_SIZE, view, ctrl, lu_event, p_event, e_manager

    e_manager = kengi.event.EventManager.instance()
    SCR_SIZE = kengi.core.get_screen().get_size()
    introv = IntroV()
    shipm = ShipModel()
    li = [RockSprite() for _ in range(NB_ROCKS)]
    view = TinyWorldView(shipm, li)
    ctrl = ShipCtrl(shipm, li)
    view.turn_on()
    ctrl.turn_on()
    introv.turn_on()
    game_ctrl = kengi.core.get_game_ctrl()
    game_ctrl.turn_on()
    lu_event = CgmEvent(EngineEvTypes.LOGICUPDATE, curr_t=None)
    p_event = CgmEvent(EngineEvTypes.PAINT, screen=kengi.core.get_screen())


def game_update(t_info=None):
    global lu_event, p_event, clockk, gameover, update_func_sig
    if t_info:
        lu_event.curr_t = t_info
    else:
        lu_event.curr_t = time.time()
    e_manager.post(lu_event)
    e_manager.post(p_event)
    e_manager.update()
    clockk.tick(60)  # doit faire kedal en web ctx
    if gameover:
        return [1, None]
    elif update_func_sig is not None:
        print('__________retour', update_func_sig)
        return update_func_sig
    kengi.flip()
    

def game_exit(vmstate=None):
    kengi.quit()
    if vmstate:
        print('sess_token registered!')
        vmstate.sess_token = 'J.C. Van Damme'
    print('asteroids2 demo.. OUT')


# -------------- utilisation sans vm ---------------{debut}
if __name__=='__main__':
    gameover = False
    game_enter()
    while not gameover:
        tmp = game_update(None)
        if tmp is not None:
            if tmp[0] == 1 or tmp[0] == 2:
                gameover = True
    game_exit()
# -------------- utilisation sans vm ---------------{fin}