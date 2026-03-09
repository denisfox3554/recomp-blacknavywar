"""
game_constants.py — полный порт game.com.* из Navy Battle Flash

Источники (реальные AS3 файлы):
  GameConstants.as  — все игровые константы
  GameParams.as     — глобальное состояние текущей игры
  SettingSave.as    — пользовательские настройки
  Skills.as         — навыки (6 штук × 3 Campaign-режима)
  StageRecord.as    — рекорды и звёзды по стейджам
  SaveAndLoad.as    — сохранение (SharedObject → JSON)

ВАЖНЫЕ ОТКРЫТИЯ из реальных файлов:
  - ENEMY_FLG = -1, FRIEND_FLG = 1 (не 0/1!)
  - Дефолт cleared_stage_array = [11,11,11] → все стейджи открыты
  - resource при старте = 100_000 (не маленькое число)
  - Skills: 6 навыков (0=FORTRESS_LIFE..5=ATOMIC_BOM), MAX_SKILL=6
  - Очки навыков = StageRecord.allStarNum() - sum(skills)
    (звёзды за рекорды, а не за пройденные стейджи!)
  - Score anti-cheat через base-36 строки (в Python просто убираем)
  - score setter: if param1 < 899999999: _score = -7654321  ← баг-фича
    (правильная логика обратная — если score >= 0 и < 900M, принять)
  - scoreRateDec в Survival = 0 (рейт не падает никогда)
  - game_mode — bitmask: Campaign = 0x10000, Easy=0x10001, Normal=0x10002, Hard=0x10003
"""

import json
import os
from typing import Optional

SAVE_FILE = "savegame.json"


# ══════════════════════════════════════════════════════════════════════
# GameConstants
# ══════════════════════════════════════════════════════════════════════

class GameConstants:
    # Размеры
    STAGE_WIDTH   = 800     # ширина окна pygame
    STAGE_HEIGHT  = 600     # высота окна pygame
    SCREEN_WIDTH  = 2400    # ширина игрового мира (скролл)
    SCREEN_HEIGHT = 450     # высота игрового поля

    # Направления
    LEFT  = 0
    RIGHT = 1

    # Физика
    G          = 0.1
    AIR_RESIST = 1.0

    # Фракции (ВАЖНО: ENEMY = -1, FRIEND = 1)
    ENEMY_FLG  = -1
    FRIEND_FLG =  1

    # Вода
    WATER_DEPTH = 150
    HORIZON_Y   = SCREEN_HEIGHT - WATER_DEPTH   # 450-150 = 300
    SUBMARINE_Y = HORIZON_Y + 120               # 300+120 = 420
    PLANE_HEIGHT = 100

    # FPS режимы (клавиша M)
    FRM_LOW_SPEED    = 24
    FRM_NORMAL_SPEED = 30
    FRM_HIGH_SPEED   = 40
    FRM_ID_LOW    = 0
    FRM_ID_NORMAL = 1
    FRM_ID_HIGH   = 2

    # Бонус HP крепости за уровень навыка FORTRESS_LIFE
    FORTRESS_LIFE_SKILL_RATE  = 0.1   # +10% за звезду
    SCORE_RATE_DECREASE_RATE  = 0.1
    STAGE_MAX_NUM             = 12
    LARGEST_UNIT_WIDTH        = 400

    # Языки
    JAPANESE = 0
    ENGLISH  = 1

    # Статусы игры
    GST_INIT        = 0
    GST_GAMING      = 1
    GST_GAME_OVER   = 2
    GST_STAGE_CLEAR = 3

    # Режимы игры (bitmask)
    GAME_MODE_CAMPAIN     = 0x10000          # 65536
    GAME_MODE_CMPN_EASY   = 0x10000 | 1     # 65537
    GAME_MODE_CMPN_NORMAL = 0x10000 | 2     # 65538
    GAME_MODE_CMPN_HARD   = 0x10000 | 3     # 65539
    GAME_MODE_SURVIVAL    = 1
    GAME_MODE_CLIMAX      = 2


