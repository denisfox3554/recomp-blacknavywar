"""Title screen widgets ported from ActionScript to Python."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SaveClearBtn:
    """Logic port of AS3 `game.title.SaveClearBtn`.

    Original behavior on mouse up:
    1. call super handler
    2. invoke `SaveConfirm.instance.inOut()`

    This Python version exposes `on_mouse_up` and records that the base handler
    would have been called.
    """

    save_confirm: Any
    super_called: bool = False

    def on_mouse_up(self) -> None:
        """Execute button click behavior."""
        self.super_called = True
        instance = getattr(self.save_confirm, "instance", self.save_confirm)
        in_out = getattr(instance, "in_out", None) or getattr(instance, "inOut", None)
        if not callable(in_out):
            raise AttributeError("save_confirm must expose instance.in_out()/inOut()")
        in_out()
