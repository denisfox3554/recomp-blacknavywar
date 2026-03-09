# ============================================================
#  Navy Battle — Python порт AI системы (из Flash/AS3)
#  Оригинал: game.ai.* (ActionScript 3)
# ============================================================

import random
import math


# ============================================================
# КОНСТАНТЫ (заглушки — заменить из GameConstants.as)
# ============================================================
class GameConstants:
    ENEMY_FLG  = 1
    FRIEND_FLG = 0
    SCREEN_WIDTH = 800

    GAME_MODE_CMPN_EASY   = 0
    GAME_MODE_CMPN_NORMAL = 1
    GAME_MODE_CMPN_HARD   = 2
    ENGLISH = "en"


# ============================================================
# ПАРАМЕТРЫ ИГРЫ (заглушки — заменить из GameParams.as)
# ============================================================
class GameParams:
    stageNum          = 0
    gameMode          = GameConstants.GAME_MODE_CMPN_NORMAL
    language          = GameConstants.ENGLISH
    maxCleardStageNum = 0
    enemyNum          = 0
    friendNum         = 0
    bossFlg           = False


# ============================================================
# ТИПЫ ЮНИТОВ (заглушки — заменить из UnitDataBase.as)
# ============================================================
class UnitType:
    BOAT               = 0x01
    AAGUNSHIP          = 0x02
    HELICOPTER         = 0x03
    SUBMARINE          = 0x04
    BATTLESHIP         = 0x05
    TORPEDOBOMBER      = 0x06
    FRIGATE            = 0x07
    CRUISER            = 0x08
    TORPEDO_BOAT       = 0x09
    DESTROYER          = 0x0A
    FIGHTER            = 0x0B
    ANTISUBMARINE_HELI = 0x0C
    ATOMICSUBMARINE    = 0x0D
    BOMBER             = 0x0E
    CARRIER            = 0x0F
    # Батареи и крепость (UNIT_CATEGORY_BATTERY=0x800, UNDERWATER=0x2000)
    BATTERY            = 0x0800   # Artillery Battery
    MACHINEGUN_BATTERY = 0x0801   # MachineGun Battery
    MISSILE_BATTERY    = 0x0802   # Missile Battery
    TORPEDO_BATTERY    = 0x0803   # Torpedo Battery
    SUBFORTRESS        = 0x2000   # Sub-Fortress (underwater battery)
    # Боссы
    POTEMKIN           = 0x10
    DREADNOUGHT        = 0x11
    RICHELIEU          = 0x12
    NAGATO             = 0x13
    VANGUARD           = 0x14
    BISMARCK           = 0x15
    IOWA               = 0x16
    HINDENBURG         = 0x17
    NIMITZ             = 0x18
    NAUTILUS           = 0x19
    YAMATO             = 0x1A
    FORTRESSUNKNOWN    = 0x1B


# ============================================================
# DATA-КЛАССЫ
# ============================================================

class AiUnitData:
    """Данные одного юнита в волне нормальной атаки."""
    def __init__(self, unit_type: int, interval: int, av_st_num: int = 0):
        self.unitTYpe  = unit_type   # тип юнита
        self.interval  = interval    # каждые N фреймов спавнить
        self.avStNum   = av_st_num   # стартовая позиция


class CounterAttackData:
    """Данные одной волны контратаки."""
    def __init__(self, unit_type: int, unit_num: int, interval: int):
        self.unitType = unit_type   # тип юнита
        self.unitNum  = unit_num    # сколько всего заспавнить
        self.interval = interval    # каждые N фреймов — один юнит


class AIData:
    """Контейнер данных AI для одного уровня."""
    def __init__(self):
        self.bossType  = 0
        self.stageNum  = 0
        self.cadArray  = []   # контратака волна 0 (тяжёлая)
        self.cadArray1 = []   # контратака волна 1 (средняя)
        self.cadArray2 = []   # контратака волна 2 (лёгкая)


# ============================================================
# БАЗА ДАННЫХ КОНТРАТАК
# ============================================================