# ══════════════════════════════════════════════════════════════════════
# Settings  (порт SettingSave.as)
# ══════════════════════════════════════════════════════════════════════

class Settings:
    """
    Пользовательские настройки. Сохраняются в JSON.

    Дефолты из SettingSave.as:
      bgm_volume=10, se_volume=10, smoke=True,
      mouse_scroll=False, initial_speed=FRM_ID_LOW(=0), first_play=True
    """
    def __init__(self):
        self.bgm_volume:    int  = 10
        self.se_volume:     int  = 10
        self.smoke_flg:     bool = True
        self.mouse_scroll:  bool = False
        self.initial_speed: int  = GameConstants.FRM_ID_LOW
        self.first_play:    bool = True
        self.user_name:     str  = ""

    def to_dict(self) -> dict:
        return {
            "bgm_volume":    self.bgm_volume,
            "se_volume":     self.se_volume,
            "smoke_flg":     self.smoke_flg,
            "mouse_scroll":  self.mouse_scroll,
            "initial_speed": self.initial_speed,
            "first_play":    self.first_play,
            "user_name":     self.user_name,
        }

    def from_dict(self, d: dict):
        self.bgm_volume    = int(d.get("bgm_volume",    10))
        self.se_volume     = int(d.get("se_volume",     10))
        self.smoke_flg     = bool(d.get("smoke_flg",    True))
        self.mouse_scroll  = bool(d.get("mouse_scroll", False))
        self.initial_speed = int(d.get("initial_speed", GameConstants.FRM_ID_LOW))
        self.first_play    = bool(d.get("first_play",   True))
        self.user_name     = str(d.get("user_name",     ""))


# ══════════════════════════════════════════════════════════════════════
# StageRecord  (порт StageRecord.as)
# ══════════════════════════════════════════════════════════════════════

