import katagames_sdk

kengi = katagames_sdk.kengi

# --------------------------------------
#  SHARED
EditorEvents = kengi.event.enum_ev_types(
    'CaretMoves'  # contains new_pos
)

DIR_CARTRIDGES = 'cartridges'
