"""
bullet_system.py — полный порт системы снарядов из Navy Battle Flash

Иерархия классов:
  BulletBase
  ├── BulletBallistic        (гравитация, угол 45°)
  │   ├── BulletBattleShip   (орудия линкоров)
  │   └── BulletBattery      (артиллерийская батарея)
  ├── BulletMachineGun       (пулемёт, lifetime=30)
  ├── BulletAntiAirSharpnel  (зенитный снаряд → взрыв в 30 осколков)
  ├── BulletMissileBase      (самонаводящаяся ракета)
  │   ├── BulletAntiAirMissile        (зенитная ракета батареи)
  │   ├── BulletAntiAirShipMissile    (крейсерская ракета)
  │   ├── BulletTorpedo               (торпеда, под водой)
  │   │   └── BulletTorpedoBom        (авиаторпеда — падает, потом плывёт)
  │   └── BulletSubmarineAntiAirMissile (подводная зенитная ракета)
  ├── BulletHedgehog         (реактивная глубинная бомба)
  │   ├── BulletBomb         (авиабомба — площадное поражение)
  │   └── BulletShipSubmarineBullet   (снаряд Unknown-босса)
  └── BulletFloatingMine     (плавающая мина — специальная атака)

BulletControl  — пул всех активных снарядов, итерация каждый кадр
BulletDataBase — статические данные снарядов
"""

import math
import pygame
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from unit_system import UnitBase

# ─────────────────────────────────────────────
# Константы (из GameConstants / BulletDataBase)
# ─────────────────────────────────────────────
SCREEN_WIDTH  = 2400
SCREEN_HEIGHT = 450
HORIZON_Y     = 300          # граница вода/воздух
SUBMARINE_Y   = 420          # глубина подлодок
G             = 0.3          # ускорение свободного падения (пикселей/кадр²)
FRIEND_FLG    = 0
ENEMY_FLG     = 1

LARGEST_UNIT_WIDTH = 800     # оптимизация bisection-поиска

# Категории юнитов (bitmask)
UNIT_CATEGORY_SHIP               = 256
UNIT_CATEGORY_PLANE              = 512
UNIT_CATEGORY_SUBMARINE          = 1024
UNIT_CATEGORY_BATTERY            = 2048
UNIT_CATEGORY_FORTRESS           = 4096
UNIT_CATEGORY_UNDERWATER_BATTERY = 8192

# Категории снарядов (bitmask)
BULLET_CATEGORY_BULLET  = 65536
BULLET_CATEGORY_MISSILE = 131072
BULLET_CATEGORY_TORPEDO = 262144

# Типы снарядов
BULLET_TYPE_BATTERY               = BULLET_CATEGORY_BULLET  | 0
BULLET_TYPE_MISSILE               = BULLET_CATEGORY_MISSILE | 1
BULLET_TYPE_TORPEDO               = BULLET_CATEGORY_TORPEDO | 2
BULLET_TYPE_MACHINEGUN            = BULLET_CATEGORY_BULLET  | 3
BULLET_TYPE_HEDGEHOG              = BULLET_CATEGORY_BULLET  | 4
BULLET_TYPE_ANTI_AIR_MISSILE      = BULLET_CATEGORY_MISSILE | 5
BULLET_TYPE_ANTI_AIR_SHIP_MISSILE = BULLET_CATEGORY_MISSILE | 6
BULLET_TYPE_BOMB                  = BULLET_CATEGORY_BULLET  | 7
BULLET_TYPE_BATTLE_SHIP           = BULLET_CATEGORY_BULLET  | 8
BULLET_TYPE_ANTIAIRSHARPNEL       = BULLET_CATEGORY_BULLET  | 9
BULLET_TYPE_TORPEDO_BOM           = BULLET_CATEGORY_TORPEDO | 10
BULLET_TYPE_SUBMARINE_AA_MISSILE  = BULLET_CATEGORY_MISSILE | 11
BULLET_TYPE_FLOATING_MINE         = BULLET_CATEGORY_BULLET  | 12
BULLET_TYPE_SHIPSUBMARINE         = BULLET_CATEGORY_BULLET  | 13


@dataclass
class BulletData:
    """Статические данные типа снаряда."""
    type:       int   = 0
    damage:     int   = 0
    speed:      float = 0.0
    dif_abs:    float = 0.0    # ускорение самонаведения (diffSpeed)
    img_size:   int   = 8
    enemy_type: int   = 0      # bitmask целей


# ─────────────────────────────────────────────
# База данных снарядов
# ─────────────────────────────────────────────

