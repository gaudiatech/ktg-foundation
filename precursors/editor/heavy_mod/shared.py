import katagames_sdk as katasdk

EditorEvTypes = katasdk.kengi.event.enum_ev_types(
    'TextAreaToCarretOp',
    'CaretMoves',
    'RedrawNeeded'  # the view has to redraw numbers etc.
)

DIR_CARTRIDGES = 'cartridges'