class CounterAttackDataBase:
    """
    Порт CounterAttackDataBase.as
    Fall-through логика: каждый уровень включает юниты всех предыдущих.
    """

    @staticmethod
    def get_data(stage: int, variant: int = 0) -> list:
        result = []

        difficulty = 1 + stage * 0.05
        rank       = 0
        total_time = 200 * 30 * (1 + stage * 0.3)
        div_factor = 4.0

        # variant определяет мультипликатор и время
        if variant == 2:
            multiplier  = 5
            total_time *= 0.6
        elif variant == 1:
            multiplier  = 6
            total_time *= 0.8
        else:
            multiplier  = 7

        def push(unit_type, cnt_div=1, int_mul=1):
            nonlocal rank
            rank += 1
            count    = multiplier * (difficulty + rank)
            interval = total_time / count
            result.append(CounterAttackData(
                unit_type,
                int(count / cnt_div),
                int(interval * int_mul)
            ))

        # Fall-through: уровень N включает всё что ниже
        if stage >= 11:
            rank += 2   # уровень 11 ещё сложнее
        if stage >= 10:
            push(UnitType.CARRIER, cnt_div=div_factor, int_mul=div_factor)
        if stage >= 9:
            push(UnitType.BOMBER, cnt_div=div_factor, int_mul=div_factor)
        if stage >= 8:
            push(UnitType.ATOMICSUBMARINE, cnt_div=div_factor, int_mul=div_factor)
        if stage >= 7:
            push(UnitType.BATTLESHIP, cnt_div=div_factor, int_mul=div_factor)
        if stage >= 6:
            push(UnitType.CRUISER)
        if stage >= 5:
            push(UnitType.FIGHTER)
        if stage >= 4:
            push(UnitType.ANTISUBMARINE_HELI)
        if stage >= 3:
            push(UnitType.DESTROYER)
        if stage >= 2:
            push(UnitType.AAGUNSHIP)
        if stage >= 1:
            push(UnitType.TORPEDOBOMBER)
            # torpedo boat имеет те же параметры что и torpedobomber
            rank -= 1
            push(UnitType.TORPEDO_BOAT)

        # Уровень 0 — базовые юниты (всегда)
        push(UnitType.FRIGATE)
        rank -= 1; push(UnitType.HELICOPTER)
        rank -= 1; push(UnitType.BOAT)
        rank -= 1
        rank += 1
        count    = multiplier * (difficulty + rank)
        interval = total_time / count
        result.append(CounterAttackData(UnitType.SUBMARINE, int(count / 3), int(interval * 3)))

        return result


# ============================================================
# БАЗА ДАННЫХ AI (боссы по уровням)
# ============================================================

BOSS_BY_STAGE = {
    0:  UnitType.POTEMKIN,
    1:  UnitType.DREADNOUGHT,
    2:  UnitType.RICHELIEU,
    3:  UnitType.NAGATO,
    4:  UnitType.VANGUARD,
    5:  UnitType.BISMARCK,
    6:  UnitType.IOWA,
    7:  UnitType.HINDENBURG,
    8:  UnitType.NIMITZ,
    9:  UnitType.NAUTILUS,
    10: UnitType.YAMATO,
    11: UnitType.FORTRESSUNKNOWN,
}

BOSS_NAMES = {
    UnitType.POTEMKIN:        "Potemkin",
    UnitType.DREADNOUGHT:     "Dreadnought",
    UnitType.RICHELIEU:       "Richelieu",
    UnitType.NAGATO:          "Nagato",
    UnitType.VANGUARD:        "Vanguard",
    UnitType.BISMARCK:        "Bismarck",
    UnitType.IOWA:            "Iowa",
    UnitType.HINDENBURG:      "Hindenburg",
    UnitType.NIMITZ:          "Nimitz",
    UnitType.NAUTILUS:        "Nautilus",
    UnitType.YAMATO:          "Yamato",
    UnitType.FORTRESSUNKNOWN: "???",
}


class AIDatabase:
    @staticmethod
    def get_data(stage: int) -> AIData:
        data           = AIData()
        data.stageNum  = stage
        data.bossType  = BOSS_BY_STAGE.get(stage, UnitType.FORTRESSUNKNOWN)
        data.cadArray  = CounterAttackDataBase.get_data(stage, 0)
        data.cadArray1 = CounterAttackDataBase.get_data(stage, 1)
        data.cadArray2 = CounterAttackDataBase.get_data(stage, 2)
        return data


