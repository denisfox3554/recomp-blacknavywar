"""Stage Select widgets ported from ActionScript to Python.

Source classes:
- game.stageSelect.StagesClimaxStar
- game.stageSelect.StagesDifficulty

These classes keep logic-only behavior so they can be reused with pygame,
arcade, tkinter, or any custom renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class StageRecordLike(Protocol):
    """Minimal protocol for StageRecord compatibility."""

    @staticmethod
    def all_star_num(game_mode: int) -> int:
        """Return total stars for a given game mode."""


class GameConstantsLike(Protocol):
    """Minimal protocol for constants consumed by stage select widgets."""

    GAME_MODE_CMPN_EASY: int
    GAME_MODE_CMPN_NORMAL: int
    GAME_MODE_CMPN_HARD: int
    FRM_ID_NORMAL: int


class GameParamsLike(Protocol):
    """Minimal protocol for game params consumed by stage select widgets."""

    game_mode: int


class UnitDescriptionLike(Protocol):
    """Minimal unit description payload."""

    unit_name: str


@dataclass
class StagesClimaxStar:
    """Port of AS3 `StagesClimaxStar`.

    Computes campaign star totals for easy/normal/hard and exposes them as
    strings (mirroring Flash TextField `.text` values).
    """

    stage_record: StageRecordLike
    game_constants: GameConstantsLike

    easy_txt: str = ""
    normal_txt: str = ""
    hard_txt: str = ""
    total_txt: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        easy = self.stage_record.all_star_num(self.game_constants.GAME_MODE_CMPN_EASY)
        normal = self.stage_record.all_star_num(self.game_constants.GAME_MODE_CMPN_NORMAL)
        hard = self.stage_record.all_star_num(self.game_constants.GAME_MODE_CMPN_HARD)

        self.easy_txt = str(easy)
        self.normal_txt = str(normal)
        self.hard_txt = str(hard)
        self.total_txt = str(easy + normal + hard)


@dataclass
class StagesDifficulty:
    """Port of AS3 `StagesDifficulty`.

    Original AS3 had an unusual `case GameConstants.FRM_ID_NORMAL` branch while
    other branches compare game mode constants. To preserve behavior we support
    both CMPN normal and FRM normal ids.
    """

    game_params: GameParamsLike
    game_constants: GameConstantsLike

    difficulty_txt: str = ""

    def refresh(self) -> None:
        mode = self.game_params.game_mode
        if mode == self.game_constants.GAME_MODE_CMPN_EASY:
            self.difficulty_txt = "Easy"
        elif mode in (
            self.game_constants.GAME_MODE_CMPN_NORMAL,
            self.game_constants.FRM_ID_NORMAL,
        ):
            self.difficulty_txt = "Normal"
        elif mode == self.game_constants.GAME_MODE_CMPN_HARD:
            self.difficulty_txt = "Hard"
        else:
            self.difficulty_txt = ""


def _read_attr(obj: Any, *names: str, default: Any = None) -> Any:
    """Return first present attribute from a list of snake/camel case names."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def _call_first(obj: Any, names: tuple[str, ...], *args: Any) -> Any:
    """Call first available method name from `names` on `obj`."""
    for name in names:
        fn = getattr(obj, name, None)
        if callable(fn):
            return fn(*args)
    raise AttributeError(f"None of methods {names!r} exist on {obj!r}")


