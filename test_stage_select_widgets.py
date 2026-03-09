import unittest

from stage_select_widgets import (
    StageSelectBtnBase,
    StageSelectSurvivalBtn,
    StagesClimaxStar,
    StagesDifficulty,
)


class _Constants:
    GAME_MODE_CMPN_EASY = 100
    GAME_MODE_CMPN_NORMAL = 200
    GAME_MODE_CMPN_HARD = 300
    FRM_ID_NORMAL = 1


class _StageRecord:
    @staticmethod
    def all_star_num(game_mode: int) -> int:
        return {
            _Constants.GAME_MODE_CMPN_EASY: 7,
            _Constants.GAME_MODE_CMPN_NORMAL: 8,
            _Constants.GAME_MODE_CMPN_HARD: 9,
        }[game_mode]


class _Params:
    def __init__(self, game_mode: int):
        self.game_mode = game_mode


class _Description:
    def __init__(self, unit_name: str):
        self.unit_name = unit_name


class _UnitDb:
    @staticmethod
    def get_description(unit_id: int):
        return _Description(f"Flagship-{unit_id}")


class _StageRecordBtn:
    SKILL_SCORE = {
        0x10001: [
            [0, 1000, 2000],
            [0, 1100, 2200],
            [0, 1200, 2400],
        ],
        2: [
            [0, 500, 700],
            [0, 600, 800],
            [0, 700, 900],
        ],
    }

    @staticmethod
    def get_high_score(stage_idx: int):
        return [3333, 4444, 5555][stage_idx]

    @staticmethod
    def get_star(stage_idx: int):
        return [1, 2, 3][stage_idx]


class _BtnConstants(_Constants):
    GAME_MODE_CAMPAIN = 0x10000




class _GoToRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, label: str):
        self.calls.append(label)

class StageSelectWidgetsTest(unittest.TestCase):
    def test_climax_star_totals(self):
        widget = StagesClimaxStar(_StageRecord, _Constants)
        self.assertEqual(widget.easy_txt, "7")
        self.assertEqual(widget.normal_txt, "8")
        self.assertEqual(widget.hard_txt, "9")
        self.assertEqual(widget.total_txt, "24")

    def test_difficulty_easy_normal_hard(self):
        easy = StagesDifficulty(_Params(_Constants.GAME_MODE_CMPN_EASY), _Constants)
        easy.refresh()
        self.assertEqual(easy.difficulty_txt, "Easy")

        normal = StagesDifficulty(_Params(_Constants.GAME_MODE_CMPN_NORMAL), _Constants)
        normal.refresh()
        self.assertEqual(normal.difficulty_txt, "Normal")

        hard = StagesDifficulty(_Params(_Constants.GAME_MODE_CMPN_HARD), _Constants)
        hard.refresh()
        self.assertEqual(hard.difficulty_txt, "Hard")

    def test_difficulty_legacy_frm_normal_branch(self):
        normal = StagesDifficulty(_Params(_Constants.FRM_ID_NORMAL), _Constants)
        normal.refresh()
        self.assertEqual(normal.difficulty_txt, "Normal")

    def test_stage_select_btn_campaign_visibility_and_values(self):
        params = type("P", (), {"game_mode": 0x10001, "cleard_stage_num": 1})()
        btn = StageSelectBtnBase(
            params,
            _BtnConstants,
            _StageRecordBtn,
            _UnitDb,
            FLAGSHIPS=(10, 20, 30),
        )
        btn.set_stage_from_parent_name("stage02")
        btn.refresh()
        self.assertEqual(btn.stage_txt, "2")
        self.assertEqual(btn.star2_txt, "1100")
        self.assertEqual(btn.star3_txt, "2200")
        self.assertEqual(btn.score_txt, "4444")
        self.assertEqual(btn.flagship_txt, "Flagship-20")
        self.assertEqual(btn.stars_frame, 3)

    def test_stage_select_btn_climax_locked_stage(self):
        params = type("P", (), {"game_mode": 2, "max_cleard_stage_num": 0})()
        btn = StageSelectBtnBase(
            params,
            _BtnConstants,
            _StageRecordBtn,
            _UnitDb,
            FLAGSHIPS=(10, 20, 30),
        )
        btn.set_stage_from_parent_name("stage03")
        btn.refresh()
        self.assertEqual(btn.star2_txt, "----")
        self.assertEqual(btn.star3_txt, "----")
        self.assertEqual(btn.score_txt, "----")
        self.assertEqual(btn.flagship_txt, "----")
        self.assertEqual(btn.stars_frame, 1)

    def test_survival_btn_enable_and_click(self):
        params = type("P", (), {"maxCleardStageNum": 1})()
        recorder = _GoToRecorder()
        btn = StageSelectSurvivalBtn(params, recorder)
        btn.set_stage_from_name("button02")
        btn.refresh_enabled()

        self.assertTrue(btn.enabled)
        self.assertTrue(btn.on_mouse_up())
        self.assertEqual(getattr(params, "stageNum"), 1)
        self.assertEqual(recorder.calls, ["gameMain"])

    def test_survival_btn_locked_no_transition(self):
        params = type("P", (), {"maxCleardStageNum": 0, "stageNum": -1})()
        recorder = _GoToRecorder()
        btn = StageSelectSurvivalBtn(params, recorder)
        btn.set_stage_from_name("button03")
        btn.refresh_enabled()

        self.assertFalse(btn.enabled)
        self.assertFalse(btn.on_mouse_up())
        self.assertEqual(params.stageNum, -1)
        self.assertEqual(recorder.calls, [])


if __name__ == "__main__":
    unittest.main()
