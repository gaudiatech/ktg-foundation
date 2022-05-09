import katagames_sdk as katasdk
import random
katasdk.bootstrap()


# COOL FACT:
# this demo barely uses the sdk, its mostly kengi features


kengi = katasdk.kengi
NEXT_GAMETAG = 'niobepolis'
pygame = kengi.pygame
EngineEvTypes = kengi.event.EngineEvTypes
print("welcome!\nPress space to regen squares, mouse to drag n drop some of em")
clock = screen = None
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


def game_enter(vm_state=None):
    global screen, clock
    katasdk.set_mode('old_school')
    clock = pygame.time.Clock()
    screen = kengi.get_surface()
    gen_carres()


def procevent(ev_obj):
    global dragging, carres, assoc_obj_position, extrablit

    if ev_obj.type == pygame.QUIT:
        return [1, None]

    elif ev_obj.type == pygame.MOUSEBUTTONDOWN:
        for elt in carres:
            if elt in assoc_obj_position:
                p = assoc_obj_position[elt]
                if elt in movables:
                    mx, my = kengi.core.proj_to_vscreen(ev_obj.pos)
                    if p[0] < mx < p[0] + SQ_SIZE:
                        if p[1] < my < p[1] + SQ_SIZE:
                            # click
                            dragging = elt
                            break
    elif ev_obj.type == pygame.MOUSEBUTTONUP:
        dragging = None
    elif ev_obj.type == pygame.MOUSEMOTION:
        if dragging:
            mx, my = kengi.core.proj_to_vscreen(ev_obj.pos)
            assoc_obj_position[dragging] = (mx - SQ_SIZE // 2, my - SQ_SIZE // 2)

    elif ev_obj.type == pygame.KEYDOWN:

        if ev_obj.key == pygame.K_SPACE:
            gen_carres()
            print('*REGEN*')
        elif ev_obj.key == pygame.K_BACKSPACE:
            extrablit = not extrablit
            print('switch extrablit, its ' + ('on' if extrablit else 'off'))
        elif ev_obj.key == pygame.K_RETURN:
            print(' - ENTER PRESSED - ')
            return [2, NEXT_GAMETAG]


def game_update(infot=None):
    global screen

    for ev in pygame.event.get():
        tmpr = procevent(ev)
        if tmpr is not None:
            return tmpr

    # draw the bg
    screen.fill((77, 122, 80))

    for elt in carres:
        screen.blit(elt, assoc_obj_position[elt])
    kengi.flip()


def game_exit(vm_state=None):
    kengi.quit()
    print('drag n drop squares demo is GONE ..........')




# -------------- ex utilisation sans vm ---------------{debut}
if __name__ == '__main__':
    gameover = False
    game_enter()
    while not gameover:
        tmp = game_update(None)
        if tmp is not None:
            if tmp[0] == 1 or tmp[0] == 2:
                gameover = True
    game_exit()
# -------------- ex utilisation sans vm ---------------{fin}