# ============================================================
# ДОСТУПНЫЕ ЮНИТЫ НА УРОВНЕ (из AvailableUnitData.as)
# ============================================================
#
# Оригинальная таблица (порт data[] из AvailableUnitData.as):
#
#   [unit_type,          key,   icon_frm, avail_stage, interval]
#
#   avail_stage = -1  → доступно с самого начала (стейдж 0)
#   avail_stage =  N  → разблокируется после прохождения стейджа N
#   interval         → каждые N фреймов AI спавнит этот юнит
#
# Батареи (BATTERY, UNDERWATER_BATTERY, FORTRESS) в AI-спавне
# не участвуют — фильтруются в конструкторе оригинала.
#
# Полная таблица (20 записей):
#
#  Юнит                  | Клавиша | Иконка | Стейдж | Интервал
#  ----------------------|---------|--------|--------|----------
#  Patrol Boat           |   1     |   1    |  -1    |   131
#  Frigate               |   2     |   2    |  -1    |  1121
#  Submarine             |   3     |   3    |  -1    |   921
#  Helicopter            |   4     |   4    |  -1    |  1999
#  AA-Gun Ship           |   5     |   7    |  -1    |  1022
#  Torpedo Boat          |   6     |   5    |   0    |   172
#  Torpedo Bomber        |   7     |   6    |   0    |  1699
#  Destroyer             |   8     |   8    |   2    |  2019
#  Anti-sub Helicopter   |   9     |   9    |   3    |  3011
#  Fighter               |   0     |  10    |   4    |  3123
#  Cruiser               |   Q     |  11    |   5    |  2699
#  Battleship            |   W     |  12    |   6    | 19111
#  Atomic Submarine      |   E     |  13    |   7    |  8999
#  Bomber                |   R     |  14    |   8    | 12111
#  Carrier               |   T     |  15    |   9    | 19499
#  Artillery Battery     |   Y     |  16    |  -1    |   (0=battery)
#  MachineGun Battery    |   U     |  17    |   1    |   (0=battery)
#  Missile Battery       |   I     |  18    |   3    |   (0=battery)
#  Torpedo Battery       |   O     |  19    |   5    |   (0=battery)
#  Sub-Fortress          |   P     |  20    |  10    |   (0=battery)

# Полная таблица иконок (для HUD — все 20 слотов включая батареи)
AVAILABLE_UNIT_ICON_DATA = [
    # [unit_type,                    key,  icon_frm, avail_stage, interval]
    [UnitType.BOAT,               "1",  1,  -1,   131],
    [UnitType.FRIGATE,            "2",  2,  -1,  1121],
    [UnitType.SUBMARINE,          "3",  3,  -1,   921],
    [UnitType.HELICOPTER,         "4",  4,  -1,  1999],
    [UnitType.AAGUNSHIP,          "5",  7,  -1,  1022],
    [UnitType.TORPEDO_BOAT,       "6",  5,   0,   172],
    [UnitType.TORPEDOBOMBER,      "7",  6,   0,  1699],
    [UnitType.DESTROYER,          "8",  8,   2,  2019],
    [UnitType.ANTISUBMARINE_HELI, "9",  9,   3,  3011],
    [UnitType.FIGHTER,            "0", 10,   4,  3123],
    [UnitType.CRUISER,            "Q", 11,   5,  2699],
    [UnitType.BATTLESHIP,         "W", 12,   6, 19111],
    [UnitType.ATOMICSUBMARINE,    "E", 13,   7,  8999],
    [UnitType.BOMBER,             "R", 14,   8, 12111],
    [UnitType.CARRIER,            "T", 15,   9, 19499],
    # Батареи (interval=0, не участвуют в AI-спавне)
    [UnitType.BATTERY,            "Y", 16,  -1,     0],
    [UnitType.MACHINEGUN_BATTERY, "U", 17,   1,     0],
    [UnitType.MISSILE_BATTERY,    "I", 18,   3,     0],
    [UnitType.TORPEDO_BATTERY,    "O", 19,   5,     0],
    [UnitType.SUBFORTRESS,        "P", 20,  10,     0],
]

# Индексы колонок
CL_TYPE      = 0
CL_KEY       = 1
CL_ICON_FRM  = 2
CL_AVLSTAGE  = 3
CL_INTERVAL  = 4

# Категории батарей (фильтруются из AI-спавна)
_BATTERY_CATEGORIES = (
    0x2000 | 0x800 | 0x1000  # BATTERY | UNDERWATER_BATTERY | FORTRESS
)

