import pygame
from heavy_mod.shared import EditorEvTypes


def scrollbar_up(self) -> None:
    self.showStartLine -= 1
    self.cursor_Y += self.line_gap
    self.pev(EditorEvTypes.RedrawNeeded)


def scrollbar_down(self) -> None:
    self.showStartLine += 1
    self.cursor_Y -= self.line_gap
    self.pev(EditorEvTypes.RedrawNeeded)
