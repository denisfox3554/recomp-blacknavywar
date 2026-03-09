"""
special_attacks.py — порт системы специальных атак из Navy Battle Flash

5 специальных атак (клавиши A/S/D/F/G), разблокируются на стейджах 1/3/5/7/9.

┌─────────────────────────────────────────────────────────────────────────────┐
│  Клавиша │ Название             │ Тип                │ Разблок. на стейдже │
├─────────────────────────────────────────────────────────────────────────────┤
│    A     │ High Altitude Bomb   │ Ковровая бомбардировка │      1           │
│    S     │ EMP                  │ Паралич врагов     │      3           │
│    D     │ Floating Mine        │ Минное поле        │      5           │
│    F     │ Satellite Attack     │ Лазерный орбитальный удар │   7      │
│    G     │ Atomic Bomb          │ Ядерный взрыв      │      9           │
└─────────────────────────────────────────────────────────────────────────────┘

Каждая атака масштабируется навыком (Skills.getSkill → +10% за уровень).
"""

import math
import random
import pygame
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from unit_system import UnitBase

# ─────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────
SCREEN_WIDTH  = 2400
SCREEN_HEIGHT = 450
STAGE_WIDTH   = 800
HORIZON_Y     = 300
G             = 0.3
FRIEND_FLG    = 0
ENEMY_FLG     = 1

# Индексы специальных атак
SA_HA_BOMB         = 0   # A
SA_EMP             = 1   # S
SA_FLOATING_MINE   = 2   # D
SA_SATELLITE       = 3   # F
SA_ATOMIC_BOMB     = 4   # G

SA_NAMES = {
    SA_HA_BOMB:       "High Altitude Bombing",
    SA_EMP:           "EMP",
    SA_FLOATING_MINE: "Floating Mine",
    SA_SATELLITE:     "Satellite Attack",
    SA_ATOMIC_BOMB:   "Atomic Bomb",
}

# Перезарядка (кадры) — нет перезарядки у спецатак в оригинале,
# иконки просто деактивируются пока идёт исполнение.
SA_RELOAD = {
    SA_HA_BOMB:       0,
    SA_EMP:           0,
    SA_FLOATING_MINE: 0,
    SA_SATELLITE:     0,
    SA_ATOMIC_BOMB:   0,
}


# ─────────────────────────────────────────────
# Глобальный навык (заглушка — интегрировать с Skills)
# ─────────────────────────────────────────────

class Skills:
    """Заглушка системы навыков. Заменить реальной реализацией."""
    _skills = {
        SA_HA_BOMB:       0,
        SA_EMP:           0,
        SA_FLOATING_MINE: 0,
        SA_SATELLITE:     0,
        SA_ATOMIC_BOMB:   0,
    }

    @classmethod
    def get_skill(cls, sa_type: int) -> int:
        return cls._skills.get(sa_type, 0)

    @classmethod
    def set_skill(cls, sa_type: int, level: int):
        cls._skills[sa_type] = level


# ─────────────────────────────────────────────
# A — Высотная бомбардировка (High Altitude Bombing)
# ─────────────────────────────────────────────

class SAHighAltitudeBombing:
    """
    Ковровая бомбардировка: 30 авиабомб (BulletBomb) по всей ширине поля.
    Бомбы падают сверху по одной каждые BOM_TIME=10 кадров.
    Интервал: (SCREEN_WIDTH - 2*190) / 30 = ~67px между бомбами.
    +10% бомб за уровень навыка.
    """
    _BASE_BOM_NUM = 30
    MARGIN        = 190
    BOM_TIME      = 10

    _bom_cnt  = 999
    _interval = 0
    _frm_cnt  = 0

    @classmethod
    def _bom_num(cls) -> int:
        return int(cls._BASE_BOM_NUM * (1 + 0.1 * Skills.get_skill(SA_HA_BOMB)))

    @classmethod
    def init(cls):
        cls._bom_cnt  = cls._bom_num() + 1
        cls._interval = 0
        cls._frm_cnt  = 0

    @classmethod
    def attack(cls):
        cls._bom_cnt  = 0
        cls._frm_cnt  = 0
        cls._interval = (SCREEN_WIDTH - 2 * cls.MARGIN) // cls._bom_num()

    @classmethod
    def enter_frame(cls):
        from bullet_system import BulletBomb
        if cls._bom_cnt > cls._bom_num():
            return
        if cls._frm_cnt % cls.BOM_TIME == 0:
            b = BulletBomb.new_instance(FRIEND_FLG)
            b.y = float(-b.bullet_data.img_size)
            b.x = float(cls.MARGIN + cls._bom_cnt * cls._interval)
            cls._bom_cnt += 1
        cls._frm_cnt += 1

    @classmethod
    def is_active(cls) -> bool:
        return cls._bom_cnt <= cls._bom_num()


