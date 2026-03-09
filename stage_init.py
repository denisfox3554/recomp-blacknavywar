"""
stage_init.py — порт StageInit.as из Navy Battle Flash

Инициализирует каждый стейдж:
  1. Создаёт крепости (Fortress) обеих сторон
  2. Устанавливает уровень вражеской крепости (level = stage // 2)
  3. На стейджах 10-11: добавляет подводную крепость (FortressSub)
  4. Расставляет батареи игрока и врага по слотам

Три режима инициализации батарей игрока:
  initFriendBattery      — Campaign (только Artillery Battery, 2-4 слота)
  initFriendBatteryDemo  — Demo/Survival (Artillery + TorpedoBattery, растёт с уровнем)
  initFriendBatteryClimax— Climax (fall-through, много батарей с первых уровней)

Батареи врага (initEnemyBattery):
  Стейджи 0-3:  MachineGun + Missile
  Стейджи 4-9:  MachineGun + Missile (больше слотов)
  Стейджи 9+:   + TorpedoBattery
  Стейджи 10-11: максимальный набор

Слоты батарей (setBattery): 0-13 = Artillery/MachineGun/Missile слоты,
                              14-17 = подводные слоты (TorpedoBattery)

Climax особенность:
  - Вражеская крепость стартует с 10% HP (hitBullet damage = life * 0.9)
  - Это делает Climax сложнее — босс появляется почти сразу
"""

# ─────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────
FRIEND_FLG = 0
ENEMY_FLG  = 1

GAME_MODE_CLIMAX = 16

# Типы батарей
UNIT_TYPE_BATTERY            = 0x0800
UNIT_TYPE_MACHINEGUN_BATTERY = 0x0801
UNIT_TYPE_MISSILE_BATTERY    = 0x0802
UNIT_TYPE_TORPEDOBATTERY     = 0x0803


# ─────────────────────────────────────────────
# Таблицы батарей (слот → тип) для каждого стейджа
# ─────────────────────────────────────────────