# Строим отсортированный список AiUnitData для AI (только боевые юниты)
# avStNum = -1 означает доступно всегда → для сортировки используем -1
_AI_UNIT_DATA_ALL: list = []
for _row in AVAILABLE_UNIT_ICON_DATA:
    _utype = _row[CL_TYPE]
    # Пропускаем батареи/крепости (interval=0 и они батареи)
    if _row[CL_INTERVAL] == 0:
        continue
    _ud = AiUnitData(_utype, _row[CL_INTERVAL], _row[CL_AVLSTAGE])
    _AI_UNIT_DATA_ALL.append(_ud)
# Сортируем по avStNum как в оригинале (Array.NUMERIC)
_AI_UNIT_DATA_ALL.sort(key=lambda u: u.avStNum)


def get_stage_unit_data(stage: int) -> list:
    """
    Возвращает список AiUnitData доступных на данном стейдже.
    Порт AvailableUnitData.getStageUnitData():
      включает юниты у которых avStNum < stage
      (т.е. avStNum = -1 всегда, avStNum = 0 начиная со стейджа 1, и т.д.)
    """
    result = []
    for ud in _AI_UNIT_DATA_ALL:
        if ud.avStNum >= stage:
            break
        result.append(ud)
    return result


def get_icon_data() -> list:
    """Возвращает полную таблицу иконок для HUD (все 20 слотов)."""
    return AVAILABLE_UNIT_ICON_DATA


# ============================================================
# БАЗОВЫЙ AI
# ============================================================

class AI:
    """
    Порт game.ai.AI — базовый класс.
    Все конкретные AI наследуются от него.
    """

    # Таблица всех типов юнитов
    UNIT_TYPES = [
        UnitType.BOAT, UnitType.AAGUNSHIP, UnitType.HELICOPTER,
        UnitType.SUBMARINE, UnitType.BATTLESHIP, UnitType.TORPEDOBOMBER,
        UnitType.FRIGATE, UnitType.CRUISER, UnitType.TORPEDO_BOAT,
        UnitType.DESTROYER, UnitType.FIGHTER, UnitType.ANTISUBMARINE_HELI,
        UnitType.ATOMICSUBMARINE, UnitType.BOMBER, UnitType.CARRIER,
    ]

    def __init__(self, spawn_callback=None):
        """
        spawn_callback(unit_type, side, x) — вызывается при спавне юнита.
        side: GameConstants.ENEMY_FLG или FRIEND_FLG
        x: позиция появления
        """
        self._spawn_cb  = spawn_callback or (lambda t, s, x: None)
        self.stage_units = []
        self.aidata      = None
        self._init()

    def _init(self):
        self.stage_units = get_stage_unit_data(GameParams.stageNum)

    def new_unit(self, unit_type: int, side: int):
        """Спавн юнита. Позиция зависит от стороны."""
        # Заглушка ширины юнита — заменить реальными данными
        img_width = 64
        if side == GameConstants.ENEMY_FLG:
            x = GameConstants.SCREEN_WIDTH + img_width / 2
        else:
            x = -img_width / 2
        self._spawn_cb(unit_type, side, x)

    def enemy_fortress_life_check(self, life_ratio: float):
        """Вызывается при изменении HP вражеской базы."""
        pass

    def boss_destroyed(self):
        """Вызывается когда босс уничтожен."""
        pass

    def enter_frame(self):
        """Игровой цикл — вызывать каждый фрейм."""
        pass


# ============================================================
# AI DEMO — автобитва на главном меню
# ============================================================

class AIDemo(AI):
    MAX_UNIT_NUM     = 200
    MAX_DIFF_NUM     = 20
    NEW_UNIT_INTERVAL = 30

    def __init__(self, spawn_callback=None):
        self._frm_cnt   = 0
        self._unit_array = []
        super().__init__(spawn_callback)
        self._unit_array = get_stage_unit_data(GameParams.maxCleardStageNum + 1)

    def _random_unit(self, side: int):
        unit = random.choice(self._unit_array)
        self.new_unit(unit.unitTYpe, side)

    def enter_frame(self):
        super().enter_frame()
        diff = GameParams.friendNum - GameParams.enemyNum

        if self._frm_cnt % self.NEW_UNIT_INTERVAL == 0:
            if GameParams.friendNum < self.MAX_UNIT_NUM and diff < self.MAX_DIFF_NUM:
                self._random_unit(GameConstants.FRIEND_FLG)
        elif self._frm_cnt % self.NEW_UNIT_INTERVAL == 1:
            if GameParams.enemyNum < self.MAX_UNIT_NUM and -diff < self.MAX_DIFF_NUM:
                self._random_unit(GameConstants.ENEMY_FLG)

        self._frm_cnt += 1