def _make_bullet_db() -> dict:
    ALL_SURFACE = (UNIT_CATEGORY_BATTERY | UNIT_CATEGORY_FORTRESS |
                   UNIT_CATEGORY_SHIP    | UNIT_CATEGORY_PLANE)
    ALL_UNDER   = (UNIT_CATEGORY_UNDERWATER_BATTERY | UNIT_CATEGORY_FORTRESS |
                   UNIT_CATEGORY_SHIP | UNIT_CATEGORY_SUBMARINE)

    specs = {
        BULLET_TYPE_BATTERY: dict(
            damage=15, speed=12, dif_abs=0, img_size=16, enemy_type=ALL_SURFACE),
        BULLET_TYPE_MISSILE: dict(
            damage=3,  speed=6,  dif_abs=2, img_size=14, enemy_type=ALL_SURFACE),
        BULLET_TYPE_TORPEDO: dict(
            damage=6,  speed=4,  dif_abs=1.5, img_size=14, enemy_type=ALL_UNDER),
        BULLET_TYPE_MACHINEGUN: dict(
            damage=2,  speed=10, dif_abs=0, img_size=5, enemy_type=ALL_SURFACE),
        BULLET_TYPE_HEDGEHOG: dict(
            damage=4,  speed=2,  dif_abs=0, img_size=8,
            enemy_type=UNIT_CATEGORY_FORTRESS | UNIT_CATEGORY_SUBMARINE),
        BULLET_TYPE_ANTI_AIR_MISSILE: dict(
            damage=3,  speed=11, dif_abs=4, img_size=14,
            enemy_type=UNIT_CATEGORY_PLANE | UNIT_CATEGORY_FORTRESS),
        BULLET_TYPE_ANTI_AIR_SHIP_MISSILE: dict(
            damage=5,  speed=10, dif_abs=3.8, img_size=21, enemy_type=ALL_SURFACE),
        BULLET_TYPE_BOMB: dict(
            damage=60, speed=0,  dif_abs=0, img_size=25,
            enemy_type=UNIT_CATEGORY_SUBMARINE | UNIT_CATEGORY_FORTRESS |
                       UNIT_CATEGORY_BATTERY   | UNIT_CATEGORY_SHIP),
        BULLET_TYPE_BATTLE_SHIP: dict(
            damage=24, speed=10, dif_abs=0, img_size=8, enemy_type=ALL_SURFACE),
        BULLET_TYPE_ANTIAIRSHARPNEL: dict(
            damage=0,  speed=14, dif_abs=0, img_size=13,
            enemy_type=UNIT_CATEGORY_PLANE | UNIT_CATEGORY_FORTRESS),
        BULLET_TYPE_TORPEDO_BOM: dict(
            damage=6,  speed=4,  dif_abs=1.5, img_size=14, enemy_type=ALL_UNDER),
        BULLET_TYPE_SUBMARINE_AA_MISSILE: dict(
            damage=3,  speed=11, dif_abs=4, img_size=14,
            enemy_type=UNIT_CATEGORY_PLANE | UNIT_CATEGORY_FORTRESS),
        BULLET_TYPE_FLOATING_MINE: dict(
            damage=60, speed=14, dif_abs=0, img_size=46,
            enemy_type=UNIT_CATEGORY_SHIP),
        BULLET_TYPE_SHIPSUBMARINE: dict(
            damage=90, speed=14, dif_abs=0, img_size=42,
            enemy_type=UNIT_CATEGORY_SHIP | UNIT_CATEGORY_SUBMARINE |
                       UNIT_CATEGORY_FORTRESS),
    }
    db = {}
    for btype, kw in specs.items():
        d = BulletData(type=btype, **kw)
        db[btype] = d
    return db


BULLET_DB: dict = _make_bullet_db()


# ─────────────────────────────────────────────
# Пул снарядов
# ─────────────────────────────────────────────

class BulletControl:
    """Глобальный менеджер активных снарядов с object pooling."""
    bullet_array: List["BulletBase"] = []
    bullet_stock: dict = {}          # type_id → [recycled bullets]

    @classmethod
    def init(cls):
        cls.bullet_array = []
        cls.bullet_stock = {}

    @classmethod
    def enter_frame(cls):
        """Обновление всех снарядов, итерация с конца (безопасное удаление)."""
        for i in range(len(cls.bullet_array) - 1, -1, -1):
            if i < len(cls.bullet_array):
                cls.bullet_array[i].on_enter_frame()

    @classmethod
    def draw(cls, surface: pygame.Surface, camera_x: int):
        for bullet in cls.bullet_array:
            bullet.draw(surface, camera_x)


# ─────────────────────────────────────────────
# Базовый снаряд
# ─────────────────────────────────────────────

