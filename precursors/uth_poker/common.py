import katagames_engine as kengi
kengi.bootstrap_e()


# class DynComponent:
#     """relies either on bare Kengi or on the KataSDK+Kengi combo"""
#     def provide_kengi(self):
#         import katagames_engine as _kengi
#         _kengi.bootstrap_e()
#         return _kengi
#
#
# class ExtComponent(DynComponent):
#     def provide_kengi(self):
#         import katagames_sdk as katasdk
#         katasdk.bootstrap()
#         return katasdk.kengi


refmodel, refview = None, None


def chip_scrolldown(x):
    global refmodel
    omega = (2, 5, 10, 20)
    curridx = omega.index(x)
    curridx -= 1
    if curridx < 0:
        curridx = len(omega) - 1
    y = omega[curridx]
    refmodel.set_chipvalue(y)


def chip_scrollup(x):
    global refmodel
    omega = (2, 5, 10, 20)
    curridx = omega.index(x)
    curridx = (curridx + 1) % len(omega)
    y = omega[curridx]
    refmodel.set_chipvalue(y)


PokerStates = kengi.struct.enum(
    'AnteSelection',
    'PreFlop',
    'Flop',
    'TurnRiver',
    'Outcome'
)

MyEvTypes = kengi.game_events_enum((
    'ChipCycle',  # contains: upwards(1,0) when going from 2->5->10->... etc or the other way around ; chips value
    'AddChips',  # used to bet in an incremental way
    'MatchStart',  # litteraly clicking on the Start button... when in AnteSelection stage

    # - buttons
    'BetSame',
    'UndoBet',
    'ClearBet',

    'NewMatch',

    'MoneyUpdate',  # contains: ante, bet, play, trips, wealth
    'ChipUpdate',  # contains: value

    'StateChanges',  # contains: pokerstate
    'RienNeVaPlus',  # sent when player has chosen bet or fold
    'MatchOver',  # contains: won(-1, 0, +1)
))