@dataclass
class StageSelectBtnBase:
    """Logic port of AS3 `StageSelectBtnBase`.

    Renderer/UI independent model that computes stage button text fields and star
    frame index.
    """

    game_params: Any
    game_constants: Any
    stage_record: Any
    unit_database: Any

    FLAGSHIPS: tuple[int, ...] = ()

    stage_num: int = 0
    stage_txt: str = ""
    score_txt: str = "----"
    star2_txt: str = "----"
    star3_txt: str = "----"
    flagship_txt: str = "----"
    stars_frame: int = 1

    def set_stage_from_parent_name(self, parent_name: str) -> None:
        """Extract stage number from Flash-style parent instance name.

        AS used `parseInt(parent.name.substr(5,2))`, i.e. names like `stage01`.
        """
        self.stage_num = int(parent_name[5:7])
        self.stage_txt = str(self.stage_num)

    def refresh(self) -> None:
        mode = _read_attr(self.game_params, "game_mode", "gameMode")
        if mode is None:
            raise AttributeError("game_params must expose game_mode/gameMode")

        is_campaign = bool(mode & self.game_constants.GAME_MODE_CAMPAIN)
        if is_campaign:
            self._campaign_txt_set(mode)
        else:
            self._climax_txt_set(mode)

    def _score_row(self, mode: int) -> list[int] | None:
        skill_score = _read_attr(self.stage_record, "SKILL_SCORE", "skill_score")
        if skill_score is None:
            return None
        if self.stage_num <= 0:
            return None
        mode_table = skill_score.get(mode)
        if not mode_table:
            return None
        idx = self.stage_num - 1
        if idx < 0 or idx >= len(mode_table):
            return None
        return mode_table[idx]

    def _set_star_thresholds(self, unlocked_for_thresholds: bool, mode: int) -> None:
        row = self._score_row(mode)
        if unlocked_for_thresholds and row is not None and len(row) > 2:
            self.star2_txt = str(row[1])
            self.star3_txt = str(row[2])
        else:
            self.star2_txt = "----"
            self.star3_txt = "----"

    def _set_score_and_flagship(self, unlocked_for_score: bool) -> None:
        if not unlocked_for_score:
            self.score_txt = "----"
            self.flagship_txt = "----"
            self.stars_frame = 1
            return

        stage_idx = self.stage_num - 1
        high_score = _call_first(self.stage_record, ("get_high_score", "getHighScore"), stage_idx)
        stars = _call_first(self.stage_record, ("get_star", "getStar"), stage_idx)
        desc = _call_first(self.unit_database, ("get_description", "getDescription"), self.FLAGSHIPS[stage_idx])

        self.score_txt = str(high_score)
        self.stars_frame = int(stars) + 1
        self.flagship_txt = str(_read_attr(desc, "unit_name", "unitName", default=""))

    def _climax_txt_set(self, mode: int) -> None:
        max_cleared = int(_read_attr(self.game_params, "max_cleard_stage_num", "maxCleardStageNum", default=-1))
        stage_limit = max_cleared + 1
        self._set_star_thresholds(self.stage_num <= stage_limit, mode)
        self._set_score_and_flagship(self.stage_num <= stage_limit)

    def _campaign_txt_set(self, mode: int) -> None:
        cleared = int(_read_attr(self.game_params, "cleard_stage_num", "cleardStageNum", default=-1))
        threshold_limit = cleared + 3
        self._set_star_thresholds(self.stage_num < threshold_limit, mode)

        score_limit = cleared + 1
        self._set_score_and_flagship(self.stage_num <= score_limit)

@dataclass
class StageSelectSurvivalBtn:
    """Logic port of AS3 `StageSelectSurvivalBtn`.

    - Reads stage number from button instance name (`name.substr(6,2)`).
    - Enables click only when stage is unlocked by `maxCleardStageNum + 1`.
    - On click sets `GameParams.stageNum = stageNum - 1` and triggers transition to
      `gameMain` via a callback.
    """

    game_params: Any
    goto_and_play: Any

    stage_num: int = 0
    enabled: bool = False

    def set_stage_from_name(self, name: str) -> None:
        """Parse stage number from names like `button01` using AS indices."""
        self.stage_num = int(name[6:8])

    def refresh_enabled(self) -> None:
        max_cleared = int(_read_attr(self.game_params, "max_cleard_stage_num", "maxCleardStageNum", default=-1))
        self.enabled = self.stage_num <= (max_cleared + 1)

    def on_mouse_up(self) -> bool:
        """Run click behavior; returns True only when transition is performed."""
        if not self.enabled:
            return False

        stage_value = self.stage_num - 1
        if hasattr(self.game_params, "stage_num"):
            self.game_params.stage_num = stage_value
        else:
            setattr(self.game_params, "stageNum", stage_value)

        if callable(self.goto_and_play):
            self.goto_and_play("gameMain")
            return True
        return False


