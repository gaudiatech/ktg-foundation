

class DynComponent:
    """relies either on bare Kengi or on the KataSDK+Kengi combo"""
    def provide_kengi(self):
        import katagames_engine as _kengi
        _kengi.bootstrap_e()
        return _kengi


class ExtComponent(DynComponent):
    def provide_kengi(self):
        import katagames_sdk as katasdk
        katasdk.bootstrap()
        return katasdk.kengi


dyncomp = DynComponent()
kengi = dyncomp.provide_kengi()
MyEvTypes = kengi.game_events_enum((
    'ChipValueUpdate',  # contains "value"
    'NewMatch',

    'MoneyUpdate',  # contains int "value"
    'StageChanges',
    'EndRoundRequested',
    'Victory',  # contains: amount
    'Tie',
    'Defeat'  # contains: loss
))
