

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
    'NewMatch',

    'MoneyUpdate',  # contains: ante, bet, play, trips, wealth
    'ChipUpdate',  # contains: value

    'StateChanges',  # contains: pokerstate
    'EndRoundRequested',

    'Victory',  # contains: amount
    'Tie',
    'Defeat'  # contains: loss
))