class BulletBase:
    """
    Базовый класс всех снарядов.

    Спрайт: sprite sheet imgSize*10 × imgSize*18 (180 кадров по углу)
    Столбцов: 10 (IMG_X_NUM), строк: 18 (IMG_Y_NUM)
    Кадр выбирается по углу вектора скорости: frame = angle/(2π)*180
    """

    IMG_X_NUM = 10

    def __init__(self, bullet_type: int, faction: int):
        self.bullet_data: BulletData = BULLET_DB[bullet_type]
        self.faction      = faction        # FRIEND_FLG / ENEMY_FLG
        self.x            = 0.0
        self.y            = 0.0
        self.vel_x        = 0.0
        self.vel_y        = 0.0
        self.speed        = self.bullet_data.speed
        self.dif_abs      = self.bullet_data.dif_abs
        self.damage       = self.bullet_data.damage
        self.enemy_type   = self.bullet_data.enemy_type
        self.hit_flag     = False
        self.frame_cnt    = 0
        # Pygame: цвет для отладочного рисования
        self.color = (0, 0, 0) if faction == FRIEND_FLG else (220, 30, 30)

    # ── Фабричный метод с pooling ──────────────────────────────────────
    @classmethod
    def _new(cls, faction: int, bullet_type: int) -> "BulletBase":
        stock = BulletControl.bullet_stock.setdefault(bullet_type, [])
        if stock:
            b = stock.pop()
            b._init_public(faction)
        else:
            b = cls(bullet_type, faction)
        BulletControl.bullet_array.append(b)
        return b

    def _init_public(self, faction: int):
        """Сброс при повторном использовании из пула."""
        self.faction    = faction
        self.speed      = self.bullet_data.speed
        self.dif_abs    = self.bullet_data.dif_abs
        self.damage     = self.bullet_data.damage
        self.enemy_type = self.bullet_data.enemy_type
        self.hit_flag   = False
        self.frame_cnt  = 0
        self.vel_x = self.vel_y = 0.0
        self.color = (0, 0, 0) if faction == FRIEND_FLG else (220, 30, 30)

    # ── Жизненный цикл ─────────────────────────────────────────────────
    def set_velocity(self, vx: float, vy: float):
        self.vel_x = vx
        self.vel_y = vy

    def remove_this(self):
        try:
            BulletControl.bullet_array.remove(self)
        except ValueError:
            pass
        stock = BulletControl.bullet_stock.setdefault(
            self.bullet_data.type, [])
        stock.append(self)

    def on_enter_frame(self):
        """Главный цикл снаряда: поиск попаданий → движение → рисование."""
        from unit_system import UnitControl  # отложенный импорт
        hit = self._hit_test_enemy(UnitControl)
        if hit is not None:
            self._hit_enemy(hit)
        self.frame_cnt += 1
        self.x += self.vel_x
        self.y += self.vel_y

    def _hit_enemy(self, unit: "UnitBase"):
        if not self.hit_flag:
            unit.hit_bullet(self.bullet_data)
            self._explode()
            self.remove_this()
        self.hit_flag = True

    def _explode(self):
        """Переопределяется в подклассах для создания эффектов."""
        pass

    # ── Поиск попаданий ────────────────────────────────────────────────
    def _hit_test_enemy(self, uc) -> Optional["UnitBase"]:
        """
        Проверяет столкновение снаряда с юнитами противника.
        Важно: корабли/самолёты только выше горизонта (y < HORIZON_Y),
               подлодки только ниже (y > HORIZON_Y).
        """
        if self.faction == ENEMY_FLG:
            side = uc.FRIEND
        else:
            side = uc.ENEMY

        et = self.enemy_type

        if (et & UNIT_CATEGORY_SHIP) and self.y < HORIZON_Y:
            hit = self._hittest_each(uc.ship_array[side])
            if hit: return hit

        if (et & UNIT_CATEGORY_SUBMARINE) and self.y > HORIZON_Y:
            hit = self._hittest_each(uc.submarine_array[side])
            if hit: return hit

        if (et & UNIT_CATEGORY_PLANE) and self.y < HORIZON_Y:
            hit = self._hittest_each(uc.plane_array[side])
            if hit: return hit

        if et & (UNIT_CATEGORY_BATTERY | UNIT_CATEGORY_UNDERWATER_BATTERY):
            hit = self._hittest_each(uc.battery_array[side])
            if hit: return hit

        if et & UNIT_CATEGORY_FORTRESS:
            hit = self._hittest_each(uc.fortress_array[side])
            if hit: return hit

        return None

    def _hittest_each(self, units: list) -> Optional["UnitBase"]:
        """Bisection-ускоренный перебор юнитов."""
        if not units:
            return None
        start = self._bisection(units)
        prev_dist = float('inf')
        for i in range(start, len(units)):
            u = units[i]
            if u.hittest_point(int(self.x), int(self.y)):
                return u
            d = abs(u.x - self.x)
            if d >= prev_dist and d > LARGEST_UNIT_WIDTH:
                return None
            prev_dist = d
        return None

    def _bisection(self, units: list) -> int:
        """Бинарный поиск начального индекса в отсортированном массиве."""
        if len(units) <= 2:
            return 0
        lo = len(units) // 2
        idx = lo
        for _ in range(10):
            u = units[idx]
            left  = u.x - u.unit_data.img_width * 0.5
            right = u.x + u.unit_data.img_width * 0.5
            if left > self.x:
                lo = max(lo // 2, 1)
                idx = max(0, idx - lo)
            elif right >= self.x:
                return max(0, idx - 1)
            else:
                lo = max(lo // 2, 1)
                idx = min(len(units) - 1, idx + lo)
        return 0

    # ── Отрисовка ──────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, camera_x: int):
        """
        Дебаговая отрисовка кругом.
        В финальной версии заменить на sprite-sheet по углу вектора скорости.
        """
        sx = int(self.x + camera_x)
        sy = int(self.y)
        r  = max(2, self.bullet_data.img_size // 4)
        if -r <= sx <= surface.get_width() + r:
            pygame.draw.circle(surface, self.color, (sx, sy), r)

    def _get_image_frame(self) -> tuple:
        """Возвращает (col, row) кадра спрайт-шита по направлению vel."""
        angle = math.atan2(self.vel_y, self.vel_x)
        if angle < 0:
            angle += math.pi * 2
        frame = int(angle / (math.pi * 2) * 180) % 180
        col = frame % self.IMG_X_NUM
        row = frame // self.IMG_X_NUM
        return col, row


# ─────────────────────────────────────────────
# Баллистический снаряд (гравитация + удаление при y > HORIZON_Y)
# ─────────────────────────────────────────────

class BulletBallistic(BulletBase):
    """Снаряд с гравитацией. setVelocity нормализует до speed под углом 45°."""

    def set_velocity(self, vx: float, vy: float):
        length = math.hypot(vx, vy)
        if length > 0:
            self.vel_x = vx / length * self.speed
            self.vel_y = vy / length * self.speed

    def on_enter_frame(self):
        super().on_enter_frame()
        self.vel_y += G
        if self.y > HORIZON_Y:
            self.remove_this()


class BulletBattleShip(BulletBallistic):
    """Бронебойный снаряд линкора. damage=24, speed=10."""

    @classmethod
    def new_instance(cls, faction: int) -> "BulletBattleShip":
        return cls._new(faction, BULLET_TYPE_BATTLE_SHIP)

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_BATTLE_SHIP, faction)


class BulletBattery(BulletBallistic):
    """Снаряд артиллерийской батареи. damage=15, speed=12."""

    @classmethod
    def new_instance(cls, faction: int) -> "BulletBattery":
        return cls._new(faction, BULLET_TYPE_BATTERY)

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_BATTERY, faction)


# ─────────────────────────────────────────────
# Пулемётный снаряд
# ─────────────────────────────────────────────

class BulletMachineGun(BulletBase):
    """
    Быстрый снаряд, damage=2, speed=10, lifetime=30 кадров.
    setVelocity нормализует вектор до speed.
    """
    LIFETIME = 30

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_MACHINEGUN, faction)
        self.lifetime = self.LIFETIME

    @classmethod
    def new_instance(cls, faction: int) -> "BulletMachineGun":
        return cls._new(faction, BULLET_TYPE_MACHINEGUN)

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self.lifetime = self.LIFETIME

    def set_velocity(self, vx: float, vy: float):
        length = math.hypot(vx, vy)
        if length > 0:
            self.vel_x = vx / length * self.speed
            self.vel_y = vy / length * self.speed

    def on_enter_frame(self):
        super().on_enter_frame()
        if self.frame_cnt > self.lifetime or self.y > HORIZON_Y:
            self.remove_this()


