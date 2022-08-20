
disp_save_ico = None  # contains info 'bout time when it needs display
dump_content = None
kartridge_output = None
screen = None
file_label = None  # for showing what is being edited

# - constants
MFPS = 50
SAVE_ICO_LIFEDUR = 1.33  # sec

# constant to have smth just like "lorem ipsum" text, if needed
DUMMY_PYCODE = """# Define the cloud object by extending pygame.sprite.Sprite
# Use an image for a better-looking sprite
class Cloud(pygame.sprite.Sprite):
    def __init__(self):
        super(Cloud, self).__init__()
        self.surf = pygame.image.load("cloud.png").convert()
        self.surf.set_colorkey((0, 0, 0), RLEACCEL)
        # The starting position is randomly generated
        self.rect = self.surf.get_rect(
            center=(
                random.randint(SCREEN_WIDTH + 20, SCREEN_WIDTH + 100),
                random.randint(0, SCREEN_HEIGHT),
            )
        )
    # Move the cloud based on a constant speed
    # Remove the cloud when it passes the left edge of the screen
    def update(self):
        self.rect.move_ip(-5, 0)
        if self.rect.right < 0:
            self.kill()
# >>>megaman.py
for i in range(3, 112):
    for j in range(9, 88):
        print('..', i*j, end='')
# this is a random comment
print('hi mom')
# >>>kappa.py
x = input('hi bro, name? ')
# this is crazy!
print(f"homie {x}")
# >>>alpha.py
print('hello')
"""

FOLDER_CART = 'cartridges'
