import os
import re
from abc import ABCMeta, abstractmethod

import katagames_sdk as katasdk


CogObj = katasdk.kengi.event.CogObj


# --------------------------------------
#  MODEL
class Sharedstuff:
    def __init__(self):
        self.disp_save_ico = None  # contains info 'bout time when it needs display
        self.dump_content = None
        self.kartridge_output = None
        self.screen = None
        self.file_label = None  # for showing what is being edited


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


class VirtualFilesetBuffer:
    """
    can use several files, by default its only main.py
    its called a BUFFER because the user can modify whats inside, then push the new BUFFER content to update
    our current data source
    """
    def __init__(self, mashup_code):
        # lets distinguish virtual .py files
        self.files_to_content = dict()
        self.file_order = None
        self._disting_files(mashup_code)

    @property
    def size(self):
        return len(self.file_order)

    def _disting_files(self, rawcode):
        all_lines = rawcode.splitlines()
        #  on généralise pour qu'on puisse gérer plusieurs fichiers et pas que 2,
        #  et que l'on puisse choisir son nom xxx.py au lieu d'avoir choisi thing.py en dur!
        groups = re.findall(r"# >>>(\b[a-z]+\b\.py)", rawcode)

        # find starts
        starts = dict()
        order = list()
        if len(groups):
            for vfilename in groups:
                for k, li in enumerate(all_lines):
                    teststr = f"# >>>{vfilename}"
                    if li == teststr:
                        starts[vfilename] = k+1
                        order.append(vfilename)

        # find stops
        stops = dict()
        order.insert(0, 'main.py')
        if len(order):
            kk = 1
            while kk < len(order):
                nxt = order[kk]
                stops[order[kk-1]] = starts[nxt]-2
                kk += 1
            stops[order[kk - 1]] = len(all_lines)-1
        else:
            order.append('main.py')
            stops['main.py'] = len(all_lines)-1
        starts['main.py'] = 0
        print('starts:\n', starts)
        print('stops:\n', stops)

        for e in order:
            self.files_to_content[e] = all_lines[starts[e]:stops[e]+1]
        order.remove('main.py')
        order.sort()
        self.file_order = ['main.py'] + order

    def __getitem__(self, item):  # item should be main.py for example
        return self.files_to_content[item]


class VirtualClipboard:  # simulation
    strv = None

    @classmethod
    def copy(cls, vstr):
        cls.strv = str(vstr)

    @classmethod
    def cut(cls, vstr):
        cls.strv = str(vstr)

    @classmethod
    def paste(cls):
        return cls.strv


sharedstuff_obj = Sharedstuff()