# ─────────────────────────────────────────────
# Зенитный снаряд (AAS — Anti-Air Shrapnel)
# ─────────────────────────────────────────────

class BulletAntiAirSharpnel(BulletBase):
    """
    Упреждающий зенитный снаряд.
    При подлёте к цели (nearFuze) или истечении lifetime=20 фреймов —
    взрывается в 30 осколков (BulletMachineGun) по кругу, range=9 фреймов.

    Создаётся через UnitUtl.anti_air_shrapnel() с предустановленным
    lifetime = dist / speed.
    """
    DEFAULT_LIFETIME = 20
    SHRAPNEL_NUM     = 30
    SHRAPNEL_RANGE   = 9    # lifetime осколков

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_ANTIAIRSHARPNEL, faction)
        self.lifetime       = self.DEFAULT_LIFETIME
        self._enemy_unit    = None
        self._prev_recycle  = 0
        self._prev_dist     = float('inf')

    @classmethod
    def new_instance(cls, faction: int) -> "BulletAntiAirSharpnel":
        return cls._new(faction, BULLET_TYPE_ANTIAIRSHARPNEL)

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self.lifetime    = self.DEFAULT_LIFETIME
        self._enemy_unit = None
        self._prev_dist  = float('inf')

    def set_velocity(self, vx: float, vy: float):
        length = math.hypot(vx, vy)
        if length > 0:
            self.vel_x = vx / length * self.speed
            self.vel_y = vy / length * self.speed

    def set_enemy_unit(self, unit: "UnitBase"):
        self._enemy_unit   = unit
        self._prev_recycle = unit.recycle_num
        self._prev_dist    = float('inf')

    def _near_fuze(self) -> bool:
        """Взрываемся, если снаряд прошёл ближайшую точку к цели."""
        if self._enemy_unit is None:
            return False
        if self._prev_recycle != self._enemy_unit.recycle_num:
            return False  # цель была уничтожена и переиспользована
        dx = self._enemy_unit.x - self.x
        dy = self._enemy_unit.y - self.y
        dist = math.hypot(dx, dy)
        if dist > self._prev_dist:
            return True
        self._prev_dist = dist
        return False

    def _explode(self):
        super()._explode()
        self._shot_shrapnel()

    def _shot_shrapnel(self):
        """Круговой взрыв из 30 осколков."""
        for i in range(self.SHRAPNEL_NUM):
            angle = math.pi * 2 / self.SHRAPNEL_NUM * i
            b = BulletMachineGun.new_instance(self.faction)
            b.x = self.x
            b.y = self.y
            b.lifetime = self.SHRAPNEL_RANGE
            b.vel_x = math.cos(angle) * b.speed
            b.vel_y = math.sin(angle) * b.speed

    def on_enter_frame(self):
        super().on_enter_frame()
        if self._near_fuze() or self.frame_cnt > self.lifetime or self.y > HORIZON_Y:
            self._explode()
            self.hit_flag = True
            self.remove_this()


# ─────────────────────────────────────────────
# Самонаводящаяся ракета (базовый класс)
# ─────────────────────────────────────────────