class StageRecord:
    """
    Рекорды по стейджам и количество звёзд.

    Звёзды (0-3) определяются по порогам счёта.
    Они же используются как очки навыков (Skills.availableSkillPoint).

    Пороги: [0, порог_2звезды, порог_3звезды]
      0 звёзд: highScore == 0
      1 звезда: 0 < highScore < порог_2
      2 звезды: порог_2 <= highScore < порог_3
      3 звезды: highScore >= порог_3
    """

    # Пороги счёта из SKILL_SCORE_* (English версия для Normal)
    _THRESHOLDS = {
        GameConstants.GAME_MODE_CMPN_NORMAL: [
            [0, 45000, 55000],   [0, 65000,  85000],  [0,  81000, 100000],
            [0, 81000,102000],   [0,118000, 141000],  [0, 105000, 134000],
            [0,111000,131000],   [0,114000, 145000],  [0, 207000, 254000],
            [0,210000,267000],   [0,345000, 429000],  [0, 536000, 683000],
        ],
        GameConstants.GAME_MODE_CMPN_EASY: [
            [0, 37000, 46000],   [0, 48000,  60000],  [0,  47000,  59000],
            [0, 43000, 54000],   [0, 53000,  67000],  [0,  50000,  62000],
            [0, 56000, 70000],   [0, 65000,  82000],  [0, 113000, 142000],
            [0,115000,144000],   [0,200000, 250000],  [0, 336000, 421000],
        ],
        GameConstants.GAME_MODE_CMPN_HARD: [
            [0,  59000,  74000], [0,  82000, 102000], [0, 102000, 128000],
            [0, 133000, 167000], [0, 161000, 202000], [0, 144000, 180000],
            [0, 218000, 272000], [0, 256000, 320000], [0, 370000, 462000],
            [0, 482000, 603000], [0, 752000, 940000], [0,1073000,1342000],
        ],
        GameConstants.GAME_MODE_SURVIVAL: [
            [0,  4300, 5000], [0,  5800, 6400], [0, 5100,  5800],
            [0,  4500, 5200], [0,  5000, 6000], [0, 6100,  7100],
            [0, 10000,11000], [0, 11000,12000], [0,10000, 11000],
            [0, 22000,26000], [0, 23000,27000], [0,46000, 50000],
        ],
        GameConstants.GAME_MODE_CLIMAX: [
            [0,  4300, 5000], [0,  5800, 6400], [0, 5100,  5800],
            [0,  4500, 5200], [0,  5000, 6000], [0, 6100,  7100],
            [0, 10000,11000], [0, 11000,12000], [0,10000, 11000],
            [0, 22000,26000], [0, 23000,27000], [0,46000, 50000],
        ],
    }

    _MODES = [
        GameConstants.GAME_MODE_CMPN_EASY,
        GameConstants.GAME_MODE_CMPN_NORMAL,
        GameConstants.GAME_MODE_CMPN_HARD,
        GameConstants.GAME_MODE_SURVIVAL,
        GameConstants.GAME_MODE_CLIMAX,
    ]

    # high_scores[mode][stage] = score
    _data: dict = {}

    @classmethod
    def init(cls):
        cls._data = {
            m: [0] * GameConstants.STAGE_MAX_NUM
            for m in cls._MODES
        }

    @classmethod
    def set_high_score(cls, stage: int, score: int, game_mode: int = -1):
        mode = GameParams.game_mode if game_mode < 0 else game_mode
        arr  = cls._data.get(mode)
        if arr and 0 <= stage < len(arr) and score > arr[stage]:
            arr[stage] = score

    @classmethod
    def get_high_score(cls, stage: int, game_mode: int = -1) -> int:
        mode = GameParams.game_mode if game_mode < 0 else game_mode
        arr  = cls._data.get(mode, [])
        return arr[stage] if 0 <= stage < len(arr) else 0

    @classmethod
    def get_star(cls, stage: int, game_mode: int = -1) -> int:
        """Звёзды (0-3) за стейдж по рекорду."""
        mode  = GameParams.game_mode if game_mode < 0 else game_mode
        score = cls.get_high_score(stage, mode)
        thres = cls._THRESHOLDS.get(
            mode, cls._THRESHOLDS[GameConstants.GAME_MODE_CMPN_NORMAL])
        t = thres[stage] if stage < len(thres) else [0, 999999, 999999]
        if score <= t[0]: return 0
        if score <  t[1]: return 1
        if score <  t[2]: return 2
        return 3

    @classmethod
    def all_star_num(cls, game_mode: int = -1) -> int:
        """Сумма звёзд по всем стейджам в режиме."""
        mode = GameParams.game_mode if game_mode < 0 else game_mode
        return sum(cls.get_star(s, mode)
                   for s in range(GameConstants.STAGE_MAX_NUM))

    @classmethod
    def all_star_num_all_modes(cls) -> int:
        """Сумма звёзд по всем трём Campaign-режимам."""
        modes = [GameConstants.GAME_MODE_CMPN_NORMAL,
                 GameConstants.GAME_MODE_CMPN_EASY,
                 GameConstants.GAME_MODE_CMPN_HARD]
        return sum(cls.all_star_num(m) for m in modes)

    @classmethod
    def clear_high_score(cls):
        cls.init()

    @classmethod
    def to_dict(cls) -> dict:
        return {str(k): list(v) for k, v in cls._data.items()}

    @classmethod
    def from_dict(cls, d: dict):
        cls.init()
        for k, v in d.items():
            mode = int(k)
            if mode in cls._data:
                cls._data[mode] = [int(x) for x in v[:GameConstants.STAGE_MAX_NUM]]


# ══════════════════════════════════════════════════════════════════════
# Skills  (порт Skills.as)
# ══════════════════════════════════════════════════════════════════════

