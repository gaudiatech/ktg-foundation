import random
import katagames_sdk as katasdk
katasdk.bootstrap()
kengi = katasdk.kengi
pygame = kengi.pygame
EngineEvTypes = kengi.event.EngineEvTypes


NEXT_GAMETAG = 'niobepolis'
W, H = 960 // 2, 540 // 2
carres = list()
assoc_obj_position = dict()
dragging = None
movables = set()
SQ_SIZE = 45
extrablit = False


def gen_carres():
    global carres, assoc_obj_position, movables, dragging, extrablit
    dragging = None
    col_a = pygame.colordict.THECOLORS['steelblue']
    col_b = pygame.colordict.THECOLORS['orange']
    omega_color_names = ['salmon', 'yellow', 'maroon4', 'lightsteelblue3', 'darkred', 'plum', 'paleturquoise']
    assoc_obj_position.clear()

    carres = [pygame.Surface((SQ_SIZE, SQ_SIZE)) for _ in range(16)]
    movables.clear()
    for elt in carres:
        elt.fill(pygame.color.THECOLORS[random.choice(omega_color_names)])

        if random.random() < 0.77:
            if random.random() < 0.5:
                pygame.draw.rect(elt, col_a, ((3, 5), (33, 15)), 0)
                if extrablit:
                    tmptmp = pygame.surface.Surface((8, 60))
                    tmptmp.fill('darkgray')
                    elt.blit(tmptmp, (7 + random.randint(3, 8), random.randint(28, 35)))
                movables.add(elt)
            else:
                pygame.draw.circle(elt, col_b, (SQ_SIZE // 2, SQ_SIZE // 2), 21, 7)

        assoc_obj_position[elt] = (random.random() * (W - 64), random.random() * (H - 64))
    print('create squares ->done! ')


class SharedGstate:
    def __init__(self):
        self.gameover = False
        self.circles = list()
        self.circles2 = list()
        self.screen = kengi.get_surface()
        self.clock = pygame.time.Clock()


gstate = None


# ----------------------- functions that manage the game --------------
def game_enter(vm_state):
    global gstate
    katasdk.set_mode('old_school')
    gstate = SharedGstate()


def handle_event(ev_obj, shared_st):
    if ev_obj.type == pygame.QUIT:
        shared_st.gameover = True

    elif ev_obj.type == pygame.KEYDOWN:
        if ev_obj.key == pygame.K_BACKSPACE:
            del shared_st.circles[:]
            del shared_st.circles2[:]
        elif ev_obj.key == pygame.K_ESCAPE:
            shared_st.gameover = True

    elif ev_obj.type == pygame.MOUSEBUTTONDOWN:
        print(ev_obj.pos, ev_obj.button, ' PRESS')
        shared_st.circles.append(
            kengi.core.proj_to_vscreen(ev_obj.pos)
        )

    elif ev_obj.type == pygame.MOUSEBUTTONUP:
        print(ev_obj.pos, ev_obj.button)
        shared_st.circles2.append(
            kengi.core.proj_to_vscreen(ev_obj.pos)
        )


def game_update(infot=None):
    global gstate
    for ev in pygame.event.get():
        handle_event(ev, gstate)
    if gstate.gameover:
        return [2, NEXT_GAMETAG]

    # draw the bg
    gstate.screen.fill((77, 70, 180))

    for elt in gstate.circles:
        pygame.draw.circle(gstate.screen, 'red', elt, 8)
    for elt in gstate.circles2:
        pygame.draw.circle(gstate.screen, 'pink', elt, 13)
    kengi.flip()


def game_exit(vm_state=None):
    kengi.quit()


# --------------------------------------------
#  Entry pt, local ctx
# --------------------------------------------
if __name__ == '__main__':
    game_enter(katasdk.vmstate)
    while not gstate.gameover:
        uresult = game_update(None)
        if uresult is not None:
            if 0 < uresult[0] < 3:
                gameover = True
    game_exit(katasdk.vmstate)