class BulletMissileBase(BulletBase):
    """
    Самонаводящаяся ракета.
    Каждый кадр:
      1. Ищет ближайшего врага нужного типа (каждые 30 кадров или при потере цели)
      2. Добавляет к vel вектор к цели длиной dif_abs (ускорение поворота)
      3. Ограничивает |vel| ≤ speed
    Прицеливание с поправкой по типу цели (корабль/субмарина/крепость/бомбардировщик).
    """

    def __init__(self, bullet_type: int, faction: int):
        super().__init__(bullet_type, faction)
        self._enemy_unit   = None
        self._prev_recycle = 0

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self._enemy_unit   = None
        self._prev_recycle = 0

    def _search_enemy(self):
        from unit_system import UnitControl, UnitUtl
        self._enemy_unit = UnitUtl.search_enemy_all(
            self.faction, self, self.enemy_type)
        if self._enemy_unit is not None:
            self._prev_recycle = self._enemy_unit.recycle_num

    def _get_aim_point(self) -> tuple:
        """Рассчитывает точку прицеливания с поправкой по типу цели."""
        u = self._enemy_unit
        tx, ty = u.x, u.y

        ut = u.unit_data.unit_type
        if ut & UNIT_CATEGORY_FORTRESS:
            # торпеды целятся чуть ниже горизонта, ракеты — чуть выше
            if self.bullet_data.type & BULLET_CATEGORY_TORPEDO:
                ty = HORIZON_Y + 10
            else:
                ty = HORIZON_Y - 10
            # крепость — целимся сбоку
            from unit_system import UNIT_TYPE_FORTRESS
            if ut == UNIT_TYPE_FORTRESS:
                if self.faction == ENEMY_FLG:
                    tx -= 100
                else:
                    tx += 100
        elif ut & UNIT_CATEGORY_SUBMARINE:
            ty -= u.unit_data.img_height / 4
        else:
            from unit_system import UNIT_TYPE_BOMBER
            if ut == UNIT_TYPE_BOMBER:
                ty -= u.unit_data.img_height / 2

        return tx, ty

    def _set_vel_enterframe(self):
        if self._enemy_unit is None:
            self._explode()
            self.remove_this()
            return
        tx, ty = self._get_aim_point()
        dx = tx - self.x
        dy = ty - self.y
        length = math.hypot(dx, dy)
        if length > 0:
            # нормализуем до dif_abs и добавляем к текущей скорости
            nx = dx / length * self.dif_abs
            ny = dy / length * self.dif_abs
            self.vel_x += nx
            self.vel_y += ny
        # ограничение скорости
        spd = math.hypot(self.vel_x, self.vel_y)
        if spd > self.speed:
            self.vel_x = self.vel_x / spd * self.speed
            self.vel_y = self.vel_y / spd * self.speed

    def on_enter_frame(self):
        # Обновляем цель каждые 30 кадров или при потере
        if (self._enemy_unit is None or
                (hasattr(self._enemy_unit, 'recycle_num') and
                 self._enemy_unit.recycle_num != self._prev_recycle) or
                self.frame_cnt % 30 == 0):
            self._search_enemy()
        self._set_vel_enterframe()
        super().on_enter_frame()

    def _explode(self):
        super()._explode()


class BulletAntiAirMissile(BulletMissileBase):
    """
    Зенитная ракета батареи.
    damage=3, speed=11, dif_abs=4.
    Не уходит под воду (отражает vel.y при y > HORIZON_Y).
    """

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_ANTI_AIR_MISSILE, faction)

    @classmethod
    def new_instance(cls, faction: int) -> "BulletAntiAirMissile":
        return cls._new(faction, BULLET_TYPE_ANTI_AIR_MISSILE)

    def _set_vel_enterframe(self):
        super()._set_vel_enterframe()
        if self.y > HORIZON_Y and self.vel_y > 0:
            self.vel_y *= -1  # отбиваем обратно вверх


class BulletAntiAirShipMissile(BulletMissileBase):
    """
    Крейсерская ракета (Cruiser). damage=5, speed=10, dif_abs=3.8.
    Атакует все надводные цели + самолёты.
    Запускается вертикально вверх: setVelocity(0, -speed).
    """

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_ANTI_AIR_SHIP_MISSILE, faction)

    @classmethod
    def new_instance(cls, faction: int) -> "BulletAntiAirShipMissile":
        return cls._new(faction, BULLET_TYPE_ANTI_AIR_SHIP_MISSILE)

    def _set_vel_enterframe(self):
        super()._set_vel_enterframe()
        if self.y > HORIZON_Y and self.vel_y > 0:
            self.vel_y *= -1


# ─────────────────────────────────────────────
# Торпеды
# ─────────────────────────────────────────────

class BulletTorpedo(BulletMissileBase):
    """
    Торпеда. damage=6, speed=4, dif_abs=1.5.
    Самонаводится на цель под водой.
    Если случайно вышла выше горизонта — vel.y инвертируется.
    """

    def __init__(self, faction: int, bullet_type: int = BULLET_TYPE_TORPEDO):
        super().__init__(bullet_type, faction)

    @classmethod
    def new_instance(cls, faction: int) -> "BulletTorpedo":
        return cls._new(faction, BULLET_TYPE_TORPEDO)

    def _set_vel_enterframe(self):
        super()._set_vel_enterframe()
        # Не даём торпеде всплыть выше горизонта
        if self.y < HORIZON_Y - 2 and self.vel_y < 0:
            self.vel_y *= -1