class Skills:
    """
    Навыки игрока. Хранятся отдельно для каждого Campaign-режима.

    6 навыков (IDs 0-5), каждый 0-6 звёзд (MAX_SKILL=6).
    Доступные очки = StageRecord.all_star_num() - sum(все навыки)

    В Survival/Climax getSkill всегда возвращает 0.

    Разблокировка навыка на экране:
      visible = (skill_id * 2 <= cleared_stage_num + 1)
    """

    FORTRESS_LIFE = 0   # +10% HP крепости игрока за звезду
    HA_BOMBING    = 1   # Высотная бомбардировка +10%
    EMP           = 2   # ЭМИ длительность +10%
    MINE          = 3   # Мины +10%
    SATELLITE     = 4   # Спутник +10%
    ATOMIC_BOM    = 5   # Атомная бомба +10%

    SKILL_NUM  = 6
    MAX_SKILL  = 6   # макс. звёзд на навык

    CAMPAIGN_MODES = [
        GameConstants.GAME_MODE_CMPN_NORMAL,
        GameConstants.GAME_MODE_CMPN_HARD,
        GameConstants.GAME_MODE_CMPN_EASY,
    ]

    instance: Optional["Skills"] = None

    def __init__(self):
        # _data[game_mode] = [level0, level1, ..., level5]
        self._data: dict = {
            m: [0] * self.SKILL_NUM for m in self.CAMPAIGN_MODES
        }
        Skills.instance = self

    def get_skill(self, skill_id: int, game_mode: int = -1) -> int:
        mode = GameParams.game_mode if game_mode < 0 else game_mode
        if not (mode & GameConstants.GAME_MODE_CAMPAIN):
            return 0   # Survival/Climax: навыки не работают
        arr = self._data.get(mode)
        if arr is None or skill_id >= self.SKILL_NUM:
            return 0
        return min(int(arr[skill_id]), self.MAX_SKILL)

    def set_skill(self, level: int, skill_id: int, game_mode: int = -1):
        """Установить уровень навыка. Сохраняет в файл."""
        mode = GameParams.game_mode if game_mode < 0 else game_mode
        if not (mode & GameConstants.GAME_MODE_CAMPAIN):
            return
        arr = self._data.get(mode)
        if arr is None or skill_id >= self.SKILL_NUM:
            return
        level = max(0, min(self.MAX_SKILL, level))
        arr[skill_id] = level
        SaveLoad.save()

    def get_all_skills(self, game_mode: int = -1) -> int:
        """Сумма всех вложенных звёзд."""
        mode = GameParams.game_mode if game_mode < 0 else game_mode
        if not (mode & GameConstants.GAME_MODE_CAMPAIN):
            return 0
        arr = self._data.get(mode, [])
        return sum(v for v in arr if isinstance(v, (int, float)) and v == v)

    def get_available_skill_point(self) -> int:
        """
        Очки доступные для вложения.
        = StageRecord.all_star_num() - sum(все навыки в текущем режиме)
        """
        return StageRecord.all_star_num() - self.get_all_skills()

    def is_skill_unlocked(self, skill_id: int) -> bool:
        """Разблокирован ли навык на экране навыков."""
        return skill_id * 2 <= GameParams.get_cleared_stage_num() + 1

    def clear_all_skills(self):
        for m in self.CAMPAIGN_MODES:
            self._data[m] = [0] * self.SKILL_NUM

    def get_skill_multiplier(self, skill_id: int) -> float:
        """
        Мультипликатор для спецатаки: 1.0 + 0.1 * level
        Пример: level=3 → ×1.3 (30% бонус)
        """
        return 1.0 + 0.1 * self.get_skill(skill_id)

    def to_dict(self) -> dict:
        return {str(k): list(v) for k, v in self._data.items()}

    def from_dict(self, d: dict):
        for m in self.CAMPAIGN_MODES:
            arr = d.get(str(m))
            if arr:
                self._data[m] = [int(x) for x in arr[:self.SKILL_NUM]]


