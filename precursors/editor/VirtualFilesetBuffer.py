import re


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