class BulletTorpedoBom(BulletTorpedo):
    """
    Авиаторпеда (торпедный бомбардировщик).
    Фаза 1 (AIR): падает вертикально под действием гравитации.
    Фаза 2 (WATER): становится обычной самонаводящейся торпедой.
    """

    def __init__(self, faction: int):
        super().__init__(faction, BULLET_TYPE_TORPEDO_BOM)
        self._air_flg = True

    @classmethod
    def new_instance(cls, faction: int) -> "BulletTorpedoBom":
        return cls._new(faction, BULLET_TYPE_TORPEDO_BOM)

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self._air_flg = True
        self.vel_x = self.vel_y = 0.0

    def _set_vel_enterframe(self):
        if self._air_flg:
            # Свободное падение
            self.vel_x = 0.0
            self.vel_y += G
            if self.y > HORIZON_Y:
                self._air_flg = False
        else:
            super()._set_vel_enterframe()


class BulletSubmarineAntiAirMissile(BulletMissileBase):
    """
    Подводная зенитная ракета (AtomicSub / Nautilus).
    damage=3, speed=11, dif_abs=4.
    Фаза 1 (UNDERWATER): поднимается вертикально (vel.x=0, vel.y=-speed).
    Фаза 2 (AIR): самонаводится на самолёт.
    """

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_SUBMARINE_AA_MISSILE, faction)
        self._underwater = True

    @classmethod
    def new_instance(cls, faction: int) -> "BulletSubmarineAntiAirMissile":
        return cls._new(faction, BULLET_TYPE_SUBMARINE_AA_MISSILE)

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self._underwater = True

    def _set_vel_enterframe(self):
        super()._set_vel_enterframe()
        if self._underwater:
            self.vel_x = 0.0
            self.vel_y = -self.speed
            if self.y < HORIZON_Y:
                self._underwater = False
        elif self.y > HORIZON_Y and self.vel_y > 0:
            self.vel_y *= -1


# ─────────────────────────────────────────────
# Глубинная бомба (Hedgehog)
# ─────────────────────────────────────────────

class BulletHedgehog(BulletBase):
    """
    Реактивная глубинная бомба (противолодочный фрегат).
    damage=4, speed=2.
    Летит вверх, потом падает, под водой тонет со скоростью UNDER_WATER_SPEED=1.
    """
    UNDER_WATER_SPEED = 1.0

    def __init__(self, faction: int, bullet_type: int = BULLET_TYPE_HEDGEHOG):
        super().__init__(bullet_type, faction)

    @classmethod
    def new_instance(cls, faction: int) -> "BulletHedgehog":
        return cls._new(faction, BULLET_TYPE_HEDGEHOG)

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self.vel_x = self.vel_y = 0.0

    def set_velocity(self, vx: float, vy: float):
        # В отличие от пулемёта — НЕ нормализует, сохраняет разброс
        self.vel_x = vx
        self.vel_y = vy

    def on_enter_frame(self):
        super().on_enter_frame()
        if self.y > SCREEN_HEIGHT + self.bullet_data.img_size:
            self.remove_this()
        elif self.y > HORIZON_Y:
            # Под водой: двигаемся строго вниз
            self.vel_x = 0.0
            self.vel_y = self.UNDER_WATER_SPEED
        else:
            # В воздухе: гравитация
            self.vel_y += G


class BulletBomb(BulletHedgehog):
    """
    Авиабомба (Bomber, Hindenburg).
    damage=60, img_size=25.
    ПЛОЩАДНОЕ ПОПАДАНИЕ — проверяет 4 угла прямоугольника img_size*0.25.
    Может попасть в несколько юнитов одновременно.
    Под водой: тонет вертикально.
    """

    def __init__(self, faction: int):
        super().__init__(faction, BULLET_TYPE_BOMB)

    @classmethod
    def new_instance(cls, faction: int) -> "BulletBomb":
        return cls._new(faction, BULLET_TYPE_BOMB)

    def _hit_test_enemy_range(self, uc) -> list:
        """Площадной hitcheck по 4 углам снаряда."""
        if self.faction == ENEMY_FLG:
            side = uc.FRIEND
        else:
            side = uc.ENEMY

        r = int(self.bullet_data.img_size * 0.25)
        hits = []
        et = self.enemy_type

        def check(arr):
            for u in arr[:]:
                if (u.hittest_point(int(self.x + r), int(self.y + r)) or
                        u.hittest_point(int(self.x + r), int(self.y - r)) or
                        u.hittest_point(int(self.x - r), int(self.y + r)) or
                        u.hittest_point(int(self.x - r), int(self.y - r))):
                    u.hit_bullet(self.bullet_data)
                    hits.append(u)

        if et & UNIT_CATEGORY_SHIP:      check(uc.ship_array[side])
        if et & UNIT_CATEGORY_SUBMARINE: check(uc.submarine_array[side])
        if et & UNIT_CATEGORY_BATTERY:   check(uc.battery_array[side])
        if et & UNIT_CATEGORY_FORTRESS:  check(uc.fortress_array[side])
        return hits

    def on_enter_frame(self):
        from unit_system import UnitControl
        hits = self._hit_test_enemy_range(UnitControl)
        if hits and not self.hit_flag:
            self._explode()
            self.remove_this()
            self.hit_flag = True
            return

        self.frame_cnt += 1
        self.x += self.vel_x
        self.y += self.vel_y

        if self.y > SCREEN_HEIGHT + self.bullet_data.img_size:
            self.remove_this()
        elif self.y > HORIZON_Y:
            self.vel_x = 0.0
            self.vel_y = self.UNDER_WATER_SPEED
        else:
            self.vel_y += G