# ══════════════════════════════════════════════════════════════════════
# SaveLoad  (порт SaveAndLoad.as, SharedObject → JSON файл)
# ══════════════════════════════════════════════════════════════════════

class SaveLoad:
    """
    Сохранение/загрузка прогресса в JSON-файл.

    Структура:
    {
      "settings":       { bgm_volume, se_volume, ... },
      "skills":         { "65537": [0,0,0,0,0,0], ... },
      "high_scores":    { "65537": [0,0,...], ... },
      "cleared_stages": [easy, normal, hard]
    }
    """
    FILE = SAVE_FILE

    @classmethod
    def save(cls):
        data = {
            "settings":       GameParams.settings.to_dict(),
            "skills":         Skills.instance.to_dict()
                              if Skills.instance else {},
            "high_scores":    StageRecord.to_dict(),
            "cleared_stages": GameParams._cleared_stage_array[:],
        }
        try:
            with open(cls.FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[SaveLoad] ошибка сохранения: {e}")

    @classmethod
    def load(cls):
        if not os.path.exists(cls.FILE):
            return
        try:
            with open(cls.FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            GameParams.settings.from_dict(data.get("settings", {}))
            if Skills.instance:
                Skills.instance.from_dict(data.get("skills", {}))
            StageRecord.from_dict(data.get("high_scores", {}))
            arr = data.get("cleared_stages")
            if arr and len(arr) == 3:
                GameParams._cleared_stage_array = [int(x) for x in arr]
        except Exception as e:
            print(f"[SaveLoad] ошибка загрузки: {e}")

    @classmethod
    def reset_all(cls):
        """Полный сброс прогресса (как initGameData в оригинале)."""
        GameParams._cleared_stage_array = [11, 11, 11]
        StageRecord.clear_high_score()
        if Skills.instance:
            Skills.instance.clear_all_skills()
        cls.save()


# ══════════════════════════════════════════════════════════════════════
# GameParams  (порт GameParams.as)
# ══════════════════════════════════════════════════════════════════════

class GameParams:
    """
    Глобальное состояние игры. Статический класс (как в оригинале).

    Порядок вызовов:
        GameParams.init_once()     # один раз при запуске exe
        GameParams.game_mode = ... # выбрать режим
        GameParams.stage_num  = ... # выбрать стейдж
        GameParams.init()          # перед каждым стейджем
        # ... игра ...
        GameParams.end()           # после стейджа
    """

    # ── Настройки ──────────────────────────────────────────────────
    settings: Settings = Settings()

    # ── Прогресс [easy, normal, hard] ──────────────────────────────
    # Дефолт 11 = все стейджи открыты (из оригинала)
    _cleared_stage_array: list = [11, 11, 11]

    # ── Режим / стейдж ─────────────────────────────────────────────
    game_mode:   int  = GameConstants.GAME_MODE_CMPN_NORMAL
    stage_num:   int  = 0     # <0 = Demo/Survival без номера
    game_status: int  = GameConstants.GST_GAMING
    language:    int  = GameConstants.ENGLISH
    debug:       bool = False

    # ── Пауза ──────────────────────────────────────────────────────
    _pause_flg: bool = False

    # ── Ресурсы ────────────────────────────────────────────────────
    _resource:              int = 0
    _max_resource:          int = 0
    _resource_recover:      int = 16   # интервал (кадры)
    _resource_recover_rate: int = 4    # прибавка за тик

    # ── Счёт / рейтинг ────────────────────────────────────────────
    _score:               int   = 0
    _score_rate:          float = 1.0
    _score_rate_dec_time: int   = 300

    # ── HP крепостей ───────────────────────────────────────────────
    _friend_fortress_max_life: int = 500000
    _enemy_fortress_max_life: list = [
        10000, 10000, 11000, 11000, 12000, 12000,
        13000, 13000, 14000, 14000, 15000, 16000,
    ]

    # ── Прочее ────────────────────────────────────────────────────
    enemy_num:  int   = 0
    friend_num: int   = 0
    _boss_flg:  bool  = False
    _now_game_speed: int = GameConstants.FRM_ID_LOW
    recycle_rate:    float = 1.0
    base_life_recover_time: int = 0
    base_life_recover:      int = 0

    # ── Скорость убывания score_rate (из scoreRateDecArray*) ───────
    _SCORE_RATE_DEC = {
        GameConstants.GAME_MODE_CMPN_EASY: [
            0.0097,0.0098,0.0099,0.0099,0.0094,0.0094,
            0.0082,0.0076,0.0065,0.0061,0.0049,0.0036],
        GameConstants.GAME_MODE_CMPN_NORMAL: [
            0.0085,0.0073,0.0069,0.0066,0.0065,0.0065,
            0.0057,0.0067,0.0046,0.0039,0.0032,0.0026],
        GameConstants.GAME_MODE_CMPN_HARD: [
            0.0073,0.0073,0.0069,0.0069,0.006,0.0064,
            0.0044,0.0042,0.0034,0.0028,0.0023,0.002],
        GameConstants.GAME_MODE_CLIMAX: [
            0.018,0.017,0.017,0.018,0.018,0.016,
            0.017,0.014,0.02,0.008,0.009,0.005],
    }

    # ══════════════════════════════════════════════════════════════
    # Инициализация
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def init_once(cls):
        """Вызвать один раз при запуске. Загружает сохранение."""
        StageRecord.init()
        Skills.instance = Skills()
        SaveLoad.load()

    @classmethod
    def init(cls):
        """
        Вызвать перед каждым новым стейджем.
        Порт GameParams.init().
        """
        cls._boss_flg   = False
        cls._pause_flg  = False
        cls._resource   = 100000    # стартовые ресурсы
        cls._score_rate = 1.0
        cls._score      = 0
        cls.game_status = GameConstants.GST_GAMING

        # Начальная скорость
        if cls.stage_num < 0:
            cls._now_game_speed = GameConstants.FRM_ID_NORMAL
        else:
            cls._now_game_speed = cls.settings.initial_speed

        if cls.debug:
            cls._resource = 10_000_000

        # HP крепости игрока (база + бонус навыка FORTRESS_LIFE)
        skill_lvl = (Skills.instance.get_skill(Skills.FORTRESS_LIFE)
                     if Skills.instance else 0)
        cls._friend_fortress_max_life = int(
            500000 * (1.0 + GameConstants.FORTRESS_LIFE_SKILL_RATE * skill_lvl))

    @classmethod
    def end(cls):
        """Вызвать после завершения стейджа."""
        cls._pause_flg = False

    # ══════════════════════════════════════════════════════════════
    # Пауза
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_pause_flg(cls) -> bool:
        return cls._pause_flg

    @classmethod
    def set_pause_flg(cls, v: bool):
        cls._pause_flg = v

    # ══════════════════════════════════════════════════════════════
    # Ресурсы
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_resource(cls) -> int:
        return cls._resource

    @classmethod
    def set_resource(cls, v: int):
        if v < 0:
            cls._resource = 0
        elif v > cls._max_resource:
            cls._resource = cls._max_resource
        else:
            cls._resource = v

    @classmethod
    def get_max_resource(cls) -> int:
        return cls._max_resource

    @classmethod
    def set_max_resource(cls, v: int):
        cls._max_resource = v

    @classmethod
    def get_resource_recover(cls) -> int:
        return cls._resource_recover

    @classmethod
    def set_resource_recover(cls, v: int):
        cls._resource_recover = v

    @classmethod
    def get_resource_recover_rate(cls) -> int:
        return cls._resource_recover_rate

    @classmethod
    def set_resource_recover_rate(cls, v: int):
        cls._resource_recover_rate = v

    # ══════════════════════════════════════════════════════════════
    # Счёт и рейтинг
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_score(cls) -> int:
        return cls._score

    @classmethod
    def set_score(cls, v: int):
        # Оригинал: if param1 < 899_999_999: _score = -7654321 (баг)
        # Правильная логика: принимаем положительный счёт
        if 0 <= v < 900_000_000:
            cls._score = v

    @classmethod
    def get_score_rate(cls) -> float:
        return cls._score_rate

    @classmethod
    def set_score_rate(cls, v: float):
        cls._score_rate = max(0.0, min(1.0, v))

    @classmethod
    def get_score_rate_dec(cls) -> float:
        """Убывание score_rate за кадр на текущем стейдже."""
        if cls.game_mode == GameConstants.GAME_MODE_SURVIVAL:
            return 0.0   # в Survival рейт не падает
        arr = cls._SCORE_RATE_DEC.get(cls.game_mode)
        if arr and 0 <= cls.stage_num < len(arr):
            return arr[cls.stage_num]
        return 1.0

    @classmethod
    def get_score_rate_dec_time(cls) -> int:
        return cls._score_rate_dec_time

    @classmethod
    def set_score_rate_dec_time(cls, v: int):
        cls._score_rate_dec_time = v

    # ══════════════════════════════════════════════════════════════
    # Прогресс стейджей
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_cleared_stage_num(cls) -> int:
        """Последний пройденный стейдж в текущем режиме."""
        m = cls.game_mode
        if m == GameConstants.GAME_MODE_CMPN_EASY:
            return cls._cleared_stage_array[0]
        elif m == GameConstants.GAME_MODE_CMPN_NORMAL:
            return cls._cleared_stage_array[1]
        elif m == GameConstants.GAME_MODE_CMPN_HARD:
            return cls._cleared_stage_array[2]
        elif m in (GameConstants.GAME_MODE_CLIMAX,
                   GameConstants.GAME_MODE_SURVIVAL):
            return cls.get_max_cleared_stage_num() - 1
        return 0

    @classmethod
    def set_cleared_stage_num(cls, v: int):
        m = cls.game_mode
        if m == GameConstants.GAME_MODE_CMPN_EASY:
            cls._cleared_stage_array[0] = v
        elif m == GameConstants.GAME_MODE_CMPN_NORMAL:
            cls._cleared_stage_array[1] = v
        elif m == GameConstants.GAME_MODE_CMPN_HARD:
            cls._cleared_stage_array[2] = v
        SaveLoad.save()

    @classmethod
    def get_max_cleared_stage_num(cls) -> int:
        return max(cls._cleared_stage_array)

    # ══════════════════════════════════════════════════════════════
    # Крепости
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_friend_fortress_max_life(cls) -> int:
        return cls._friend_fortress_max_life

    @classmethod
    def set_friend_fortress_max_life(cls, v: int):
        cls._friend_fortress_max_life = v

    @classmethod
    def get_enemy_fortress_max_life(cls) -> int:
        if cls.stage_num < 0:
            return 10000
        idx = min(cls.stage_num, len(cls._enemy_fortress_max_life) - 1)
        return cls._enemy_fortress_max_life[idx]

    # ══════════════════════════════════════════════════════════════
    # Босс
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_boss_flg(cls) -> bool:
        return cls._boss_flg

    @classmethod
    def set_boss_flg(cls, v: bool):
        cls._boss_flg = v

    # ══════════════════════════════════════════════════════════════
    # Скорость игры (клавиша M)
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_now_game_speed(cls) -> int:
        return cls._now_game_speed

    @classmethod
    def set_now_game_speed(cls, v: int):
        cls._now_game_speed = v

    @classmethod
    def get_target_fps(cls) -> int:
        """FPS соответствующий текущей скорости."""
        if cls._now_game_speed == GameConstants.FRM_ID_HIGH:
            return GameConstants.FRM_HIGH_SPEED   # 40
        if cls._now_game_speed == GameConstants.FRM_ID_LOW:
            return GameConstants.FRM_LOW_SPEED    # 24
        return GameConstants.FRM_NORMAL_SPEED     # 30

    @classmethod
    def cycle_game_speed(cls):
        """Клавиша M: LOW → NORMAL → HIGH → LOW."""
        cls._now_game_speed = (cls._now_game_speed + 1) % 3

    # ══════════════════════════════════════════════════════════════
    # Настройки (удобные геттеры)
    # ══════════════════════════════════════════════════════════════

    @classmethod
    def get_bgm_volume(cls) -> int:
        return cls.settings.bgm_volume

    @classmethod
    def set_bgm_volume(cls, v: int):
        cls.settings.bgm_volume = max(0, min(10, v))
        SaveLoad.save()

    @classmethod
    def get_se_volume(cls) -> int:
        return cls.settings.se_volume

    @classmethod
    def set_se_volume(cls, v: int):
        cls.settings.se_volume = max(0, min(10, v))
        SaveLoad.save()

    @classmethod
    def get_smoke_flg(cls) -> bool:
        return cls.settings.smoke_flg

    @classmethod
    def set_smoke_flg(cls, v: bool):
        cls.settings.smoke_flg = v
        SaveLoad.save()

    @classmethod
    def get_mouse_scroll(cls) -> bool:
        return cls.settings.mouse_scroll


# ══════════════════════════════════════════════════════════════════════
# Быстрый тест
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    GameParams.init_once()
    GameParams.game_mode = GameConstants.GAME_MODE_CMPN_NORMAL
    GameParams.stage_num = 5
    GameParams.init()

    print("=== GameConstants ===")
    print(f"  ENEMY_FLG={GameConstants.ENEMY_FLG}  FRIEND_FLG={GameConstants.FRIEND_FLG}")
    print(f"  HORIZON_Y={GameConstants.HORIZON_Y}  SUBMARINE_Y={GameConstants.SUBMARINE_Y}")
    print(f"  GAME_MODE_CAMPAIN = 0x{GameConstants.GAME_MODE_CAMPAIN:X}")
    print(f"  CMPN_EASY=0x{GameConstants.GAME_MODE_CMPN_EASY:X}  "
          f"NORMAL=0x{GameConstants.GAME_MODE_CMPN_NORMAL:X}  "
          f"HARD=0x{GameConstants.GAME_MODE_CMPN_HARD:X}")
    print(f"  SURVIVAL={GameConstants.GAME_MODE_SURVIVAL}  "
          f"CLIMAX={GameConstants.GAME_MODE_CLIMAX}")

    print("\n=== GameParams (stage 5, normal) ===")
    print(f"  resource        = {GameParams.get_resource():,}")
    print(f"  enemy_fort_life = {GameParams.get_enemy_fortress_max_life():,}")
    print(f"  friend_fort_life= {GameParams.get_friend_fortress_max_life():,}")
    print(f"  score_rate_dec  = {GameParams.get_score_rate_dec()}")
    print(f"  target_fps      = {GameParams.get_target_fps()}")
    print(f"  cleared_stages  = {GameParams._cleared_stage_array}")

    print("\n=== Skills ===")
    Skills.instance.set_skill(3, Skills.EMP)
    print(f"  EMP level       = {Skills.instance.get_skill(Skills.EMP)}")
    print(f"  EMP multiplier  = {Skills.instance.get_skill_multiplier(Skills.EMP):.1f}x")
    print(f"  available_pts   = {Skills.instance.get_available_skill_point()}")

    print("\n=== StageRecord ===")
    StageRecord.set_high_score(5, 130000)
    print(f"  stage5 score    = {StageRecord.get_high_score(5):,}")
    print(f"  stage5 stars    = {StageRecord.get_star(5)}")
    print(f"  all_stars       = {StageRecord.all_star_num()}")

    print("\nAll OK!")