# ─────────────────────────────────────────────
# S — ЭМИ (EMP)
# ─────────────────────────────────────────────

class SAEMP:
    """
    ЭМИ: парализует все вражеские юниты на 180 кадров (6 сек при 30fps).
    Пока empFlg=True → все враги-корабли останавливаются (vel.x=0 в setSpeed).
    +10% длительности за уровень навыка.
    Визуал: молния + синий экран на 8 кадров (ThunderMain / EMPBack).
    """
    _BASE_DURATION = 180

    _emp_flg = False
    _frm_cnt = 9999

    @classmethod
    def _duration(cls) -> int:
        return int(cls._BASE_DURATION * (1 + 0.1 * Skills.get_skill(SA_EMP)))

    @classmethod
    def init(cls):
        cls._emp_flg = False
        cls._frm_cnt = cls._duration() + 1

    @classmethod
    def attack(cls):
        cls._emp_flg = True
        cls._frm_cnt = 0
        # Визуал: вспышка молнии (реализовать в renderer)
        EMPVisual.trigger()

    @classmethod
    def enter_frame(cls):
        if not cls._emp_flg:
            return
        if cls._frm_cnt > cls._duration():
            cls._emp_flg = False
        if cls._frm_cnt == 8:
            EMPVisual.clear()
        cls._frm_cnt += 1

    @classmethod
    def emp_flg(cls) -> bool:
        return cls._emp_flg

    @classmethod
    def is_active(cls) -> bool:
        return cls._emp_flg


class EMPVisual:
    """Визуальный эффект ЭМИ — синяя вспышка на экране."""
    _active     = False
    _show_flash = False
    surface:    Optional[pygame.Surface] = None   # задаётся из renderer

    @classmethod
    def trigger(cls):
        cls._active     = True
        cls._show_flash = True

    @classmethod
    def clear(cls):
        cls._show_flash = False

    @classmethod
    def draw(cls, surface: pygame.Surface):
        if cls._show_flash:
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((100, 180, 255, 80))
            surface.blit(overlay, (0, 0))


# ─────────────────────────────────────────────
# D — Плавающие мины (Floating Mine)
# ─────────────────────────────────────────────

class SAFloatingMine:
    """
    Минное поле: 25 мин (BulletFloatingMine) запускаются с левого края.
    Мины равномерно распределяются по ширине поля через физику:
      - Время полёта в воздухе: t = 2*VY/G
      - Начальная горизонтальная скорость рассчитывается так, чтобы
        мины приземлились равномерно от MARGIN до SCREEN_WIDTH-MARGIN
    +10% мин за уровень навыка.
    """
    _BASE_BOM_NUM = 25
    MARGIN        = 250
    VY            = 7.0   # начальная вертикальная скорость вверх

    @classmethod
    def _bom_num(cls) -> int:
        return int(cls._BASE_BOM_NUM * (1 + 0.1 * Skills.get_skill(SA_FLOATING_MINE)))

    @classmethod
    def attack(cls):
        from bullet_system import BulletFloatingMine
        n   = cls._bom_num()
        # Время полёта одной мины до горизонта
        t   = 2 * cls.VY / G
        # Горизонтальная скорость первой и последней мины
        vx0 = cls.MARGIN / t * (1 + (random.random() - 0.5) * 0.1)
        vx1 = (SCREEN_WIDTH - cls.MARGIN) / t
        dvx = (vx1 - vx0) / (n - 1) if n > 1 else 0

        for i in range(n):
            b = BulletFloatingMine.new_instance(FRIEND_FLG)
            b.x = 0.0
            b.y = float(HORIZON_Y - 10)
            b.set_velocity(vx0 + dvx * i, -cls.VY)


# ─────────────────────────────────────────────
# F — Спутниковая атака (Satellite Attack)
# ─────────────────────────────────────────────