class BulletShipSubmarineBullet(BulletHedgehog):
    """
    Снаряд-волна Unknown-босса (SSbullet).
    damage=90, img_size=42.
    Запускается веером: каждые 30 фреймов 12 снарядов,
    скорость нарастает: vx = sign(dx)*(i*0.2+3), vy=-3.
    Площадное попадание (как Bomb).
    """

    def __init__(self, faction: int):
        super().__init__(faction, BULLET_TYPE_SHIPSUBMARINE)

    @classmethod
    def new_instance(cls, faction: int) -> "BulletShipSubmarineBullet":
        return cls._new(faction, BULLET_TYPE_SHIPSUBMARINE)

    def on_enter_frame(self):
        from unit_system import UnitControl
        # Аналог площадного hitcheck как у BulletBomb
        if self.faction == ENEMY_FLG:
            side = UnitControl.FRIEND
        else:
            side = UnitControl.ENEMY

        r = int(self.bullet_data.img_size * 0.25)
        hit_any = False
        et = self.enemy_type

        def check(arr):
            nonlocal hit_any
            for u in arr:
                if (u.hittest_point(int(self.x + r), int(self.y + r)) or
                        u.hittest_point(int(self.x + r), int(self.y - r)) or
                        u.hittest_point(int(self.x - r), int(self.y + r)) or
                        u.hittest_point(int(self.x - r), int(self.y - r))):
                    u.hit_bullet(self.bullet_data)
                    hit_any = True

        if et & UNIT_CATEGORY_SHIP:      check(UnitControl.ship_array[side])
        if et & UNIT_CATEGORY_SUBMARINE: check(UnitControl.submarine_array[side])
        if et & UNIT_CATEGORY_FORTRESS:  check(UnitControl.fortress_array[side])

        if hit_any and not self.hit_flag:
            self._explode()
            self.remove_this()
            self.hit_flag = True
            return

        self.frame_cnt += 1
        self.x += self.vel_x
        self.y += self.vel_y

        if self.y > SCREEN_HEIGHT + self.bullet_data.img_size:
            self.remove_this()
        elif self.y > HORIZON_Y:
            self.vel_x = 0.0
            self.vel_y = self.UNDER_WATER_SPEED
        else:
            self.vel_y += G


# ─────────────────────────────────────────────
# Плавающая мина (Special Attack)
# ─────────────────────────────────────────────

class BulletFloatingMine(BulletBase):
    """
    Плавающая мина (специальная атака).
    damage=60, img_size=46, атакует только SHIP.

    Состояния:
      INIT     — падает под гравитацией до HORIZON_Y
      FLOATING — тормозит в воде (resist=0.9) и всплывает (float_force=0.5)
                 пока не достигнет поверхности
      END      — застывает на поверхности (y = HORIZON_Y - 2)
    """
    WATER_RESIST = 0.9
    FLOAT_FORCE  = 0.5
    ST_INIT      = 1
    ST_FLOATING  = 2
    ST_END       = 3

    def __init__(self, faction: int):
        super().__init__(BULLET_TYPE_FLOATING_MINE, faction)
        self._status = self.ST_INIT

    @classmethod
    def new_instance(cls, faction: int) -> "BulletFloatingMine":
        return cls._new(faction, BULLET_TYPE_FLOATING_MINE)

    def _init_public(self, faction: int):
        super()._init_public(faction)
        self.vel_x = self.vel_y = 0.0
        self._status = self.ST_INIT

    def set_velocity(self, vx: float, vy: float):
        self.vel_x = vx
        self.vel_y = vy

    def on_enter_frame(self):
        super().on_enter_frame()  # проверка попаданий
        if self._status == self.ST_INIT:
            if self.y > HORIZON_Y:
                self._status = self.ST_FLOATING
            self.vel_y += G

        elif self._status == self.ST_FLOATING:
            if self.y > HORIZON_Y:
                self.vel_x *= self.WATER_RESIST
                self.vel_y -= self.FLOAT_FORCE
                self.vel_y *= self.WATER_RESIST
            else:
                # Достигла поверхности — замираем
                self.vel_x = 0.0
                self.vel_y = 0.0
                self.y = HORIZON_Y - 2
                self._status = self.ST_END
        # ST_END: мина стоит на месте, ждёт попадания


# ─────────────────────────────────────────────
# Утилита создания снарядов (UnitUtl-порт)
# ─────────────────────────────────────────────