# ============================================================
# AI SURVIVAL — бесконечное ускорение
# ============================================================

class AISurvival(AI):
    RATE_DEC_FACTOR = 1.1e-8
    MAX_ENEMY_NUM   = 200
    MIN_INTERVAL    = 10

    def __init__(self, stage: int, spawn_callback=None):
        self._frm_cnt      = 0
        self._interval_rate = 1.0
        self._dec_factor    = 1.0
        super().__init__(spawn_callback)
        self.aidata          = AIDatabase.get_data(stage)
        self._unit_array     = get_stage_unit_data(self.aidata.stageNum)

    def enter_frame(self):
        super().enter_frame()
        self._frm_cnt     += 1
        self._dec_factor  -= self.RATE_DEC_FACTOR
        self._interval_rate *= self._dec_factor
        self._normal_attack()

    def _normal_attack(self):
        if GameParams.enemyNum > self.MAX_ENEMY_NUM:
            return
        for unit in self._unit_array:
            interval = int(unit.interval * (1 - self.aidata.stageNum * 0.02) * self._interval_rate)
            interval = max(interval, self.MIN_INTERVAL)
            if interval > 0 and self._frm_cnt % interval == 0:
                self.new_unit(unit.unitTYpe, GameConstants.ENEMY_FLG)


# ============================================================
# AI CLIMAX — боссы + волны по таймеру
# ============================================================

class AIClimax(AI):
    BOSS_WAIT = 300

    STATUS_NORMAL        = 1
    STATUS_COUNTER_ATTACK = 2
    STATUS_BOSS_DESTROYED = 4

    COUNTER_ATTACK_RATE = [1, 1, 1, 1, 1, 0.8, 0.4, 0.7, 0.7, 0.335, 0.44, 0.775]

    def __init__(self, stage: int, spawn_callback=None, on_boss=None, on_boss_destroyed=None):
        self._frm_cnt   = 0
        self._status    = self.STATUS_NORMAL
        self._boss_name = ""
        self._on_boss            = on_boss or (lambda name: None)
        self._on_boss_destroyed  = on_boss_destroyed or (lambda name: None)
        super().__init__(spawn_callback)
        self.aidata       = AIDatabase.get_data(stage)
        self._unit_array  = get_stage_unit_data(self.aidata.stageNum)
        self._scale_counter_attack()

    def _scale_counter_attack(self):
        rate = self.COUNTER_ATTACK_RATE[GameParams.stageNum]
        for arr in [self.aidata.cadArray, self.aidata.cadArray1, self.aidata.cadArray2]:
            for ca in arr:
                ca.interval = int(ca.interval * rate)
                ca.unitNum  = int(ca.unitNum  / rate)
                if ca.interval == 0:
                    ca.interval = 1

    def boss_destroyed(self):
        super().boss_destroyed()
        self._status |= self.STATUS_BOSS_DESTROYED
        self._on_boss_destroyed(self._boss_name)

    def _spawn_boss(self):
        boss_type       = self.aidata.bossType
        self._boss_name = BOSS_NAMES.get(boss_type, "???")
        img_width       = 128   # заглушка — заменить реальной шириной босса
        x = GameConstants.SCREEN_WIDTH + img_width / 2
        self._spawn_cb(boss_type, GameConstants.ENEMY_FLG, x)
        self._on_boss(self._boss_name)

    def _normal_attack(self):
        for unit in self._unit_array:
            interval = int(unit.interval * (1 - self.aidata.stageNum * 0.02))
            if self._status & self.STATUS_BOSS_DESTROYED:
                interval *= 2
            if interval > 0 and self._frm_cnt % interval == 0:
                self.new_unit(unit.unitTYpe, GameConstants.ENEMY_FLG)

    def _counter_attack(self):
        for ca in reversed(self.aidata.cadArray):
            if ca.unitNum <= 0:
                self.aidata.cadArray.remove(ca)
            elif ca.interval > 0 and self._frm_cnt % ca.interval == 0:
                self.new_unit(ca.unitType, GameConstants.ENEMY_FLG)
                ca.unitNum -= 1

    def enter_frame(self):
        self._frm_cnt += 1
        super().enter_frame()

        if self._status & self.STATUS_NORMAL:
            self._normal_attack()

        if (self._status & self.STATUS_COUNTER_ATTACK) and \
           not (self._status & self.STATUS_BOSS_DESTROYED):
            self._counter_attack()

        if self._frm_cnt == self.BOSS_WAIT:
            self._status |= self.STATUS_COUNTER_ATTACK
            self._spawn_boss()