class SASatelliteAttack:
    """
    Лазерный удар со спутника: 15 лазерных лучей по случайным вражеским
    самолётам, каждый наносит 100 урона, луч виден 10 кадров.
    Визуальный эффект: светящаяся линия от точки (0, -5000) до земли,
    постепенно пропадает (alpha *= 0.9 на протяжении 30 кадров).
    +10% лучей за уровень навыка.

    Состояния: INIT → LASER (активные лучи) → CLEAR (затухание)
    """
    _BASE_LASER_NUM = 15
    DURATION        = 10    # кадров между лучами
    CLEAR_DURATION  = 30    # кадров затухания
    DAMAGE          = 100
    LASER_ORIGIN_Y  = -5000 # откуда "падает" луч

    ST_INIT  = 0
    ST_LASER = 1
    ST_CLEAR = 2

    _status   = ST_INIT
    _ls_cnt   = 0
    _frm_cnt  = 9999
    # Список активных лазеров для отрисовки: [(x1,y1,x2,y2,alpha)]
    _lasers:  List[dict] = []
    _alpha    = 0.0

    @classmethod
    def _laser_num(cls) -> int:
        return int(cls._BASE_LASER_NUM * (1 + Skills.get_skill(SA_SATELLITE) * 0.1))

    @classmethod
    def init(cls):
        cls._status  = cls.ST_INIT
        cls._ls_cnt  = 0
        cls._frm_cnt = cls.DURATION * cls._laser_num() + 1
        cls._lasers  = []
        cls._alpha   = 0.0

    @classmethod
    def attack(cls):
        cls._frm_cnt = 0
        cls._ls_cnt  = 0
        cls._status  = cls.ST_LASER
        cls._lasers  = []
        cls._alpha   = 1.0

    @classmethod
    def _laser_attack(cls, uc):
        """Бьёт по случайному вражескому самолёту, добавляет луч в список."""
        from bullet_system import BulletData as BD_class
        planes = uc.plane_array[uc.ENEMY]
        if not planes:
            return
        target = random.choice(planes)
        # Нанести урон
        bd = type('BD', (), {'damage': cls.DAMAGE, 'type': 0})()
        target.hit_bullet(bd)
        # Запомнить луч
        cls._lasers.append({
            'tx': target.x, 'ty': target.y,
            'alpha': 1.0
        })

    @classmethod
    def enter_frame(cls):
        from unit_system import UnitControl
        if cls._status == cls.ST_INIT:
            return

        if cls._status == cls.ST_LASER:
            if cls._frm_cnt % cls.DURATION == 0:
                cls._ls_cnt += 1
                cls._laser_attack(UnitControl)
                if cls._ls_cnt >= cls._laser_num():
                    cls._status  = cls.ST_CLEAR
                    cls._frm_cnt = 0

        elif cls._status == cls.ST_CLEAR:
            cls._alpha *= 0.9
            if cls._frm_cnt >= cls.CLEAR_DURATION:
                cls._lasers = []
                cls._status = cls.ST_INIT

        cls._frm_cnt += 1

    @classmethod
    def draw(cls, surface: pygame.Surface, camera_x: int):
        """Рисует лазерные лучи от спутника до целей."""
        if not cls._lasers or cls._alpha <= 0.01:
            return
        alpha_int = int(255 * cls._alpha)
        origin_y  = 0  # рисуем от верхнего края экрана (не -5000)
        for laser in cls._lasers:
            tx = int(laser['tx'] + camera_x)
            ty = int(laser['ty'])
            # Луч от верхнего края до цели
            lx = tx  # вертикальный луч для простоты
            color = (100, 220, 255, alpha_int)
            # Рисуем через Surface с alpha
            tmp = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(tmp, color, (lx, origin_y), (tx, ty), 3)
            # Свечение: более широкая полупрозрачная линия
            glow_color = (180, 240, 255, alpha_int // 3)
            pygame.draw.line(tmp, glow_color, (lx, origin_y), (tx, ty), 10)
            surface.blit(tmp, (0, 0))

    @classmethod
    def is_active(cls) -> bool:
        return cls._status != cls.ST_INIT


# ─────────────────────────────────────────────
# G — Атомная бомба (Atomic Bomb)
# ─────────────────────────────────────────────

class SAAtomicBomb:
    """
    Ядерный взрыв: наносит до 800 урона ВСЕМ юнитам на поле
    (кроме батарей и крепостей), урон уменьшается с расстоянием от центра.

    Формула урона:
        dist_factor = 1 + abs(unit.x - SCREEN_WIDTH/2) / SCREEN_WIDTH * 2 * 10
        damage = MAX_DAMAGE / dist_factor

    Например:
        В центре (x=1200):      damage = 800 / 1.0  = 800
        На краю  (x=0 или 2400): damage = 800 / 11.0 ≈ 72

    НЕ бьёт батареи (BATTERY) и крепости (FORTRESS).
    +10% макс. урона за уровень навыка.
    Анимируется как MovieClip (в Python: отдельный эффект взрыва на весь экран).
    """
    _BASE_MAX_DAMAGE = 800

    # Состояние анимации
    _active   = False
    _frm_cnt  = 0
    ANIM_FRAMES = 60   # длительность визуала ядерного взрыва

    @classmethod
    def _max_damage(cls) -> int:
        return int(cls._BASE_MAX_DAMAGE *
                   (1 + Skills.get_skill(SA_ATOMIC_BOMB) * 0.1))

    @classmethod
    def attack(cls):
        cls._active  = True
        cls._frm_cnt = 0
        cls._apply_damage()

    @classmethod
    def _apply_damage(cls):
        """Наносит урон всем юнитам кроме батарей и крепостей."""
        from unit_system import UnitControl, UNIT_CATEGORY_BATTERY, UNIT_CATEGORY_FORTRESS

        # allArray: [ship_array, plane_array, submarine_array, battery_array, fortress_array]
        # Пропускаем индексы BATTERY=3 и FORTRESS=4
        SKIP = {UnitControl.BATTERY, UnitControl.FORTRESS}
        max_dmg = cls._max_damage()

        for i, arr_pair in enumerate(UnitControl.all_array):
            if i in SKIP:
                continue
            for faction_arr in arr_pair:
                for unit in list(faction_arr):  # копия — юниты могут умереть
                    dist_factor = (1.0 + abs(unit.x - SCREEN_WIDTH * 0.5)
                                   / SCREEN_WIDTH * 2 * 10)
                    dmg = int(max_dmg / dist_factor)
                    bd  = type('BD', (), {'damage': dmg, 'type': 0})()
                    unit.hit_bullet(bd)

    @classmethod
    def enter_frame(cls):
        if not cls._active:
            return
        cls._frm_cnt += 1
        if cls._frm_cnt >= cls.ANIM_FRAMES:
            cls._active = False

    @classmethod
    def draw(cls, surface: pygame.Surface):
        """Рисует экранный эффект ядерного взрыва."""
        if not cls._active:
            return
        progress = cls._frm_cnt / cls.ANIM_FRAMES  # 0→1

        # Вспышка: белый → оранжевый → затухание
        if progress < 0.15:
            # Ослепляющая белая вспышка
            a = int(255 * (progress / 0.15))
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, a))
            surface.blit(overlay, (0, 0))
        elif progress < 0.5:
            # Оранжевое свечение
            p = (progress - 0.15) / 0.35
            a = int(200 * (1.0 - p))
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 140, 0, a))
            surface.blit(overlay, (0, 0))
        # else: постепенно исчезает

        # Гриб-облако (круг расширяется)
        cx = surface.get_width() // 2
        cy = surface.get_height() // 2
        max_r = int(surface.get_width() * 0.4)
        r     = int(max_r * min(progress * 3, 1.0))
        a     = int(180 * (1.0 - progress))
        if r > 0 and a > 0:
            tmp = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (255, 200, 50, a), (cx, cy), r)
            pygame.draw.circle(tmp, (255, 100, 0, a // 2), (cx, cy),
                               int(r * 0.6))
            surface.blit(tmp, (0, 0))

    @classmethod
    def is_active(cls) -> bool:
        return cls._active


# ─────────────────────────────────────────────
# Главный контроллер специальных атак
# ─────────────────────────────────────────────

class SpecialAttackControl:
    """
    Управляет всеми 5 специальными атаками.

    Порядок в enter_frame (из оригинала):
        1. SAHighAltitudeBombing  (бомбы падают постепенно)
        2. SAEMP                  (таймер паралича)
        3. SASatelliteAttack      (лазеры с паузами)
        4. SAAtomicBomb           (анимация взрыва)

    SAFloatingMine и SAAtomicBomb — одноразовые (не имеют enter_frame в оригинале).
    """

    @classmethod
    def init(cls):
        SAEMP.init()
        SASatelliteAttack.init()
        SAHighAltitudeBombing.init()

    @classmethod
    def enter_frame(cls):
        SAHighAltitudeBombing.enter_frame()
        SAEMP.enter_frame()
        SASatelliteAttack.enter_frame()
        SAAtomicBomb.enter_frame()

    @classmethod
    def attack(cls, sa_type: int):
        """Вызвать специальную атаку по типу SA_*."""
        if sa_type == SA_HA_BOMB:
            SAHighAltitudeBombing.attack()
        elif sa_type == SA_EMP:
            SAEMP.attack()
        elif sa_type == SA_FLOATING_MINE:
            SAFloatingMine.attack()
        elif sa_type == SA_SATELLITE:
            SASatelliteAttack.attack()
        elif sa_type == SA_ATOMIC_BOMB:
            SAAtomicBomb.attack()

    @classmethod
    def draw(cls, surface: pygame.Surface, camera_x: int):
        """Рисует визуальные эффекты активных спецатак."""
        EMPVisual.draw(surface)
        SASatelliteAttack.draw(surface, camera_x)
        SAAtomicBomb.draw(surface)

    @classmethod
    def is_emp_active(cls) -> bool:
        """Нужно проверять в setSpeed каждого вражеского корабля."""
        return SAEMP.emp_flg()


# ─────────────────────────────────────────────
# Справка по урону атомной бомбы
# ─────────────────────────────────────────────
# x=0    (левый край):   damage ≈  72  (800 / 11.0)
# x=600  (25% ширины):   damage ≈ 122  (800 / 6.5)
# x=1200 (центр):        damage = 800  (800 / 1.0)
# x=1800 (75% ширины):   damage ≈ 122
# x=2400 (правый край):  damage ≈  72
