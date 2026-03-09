"""Title screen widgets ported from ActionScript to Python."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SaveConfirm:
    """Logic port of AS3 `game.title.SaveConfirm`.

    AS3 behavior:
    - constructor sets static `instance = this`
    - on remove from stage sets `instance = null`
    - `inOut()` transitions only from INIT or DISPLAY and calls
      `gotoAndPlay("init")` or `gotoAndPlay("hide")` respectively, then moves
      to MOVING state.
    """

    INIT: int = 0
    MOVING: int = 1
    DISPLAY: int = 2

    instance: "SaveConfirm | None" = None

    status: int = INIT
    timeline_calls: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        type(self).instance = self

    def on_remove(self) -> None:
        """Mirror REMOVED_FROM_STAGE handler."""
        type(self).instance = None

    def goto_and_play(self, label: str) -> None:
        """Record timeline transitions triggered by widget logic."""
        self.timeline_calls.append(label)

    def in_out(self) -> None:
        """Python/snake_case alias for ActionScript `inOut()`."""
        if self.status == self.INIT:
            self.goto_and_play("init")
            self.status = self.MOVING
        elif self.status == self.DISPLAY:
            self.goto_and_play("hide")
            self.status = self.MOVING

    def inOut(self) -> None:  # noqa: N802 - keep AS3-compatible method name
        """AS3-compatible method name."""
        self.in_out()


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


@dataclass
class TitleCredistBtn:
    """Logic port of AS3 `game.title.TitleCredistBtn` (typo preserved)."""

    doc_root: Any
    super_called: bool = False

    def on_mouse_up(self) -> None:
        """Mirror `onMouseUpHandler`: super call + goto credits."""
        self.super_called = True
        instance = getattr(self.doc_root, "instance", self.doc_root)
        goto = getattr(instance, "goto_and_play", None) or getattr(instance, "gotoAndPlay", None)
        if not callable(goto):
            raise AttributeError("doc_root must expose instance.goto_and_play()/gotoAndPlay()")
        goto("credits")