# ============================================================
# AI STAGE — основная кампания (триггеры по HP базы)
# ============================================================

class AIStage(AI):
    STATUS_NORMAL         = 1
    STATUS_COUNTER_ATTACK = 2
    STATUS_BOSS_DESTROYED = 4

    BGM_LENGTH             = 30 * 20
    COUNTER_ATTACK_INTERVAL = 30

    INTERVAL_RATE_HARD      = 0.77
    INTERVAL_RATE_NORMAL    = 1.0
    INTERVAL_RATE_NORMAL_EN = 1.1
    INTERVAL_RATE_EASY      = 1.3

    COUNTER_ATTACK_RATE = [0.3, 0.3, 0.3, 0.3, 0.3, 0.44, 0.72, 0.8, 0.91, 0.95, 0.97, 1]

    def __init__(self, stage: int, spawn_callback=None, on_boss=None, on_boss_destroyed=None):
        self._frm_cnt               = 0
        self._bgm_cnt               = 0
        self._counter_attack_cnt    = 0
        self._counter_attack_wave_cnt = 1
        self._interval_rate         = 1.0
        self._status                = self.STATUS_NORMAL
        self._ca_data               = []
        self._boss_name             = ""
        self._on_boss               = on_boss or (lambda name: None)
        self._on_boss_destroyed     = on_boss_destroyed or (lambda name: None)
        super().__init__(spawn_callback)
        self.aidata      = AIDatabase.get_data(stage)
        self._unit_array = get_stage_unit_data(self.aidata.stageNum)
        self._difficulty_set()

    def _difficulty_set(self):
        mode = GameParams.gameMode
        if mode == GameConstants.GAME_MODE_CMPN_EASY:
            self._interval_rate      = self.INTERVAL_RATE_EASY
            self._counter_attack_cnt = 2
        elif mode == GameConstants.GAME_MODE_CMPN_HARD:
            self._interval_rate      = self.INTERVAL_RATE_HARD
            self._counter_attack_cnt = 0
        else:  # NORMAL
            self._interval_rate = self.INTERVAL_RATE_NORMAL
            if GameParams.language == GameConstants.ENGLISH:
                self._interval_rate = self.INTERVAL_RATE_NORMAL_EN
            self._counter_attack_cnt = 1

        rate = self.COUNTER_ATTACK_RATE[GameParams.stageNum] * self._interval_rate
        self._scale_counter_attack(rate)

    def _scale_counter_attack(self, rate: float):
        for i, arr in enumerate([self.aidata.cadArray, self.aidata.cadArray1, self.aidata.cadArray2]):
            r = rate * (1 + i * 0.1)
            for ca in arr:
                ca.interval = int(ca.interval * r)
                ca.unitNum  = int(ca.unitNum  / r)
                if ca.interval == 0:
                    ca.interval = 1

    def enemy_fortress_life_check(self, life_ratio: float):
        super().enemy_fortress_life_check(life_ratio)
        if self._counter_attack_cnt == 0 and life_ratio < 0.8:
            self._counter_attack_start(2)
        elif self._counter_attack_cnt == 1 and life_ratio < 0.5:
            self._counter_attack_start(1)
        elif self._counter_attack_cnt == 2 and life_ratio < 0.1:
            self._counter_attack_start(0)
            self._spawn_boss()

    def _counter_attack_start(self, variant: int):
        self._status |= self.STATUS_COUNTER_ATTACK
        self._counter_attack_cnt += 1
        if variant == 0:
            self._ca_data = self.aidata.cadArray
        elif variant == 1:
            self._ca_data = self.aidata.cadArray1
        else:
            self._ca_data = self.aidata.cadArray2
        self._counter_attack_start_wave()
        self._counter_attack_wave_cnt = -self.COUNTER_ATTACK_INTERVAL
        self._bgm_cnt = 0

    def _counter_attack_start_wave(self):
        for ca in reversed(self._ca_data):
            self.new_unit(ca.unitType, GameConstants.ENEMY_FLG)

    def _spawn_boss(self):
        boss_type       = self.aidata.bossType
        self._boss_name = BOSS_NAMES.get(boss_type, "???")
        img_width = 128
        x = GameConstants.SCREEN_WIDTH + img_width / 2
        self._spawn_cb(boss_type, GameConstants.ENEMY_FLG, x)
        self._on_boss(self._boss_name)

    def boss_destroyed(self):
        super().boss_destroyed()
        self._status |= self.STATUS_BOSS_DESTROYED
        self._on_boss_destroyed(self._boss_name)

    def _normal_attack(self):
        for unit in self._unit_array:
            interval = int(unit.interval * (1 - self.aidata.stageNum * 0.02) * self._interval_rate)
            if self._status & self.STATUS_BOSS_DESTROYED:
                interval *= 2
            if interval > 0 and self._frm_cnt % interval == 0:
                self.new_unit(unit.unitTYpe, GameConstants.ENEMY_FLG)

    def _counter_attack(self):
        for ca in reversed(self._ca_data):
            if ca.unitNum <= 0:
                self._ca_data.remove(ca)
            elif ca.interval > 0 and self._frm_cnt % ca.interval == 0:
                self.new_unit(ca.unitType, GameConstants.ENEMY_FLG)
                ca.unitNum -= 1

    def enter_frame(self):
        self._frm_cnt += 1
        super().enter_frame()

        if self._status & self.STATUS_NORMAL:
            self._normal_attack()

        if (self._status & self.STATUS_COUNTER_ATTACK) and \
           not (self._status & self.STATUS_BOSS_DESTROYED):
            self._counter_attack()

        self._bgm_cnt               += 1
        self._counter_attack_wave_cnt += 1
        if self._counter_attack_wave_cnt == 0:
            self._counter_attack_start_wave()