class BulletFactory:
    """
    Фабричные методы для создания снарядов — порт UnitUtl.machineGunShot,
    antiAirSharpnel, attackParabolaBullet.
    """

    @staticmethod
    def machine_gun_shot(enemy_unit: "UnitBase", src_x: float, src_y: float,
                         faction: int, lifetime: int = -1,
                         lead_predict: bool = False) -> BulletMachineGun:
        """
        Создаёт пулемётный снаряд с упреждением (lead_predict=True для зениток).
        lifetime > 0 — переопределяет стандартный (30 кадров).

        lead_predict: time = dist/speed*0.8, целим в predicted pos.
        """
        b = BulletMachineGun.new_instance(faction)
        if lifetime > 0:
            b.lifetime = lifetime

        tx = enemy_unit.x
        ty = enemy_unit.y

        if lead_predict:
            dist = math.hypot(tx - src_x, ty - src_y)
            t = dist / b.speed * 0.8
            tx += enemy_unit.vel_x * t
            ty += enemy_unit.vel_y * t

        # Поправка прицела по типу цели
        from unit_system import (UNIT_TYPE_FORTRESS, UNIT_TYPE_SUBFORTRESS,
                                  UNIT_TYPE_BOMBER)
        ut = enemy_unit.unit_data.unit_type
        if ut & UNIT_CATEGORY_SHIP:
            ty -= enemy_unit.unit_data.img_height / 4
        elif ut == UNIT_TYPE_FORTRESS:
            ty = max(ty - 40, HORIZON_Y - 10)
            if faction == ENEMY_FLG:
                tx -= 100
            else:
                tx += 100
        elif ut == UNIT_TYPE_SUBFORTRESS:
            ty -= 70
        elif ut == UNIT_TYPE_BOMBER:
            ty -= enemy_unit.unit_data.img_width / 4

        b.x = src_x
        b.y = src_y
        dx = tx - src_x
        dy = ty - src_y
        b.set_velocity(dx, dy)
        return b

    @staticmethod
    def anti_air_shrapnel(enemy_unit: "UnitBase", src_x: float, src_y: float,
                          faction: int) -> BulletAntiAirSharpnel:
        """
        Создаёт зенитный снаряд с точным упреждением.
        lifetime = dist / speed (снаряд исчезает точно в момент взрыва).
        """
        b = BulletAntiAirSharpnel.new_instance(faction)
        tx, ty = enemy_unit.x, enemy_unit.y
        dist = math.hypot(tx - src_x, ty - src_y)
        t = dist / b.speed
        tx += enemy_unit.vel_x * t
        ty += enemy_unit.vel_y * t
        b.lifetime = int(t)
        b.set_enemy_unit(enemy_unit)
        b.x = src_x
        b.y = src_y
        b.set_velocity(tx - src_x, ty - src_y)
        return b

    @staticmethod
    def attack_parabola_bullet(
            enemy_unit: "UnitBase",
            bullet: BulletBallistic,
            src_x: float, src_y: float) -> bool:
        """
        Вычисляет начальную скорость баллистического снаряда для попадания в цель
        с учётом гравитации G и скорости цели.

        Угол вылета всегда 45° (vx = vy = speed/√2).
        Решает квадратное уравнение для скорости.

        Возвращает False если цель недостижима (дискриминант < 0).
        Небольшой разброс ±1.7% для реалистичности.
        """
        import random as _random

        tx = enemy_unit.x
        ty = enemy_unit.y
        tvx = enemy_unit.vel_x
        tvy = enemy_unit.vel_y

        dx = tx - src_x
        dy = ty - src_y
        g = G

        if dx < 0:
            a = dy - dx
            b_coef = (math.sqrt(2) * tvx * dy
                      - dx * (tvx + tvy) * math.sqrt(0.5))
        else:
            a = dy + dx
            b_coef = (-math.sqrt(2) * tvx * dy
                      - dx * (tvx - tvy) * math.sqrt(0.5))

        if a == 0:
            bullet.remove_this()
            return False

        c_coef = (2 * dy * tvx * tvx
                  - 2 * dx * tvx * tvy
                  - g * dx * dx)
        discriminant = b_coef * b_coef - a * c_coef

        if discriminant < 0:
            bullet.remove_this()
            return False

        scatter = 1.0 + (_random.random() - 0.5) / 30.0
        spd = (-b_coef + math.sqrt(discriminant)) / a * scatter
        bullet.speed = spd

        SQ2 = math.sqrt(0.5)
        if dx < 0:
            vx = -spd * SQ2
            vy = -spd * SQ2
        else:
            vx = spd * SQ2
            vy = -spd * SQ2

        bullet.x = src_x
        bullet.y = src_y
        bullet.vel_x = vx
        bullet.vel_y = vy
        return True


# ─────────────────────────────────────────────
# Краткая справка по всем типам снарядов
# ─────────────────────────────────────────────
BULLET_SUMMARY = """
Тип снаряда              Дмг  Скор  DifAbs  Цели
─────────────────────────────────────────────────────────────
BulletBattery            15   12    0       Корабли/Самолёты/Батареи/Крепость
BulletBattleShip         24   10    0       Корабли/Самолёты/Батареи/Крепость
BulletMachineGun          2   10    0       Корабли/Самолёты/Батареи/Крепость
BulletAntiAirSharpnel     0   14    0       (снаряд→30 осколков MachineGun)
BulletAntiAirMissile      3   11    4       Самолёты/Крепость
BulletAntiAirShipMissile  5   10    3.8     Корабли/Самолёты/Батареи/Крепость
BulletTorpedo             6    4    1.5     Корабли/Подлодки/ПодводБатареи/Крепость
BulletTorpedoBom          6    4    1.5     (как торпеда, сначала падает)
BulletSubAirMissile       3   11    4       Самолёты/Крепость
BulletHedgehog            4    2    0       Подлодки/Крепость
BulletBomb               60    0    0       Корабли/Подлодки/Батареи/Крепость (площадь)
BulletShipSubmarine      90   14    0       Корабли/Подлодки/Крепость (площадь)
BulletFloatingMine       60   14    0       Только корабли
"""