@dataclass
class StageSelectSurvivalBtnBase:
    """Logic port of AS3 `StageSelectSurvivalBtnBase`.

    Reads stage index from parent button name (`parent.name.substr(6,2)`),
    writes stage label text, and exposes score visibility/value according to
    survival unlock progression.
    """

    game_params: Any
    stage_record: Any

    stage_num: int = 0
    stage_txt: str = ""
    score_txt: str = "----"

    def set_stage_from_parent_name(self, parent_name: str) -> None:
        """Parse stage number from names like `button01` using AS indices."""
        self.stage_num = int(parent_name[6:8])
        self.stage_txt = str(self.stage_num)

    def refresh(self) -> None:
        mode = _read_attr(self.game_params, "game_mode", "gameMode")
        cleared = int(_read_attr(self.game_params, "cleard_stage_num", "cleardStageNum", default=-1))

        # AS reads this row but does not use it in final UI assignments.
        skill_score = _read_attr(self.stage_record, "SKILL_SCORE", "skill_score", default={})
        mode_rows = skill_score.get(mode, []) if hasattr(skill_score, 'get') else []
        _ = mode_rows[self.stage_num - 1] if 0 < self.stage_num <= len(mode_rows) else None

        if self.stage_num > (cleared + 2):
            self.score_txt = "----"
            return

        stage_idx = self.stage_num - 1
        high_score = _call_first(self.stage_record, ("get_high_score", "getHighScore"), stage_idx)
        self.score_txt = str(high_score)


@dataclass
class StageSkillAvailablePoint:
    """Logic port of AS3 `StageSkillAvailablePoint`.

    Mirrors `a_txt.text = Skills.instance.availableSkillPoint.toString()`.
    """

    skills: Any
    a_txt: str = ""

    def __post_init__(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        instance = _read_attr(self.skills, "instance", default=self.skills)
        points = _read_attr(instance, "available_skill_point", "availableSkillPoint", default=0)
        self.a_txt = str(points)


@dataclass
class StageSeletcBtn:
    """Logic port of AS3 `StageSeletcBtn` (typo preserved from original).

    Determines button enabled state from campaign/climax unlock rules and
    performs stage selection transition to game main on click.
    """

    game_params: Any
    game_constants: Any
    stage_record: Any
    goto_and_play: Any

    stage_num: int = 0
    enabled: bool = False

    def set_stage_from_name(self, name: str) -> None:
        """Parse stage number from names like `stage01` using AS indices."""
        self.stage_num = int(name[5:7])

    def refresh_enabled(self) -> None:
        mode = _read_attr(self.game_params, "game_mode", "gameMode", default=0)
        self.enabled = False

        if mode & self.game_constants.GAME_MODE_CAMPAIN:
            cleared = int(_read_attr(self.game_params, "cleard_stage_num", "cleardStageNum", default=-1))
            if self.stage_num <= (cleared + 2):
                self.enabled = True
            return

        all_stars = _call_first(self.stage_record, ("all_star_num_all_mode", "allStarNumAllMode"))
        max_cleared = int(_read_attr(self.game_params, "max_cleard_stage_num", "maxCleardStageNum", default=-1))
        if self.stage_num <= (all_stars / 3) and self.stage_num <= (max_cleared + 1):
            self.enabled = True

    def on_mouse_up(self) -> bool:
        """Run click behavior; returns True when transition is performed."""
        if not self.enabled:
            return False

        stage_value = self.stage_num - 1
        if hasattr(self.game_params, "stage_num"):
            self.game_params.stage_num = stage_value
        else:
            setattr(self.game_params, "stageNum", stage_value)

        if callable(self.goto_and_play):
            self.goto_and_play("gameMain")
            return True
        return False