# ============================================================
# БЫСТРЫЙ ТЕСТ
# ============================================================

if __name__ == "__main__":
    spawned = []

    def on_spawn(unit_type, side, x):
        side_str = "ENEMY" if side == GameConstants.ENEMY_FLG else "FRIEND"
        name = {v: k for k, v in UnitType.__dict__.items() if isinstance(v, int)}.get(unit_type, "???")
        spawned.append((unit_type, side_str, x))
        print(f"  SPAWN [{side_str:6}] {name:<22} x={x:.0f}")

    print("=" * 55)
    print("  ТЕСТ: AISurvival — уровень 3, 120 фреймов")
    print("=" * 55)
    GameParams.stageNum = 3
    ai = AISurvival(3, spawn_callback=on_spawn)
    for _ in range(120):
        ai.enter_frame()
    print(f"\n  Всего заспавнено: {len(spawned)} юнитов\n")

    print("=" * 55)
    print("  ТЕСТ: AIClimax — уровень 5, до появления босса")
    print("=" * 55)
    spawned.clear()
    GameParams.stageNum = 5

    def on_boss(name):
        print(f"\n  *** БОСС ПОЯВИЛСЯ: {name} ***\n")

    ai2 = AIClimax(5, spawn_callback=on_spawn, on_boss=on_boss)
    for f in range(310):
        ai2.enter_frame()
    print(f"\n  Всего заспавнено: {len(spawned)} юнитов\n")

    print("=" * 55)
    print("  ТЕСТ: AIStage HARD — триггер контратаки по HP")
    print("=" * 55)
    spawned.clear()
    GameParams.stageNum = 2
    GameParams.gameMode = GameConstants.GAME_MODE_CMPN_HARD
    ai3 = AIStage(2, spawn_callback=on_spawn, on_boss=on_boss)
    for _ in range(50):
        ai3.enter_frame()
    print("\n  --- HP базы упало до 45% ---")
    ai3.enemy_fortress_life_check(0.45)
    for _ in range(50):
        ai3.enter_frame()
    print(f"\n  Всего заспавнено: {len(spawned)} юнитов")