# Campaign — батареи игрока (только Artillery, слоты 7-10)
_FRIEND_BATTERY_CAMPAIGN = {
    0:  [(9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
    1:  [(9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
    2:  [(9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
    3:  [(9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
    4:  [(8, UNIT_TYPE_BATTERY), (9, UNIT_TYPE_BATTERY),  (10, UNIT_TYPE_BATTERY)],
    5:  [(8, UNIT_TYPE_BATTERY), (9, UNIT_TYPE_BATTERY),  (10, UNIT_TYPE_BATTERY)],
    6:  [(8, UNIT_TYPE_BATTERY), (9, UNIT_TYPE_BATTERY),  (10, UNIT_TYPE_BATTERY)],
    7:  [(8, UNIT_TYPE_BATTERY), (9, UNIT_TYPE_BATTERY),  (10, UNIT_TYPE_BATTERY)],
    8:  [(8, UNIT_TYPE_BATTERY), (9, UNIT_TYPE_BATTERY),  (10, UNIT_TYPE_BATTERY)],
    9:  [(7, UNIT_TYPE_BATTERY), (8, UNIT_TYPE_BATTERY),
         (9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
    10: [(7, UNIT_TYPE_BATTERY), (8, UNIT_TYPE_BATTERY),
         (9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
    11: [(7, UNIT_TYPE_BATTERY), (8, UNIT_TYPE_BATTERY),
         (9, UNIT_TYPE_BATTERY), (10, UNIT_TYPE_BATTERY)],
}

# Demo/Survival — батареи игрока (Artillery + TorpedoBattery)
# Растёт с каждым стейджем, максимум на 11: слоты 0-13 + торпеды 14-17
_B  = UNIT_TYPE_BATTERY
_TB = UNIT_TYPE_TORPEDOBATTERY
_FRIEND_BATTERY_DEMO = {
    0:  [(9,_B),(10,_B)],
    1:  [(8,_B),(9,_B),(10,_B)],
    2:  [(7,_B),(8,_B),(9,_B),(10,_B)],
    3:  [(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    4:  [(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    5:  [(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    6:  [(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    7:  [(1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    8:  [(0,_B),(1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    9:  [(0,_B),(1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B),
         (14,_TB)],
    10: [(0,_B),(1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B),
         (11,_B),(12,_B),(14,_TB),(15,_TB)],
    11: [(0,_B),(1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B),
         (11,_B),(12,_B),(13,_B),(14,_TB),(15,_TB),(16,_TB),(17,_TB)],
}

# Climax — батареи игрока (fall-through: стейдж N включает все уровни ниже)
# Вражеская крепость стартует с 10% HP
_MG = UNIT_TYPE_MACHINEGUN_BATTERY
_MS = UNIT_TYPE_MISSILE_BATTERY
_FRIEND_BATTERY_CLIMAX = {
    # Каждый уровень включает всё что ниже (fall-through в оригинале)
    0:  [(9,_B),(10,_B)],
    1:  [(8,_B),(9,_B),(10,_B)],
    2:  [(7,_B),(8,_B),(9,_B),(10,_B)],
    3:  [(7,_B),(8,_B),(9,_B),(10,_B)],
    4:  [(7,_B),(8,_B),(9,_B),(10,_B)],
    5:  [(7,_B),(8,_B),(9,_B),(10,_B)],
    6:  [(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    7:  [(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    8:  [(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    9:  [(14,_TB),(1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    10: [(15,_TB),(16,_TB),(0,_B),(14,_TB),(1,_B),(2,_B),(3,_B),(4,_B),
         (5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
    11: [(11,_B),(12,_B),(13,_B),(17,_TB),(15,_TB),(16,_TB),(0,_B),(14,_TB),
         (1,_B),(2,_B),(3,_B),(4,_B),(5,_B),(6,_B),(7,_B),(8,_B),(9,_B),(10,_B)],
}

# Вражеские батареи (MachineGun + Missile + TorpedoBattery на поздних стейджах)
_ENEMY_BATTERY = {
    0:  [(5,_MG),(6,_MG),(7,_MG)],
    1:  [(5,_MG),(6,_MG),(7,_MG),(8,_MS),(9,_MS),(10,_MS)],
    2:  [(4,_MG),(5,_MG),(6,_MG),(7,_MG),(8,_MS),(9,_MS),(10,_MS)],
    3:  [(4,_MG),(5,_MG),(6,_MG),(7,_MG),(8,_MS),(9,_MS),(10,_MS)],
    4:  [(3,_MG),(4,_MG),(5,_MG),(6,_MG),(7,_MS),(8,_MS),(9,_MS),(10,_MS)],
    5:  [(3,_MG),(4,_MG),(5,_MG),(6,_MG),(7,_MS),(8,_MS),(9,_MS),(10,_MS)],
    6:  [(2,_MG),(3,_MG),(4,_MG),(5,_MG),(6,_MS),(7,_MS),(8,_MS),(9,_MS),(10,_MS)],
    7:  [(2,_MG),(3,_MG),(4,_MG),(5,_MG),(6,_MS),(7,_MS),(8,_MS),(9,_MS),(10,_MS)],
    8:  [(1,_MG),(2,_MG),(3,_MG),(4,_MG),(5,_MG),(6,_MS),(7,_MS),(8,_MS),(9,_MS),(10,_MS)],
    9:  [(1,_MG),(2,_MG),(3,_MG),(4,_MG),(5,_MG),(6,_MS),(7,_MS),(8,_MS),(9,_MS),(10,_MS),
         (14,_TB)],
    10: [(0,_MG),(1,_MG),(2,_MG),(3,_MG),(4,_MG),(5,_MS),(6,_MS),(7,_MS),(8,_MS),(9,_MS),
         (10,_MS),(11,_MS),(12,_MG),(14,_TB),(15,_TB)],
    11: [(0,_MG),(1,_MG),(2,_MG),(3,_MG),(4,_MG),(5,_MS),(6,_MS),(7,_MS),(8,_MS),(9,_MS),
         (10,_MS),(11,_MG),(12,_MS),(13,_MS),(14,_TB),(15,_TB),(16,_TB),(17,_TB)],
}


# ─────────────────────────────────────────────
# Главный класс инициализации
# ─────────────────────────────────────────────

class StageInit:
    """
    Порт StageInit.as.

    Использование:
        from stage_init import StageInit
        StageInit.init_stage(stage_num, game_mode, battery_control,
                             spawn_fortress, spawn_fortress_sub)

    Параметры:
        stage_num       — номер стейджа 0-11
        game_mode       — константа режима игры
        battery_control — объект с методом set_battery(slot, faction, btype)
        spawn_fortress(faction) → UnitFortress
        spawn_fortress_sub(faction) → UnitFortressSub (опционально)
    """

    @staticmethod
    def init_stage(stage_num: int,
                   game_mode: int,
                   battery_control,
                   spawn_fortress,
                   spawn_fortress_sub=None,
                   is_demo: bool = False):
        """
        Главный метод инициализации стейджа.

        is_demo=True  → используется в Demo/Survival (GameParams.stageNum < 0)
        game_mode == GAME_MODE_CLIMAX → Climax режим
        """
        stage = min(stage_num, 11)

        # Создаём крепости обеих сторон
        friend_fortress = spawn_fortress(FRIEND_FLG)
        enemy_fortress  = spawn_fortress(ENEMY_FLG)

        # Уровень вражеской крепости = stage // 2
        # (влияет на HP и количество слотов батарей крепости)
        enemy_fortress.level = stage // 2

        if is_demo:
            # Demo / Survival
            friend_fortress.level = enemy_fortress.level
            if stage > 9 and spawn_fortress_sub:
                spawn_fortress_sub(FRIEND_FLG)
            StageInit._set_batteries(
                _FRIEND_BATTERY_DEMO.get(stage, []), battery_control)

        elif game_mode == GAME_MODE_CLIMAX:
            # Climax: вражеская крепость стартует с 10% HP
            enemy_fortress.take_damage(enemy_fortress.life * 0.9)
            if stage > 10 and spawn_fortress_sub:
                spawn_fortress_sub(FRIEND_FLG)
            StageInit._set_batteries(
                _FRIEND_BATTERY_CLIMAX.get(stage, []), battery_control)

        else:
            # Campaign (Easy / Normal / Hard)
            StageInit._set_batteries(
                _FRIEND_BATTERY_CAMPAIGN.get(stage, []), battery_control)

        # Подводная крепость врага на стейджах 10-11
        if stage > 9 and spawn_fortress_sub:
            spawn_fortress_sub(ENEMY_FLG)

        # Вражеские батареи (всегда)
        StageInit._set_batteries(
            _ENEMY_BATTERY.get(stage, []), battery_control,
            faction=ENEMY_FLG)

        return friend_fortress, enemy_fortress

    @staticmethod
    def _set_batteries(slots: list, battery_control, faction: int = FRIEND_FLG):
        """Устанавливает батареи в указанные слоты."""
        for slot, btype in slots:
            battery_control.set_battery(slot, faction, btype)

    # ── Удобные методы для прямого вызова ────────────────────────────

    @staticmethod
    def get_friend_batteries_campaign(stage: int) -> list:
        """Возвращает список (slot, type) для Campaign."""
        return _FRIEND_BATTERY_CAMPAIGN.get(min(stage, 11), [])

    @staticmethod
    def get_friend_batteries_demo(stage: int) -> list:
        """Возвращает список (slot, type) для Demo/Survival."""
        return _FRIEND_BATTERY_DEMO.get(min(stage, 11), [])

    @staticmethod
    def get_friend_batteries_climax(stage: int) -> list:
        """Возвращает список (slot, type) для Climax."""
        return _FRIEND_BATTERY_CLIMAX.get(min(stage, 11), [])

    @staticmethod
    def get_enemy_batteries(stage: int) -> list:
        """Возвращает список (slot, type) для врага."""
        return _ENEMY_BATTERY.get(min(stage, 11), [])

    @staticmethod
    def has_friend_sub_fortress(stage: int, game_mode: int,
                                is_demo: bool = False) -> bool:
        """Нужна ли подводная крепость игроку."""
        if is_demo:
            return stage > 9
        if game_mode == GAME_MODE_CLIMAX:
            return stage > 10
        return False

    @staticmethod
    def has_enemy_sub_fortress(stage: int) -> bool:
        """Нужна ли подводная крепость врагу."""
        return stage > 9


# ─────────────────────────────────────────────
# Краткая сводка по стейджам
# ─────────────────────────────────────────────

def print_stage_summary():
    """Выводит таблицу батарей и крепостей по всем стейджам."""
    print(f"{'Stage':<6} {'FortLvl':<8} {'EnemySub':<9} "
          f"{'Friend batt (Camp)':<22} {'Enemy batt'}")
    print("-" * 80)
    type_names = {
        UNIT_TYPE_BATTERY:            "Art",
        UNIT_TYPE_MACHINEGUN_BATTERY: "MG",
        UNIT_TYPE_MISSILE_BATTERY:    "Mis",
        UNIT_TYPE_TORPEDOBATTERY:     "Torp",
    }
    for s in range(12):
        fb = _FRIEND_BATTERY_CAMPAIGN.get(s, [])
        eb = _ENEMY_BATTERY.get(s, [])
        fb_str = " ".join(f"{sl}:{type_names[t]}" for sl,t in fb)
        eb_str = " ".join(f"{sl}:{type_names[t]}" for sl,t in eb)
        sub = "YES" if s > 9 else "-"
        print(f"  {s:<4} {s//2:<8} {sub:<9} {fb_str:<22} {eb_str}")


if __name__ == "__main__":
    print_stage_summary()
