from abc import abstractmethod, ABCMeta
import os


class AbstractScProvider(metaclass=ABCMeta):
    @abstractmethod
    def get_source_code(self):
        raise NotImplementedError

    @abstractmethod
    def update_data_source(self, all_lines):
        raise NotImplementedError


class LocalSourceProvider(AbstractScProvider):
    def __init__(self, basecode):
        self.content = basecode

    def get_source_code(self):
        return self.content

    def update_data_source(self, all_lines):
        pass


# there are 4 (FOUR) possibilities:
# game-template x (DISK v Server) ; existing code x (DISK v Server)
class ScProviderFactory:
    # you can replace values manually if needed, before using the factory cls
    LOCAL_DATA_SRC = 'cartridges'

    REMOTE_DATA_SRC = ''

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

    def __init__(self):
        raise NotImplementedError

    @classmethod
    def build(cls, **kwargs):
        # depending on kwargs we'll use a game-template with target,
        if 'local_target' in kwargs:
            # test existence
            if os.path.exists(kwargs['local_target']):
                pass  # TODO
            else:
                return LocalSourceProvider(cls.DUMMY_PYCODE)

        elif 'remote_target' in kwargs:
            pass
        else:
            raise ValueError('cannot build ad-hoc ScProvider')
