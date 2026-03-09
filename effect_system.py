"""
effect_system.py — порт системы эффектов из Navy Battle Flash

Два эффекта:
  EffectBase   — дымовые частицы (smoke particles)
  ThunderMain  — молния ЭМИ (процедурная рекурсивная молния)

─────────────────────────────────────────────────────────────
ДЫМОВЫЕ ЧАСТИЦЫ (EffectBase / ParticleMove)
─────────────────────────────────────────────────────────────
Три размера дыма:

  SMOKE_BIG  (0) — большой взрыв/дым:
    count=13, speed=7, spread=45, alpha=150, decay=0.7
    Используется: крупные взрывы кораблей

  SMOKE_TINY (2) — маленький дым/вспышка:
    count=4,  speed=2, spread=3,  alpha=10,  decay=0.7
    Используется: попадание пули, ракеты

  default    (1) — средний дым:
    count=7,  speed=2, spread=18, alpha=110, decay=0.7
    Используется: средние взрывы

Частицы двигаются по случайному вектору, альфа уменьшается
на decay каждый кадр, удаляются при alpha < 1.
Можно отключить через GameParams.smoke_flg = False.

─────────────────────────────────────────────────────────────
МОЛНИЯ ЭМИ (ThunderMain)
─────────────────────────────────────────────────────────────
Процедурная ветвящаяся молния:
  - Главный луч от (0,0) до (STAGE_WIDTH, SCREEN_HEIGHT)
  - Каждый сегмент отклоняется на случайный перпендикуляр
  - С вероятностью proportional to lineWidth*2 создаётся ветка
  - Ветки меньше и тоньше
  - Цвет: белый (#FFFFFF) с голубым свечением (#221FFF → 0x221FFF)
  - Рисуется один раз при вызове thunder_rewrite(), потом стирается на кадр 8
"""

import math
import random
import pygame
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────
SCREEN_WIDTH  = 2400
SCREEN_HEIGHT = 450
STAGE_WIDTH   = 800

SMOKE_BIG  = 0
SMOKE_TINY = 2
# default = 1 (любое другое значение)


# ─────────────────────────────────────────────
# Одна дымовая частица
# ─────────────────────────────────────────────

@dataclass
class SmokeParticle:
    x:     float
    y:     float
    vx:    float
    vy:    float
    alpha: float   # 0-255
    decay: float   # множитель альфа за кадр (0.7)
    size:  int     # радиус в пикселях

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.alpha *= self.decay

    @property
    def alive(self) -> bool:
        return self.alpha >= 1.0


# ─────────────────────────────────────────────
# Система дымовых частиц
# ─────────────────────────────────────────────

class EffectBase:
    """
    Порт EffectBase + NewParticles + ParticleMove.

    Использование:
        EffectBase.init()
        # каждый кадр:
        EffectBase.update(camera_x)
        EffectBase.draw(surface, camera_x)
        # создать дым:
        EffectBase.smoke(SMOKE_BIG, x, y)
        EffectBase.smoke(SMOKE_TINY, x, y, vel_x, vel_y)
    """

    instance: Optional["EffectBase"] = None

    # Параметры каждого типа дыма:
    # (count, speed, spread_angle_deg, alpha, decay, particle_size)
    _SMOKE_PARAMS = {
        SMOKE_BIG:  (13, 7,  45, 150, 0.7, 6),
        1:          (7,  2,  18, 110, 0.7, 4),
        SMOKE_TINY: (4,  2,  3,  10,  0.7, 2),
    }

    _particles: List[SmokeParticle] = []
    _enabled:   bool = True

    @classmethod
    def init(cls):
        cls._particles = []
        cls._enabled   = True
        cls.instance   = cls

    @classmethod
    def set_smoke_enabled(cls, enabled: bool):
        cls._enabled = enabled
        if not enabled:
            cls._particles.clear()

    @classmethod
    def smoke(cls, smoke_type: int, x: int, y: int,
              base_vx: float = 0.0, base_vy: float = 0.0):
        """
        Создаёт дымовые частицы в точке (x, y).
        base_vx/vy — начальная скорость источника (добавляется к частицам).

        Порт NewParticles.smoke():
          count   = кол-во частиц
          speed   = базовая скорость
          spread  = угол разброса в градусах
          alpha   = начальная прозрачность (0-255)
          decay   = множитель альфа за кадр
        """
        if not cls._enabled:
            return

        params = cls._SMOKE_PARAMS.get(smoke_type, cls._SMOKE_PARAMS[1])
        count, speed, spread_deg, alpha, decay, psize = params

        for _ in range(count):
            angle = random.uniform(-spread_deg, spread_deg) * math.pi / 180
            spd   = random.uniform(0.5, 1.5) * speed
            vx    = math.cos(angle) * spd + base_vx
            vy    = math.sin(angle) * spd + base_vy
            p = SmokeParticle(
                x=float(x), y=float(y),
                vx=vx, vy=vy,
                alpha=float(alpha),
                decay=decay,
                size=psize
            )
            cls._particles.append(p)

    @classmethod
    def update(cls, camera_x: int = 0):
        """Обновить все частицы. camera_x для корректного удаления за экраном."""
        if not cls._enabled:
            return
        cls._particles = [p for p in cls._particles if p.alive]
        for p in cls._particles:
            p.update()

    @classmethod
    def draw(cls, surface: pygame.Surface, camera_x: int):
        """Нарисовать все дымовые частицы."""
        if not cls._enabled or not cls._particles:
            return
        for p in cls._particles:
            sx = int(p.x + camera_x)
            sy = int(p.y)
            if not (-p.size <= sx <= surface.get_width() + p.size):
                continue
            a = max(0, min(255, int(p.alpha)))
            if a == 0:
                continue
            # Рисуем тёмно-серый кружок с прозрачностью
            tmp = pygame.Surface((p.size * 2, p.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (40, 40, 40, a), (p.size, p.size), p.size)
            surface.blit(tmp, (sx - p.size, sy - p.size))

    @classmethod
    def particle_count(cls) -> int:
        return len(cls._particles)


# ─────────────────────────────────────────────
# Ветка молнии (внутренний класс)
# ─────────────────────────────────────────────

@dataclass
class BranchData:
    start_x:    float = 0.0
    start_y:    float = 0.0
    end_x:      float = 0.0
    end_y:      float = 0.0
    line_width: float = 0.0


# ─────────────────────────────────────────────
# Молния ЭМИ
# ─────────────────────────────────────────────

class ThunderMain:
    """
    Порт ThunderMain.as — процедурная ветвящаяся молния.

    Алгоритм:
      1. thunder_rewrite(end_x, end_y) — рисует молнию от (0,0) до (end_x, end_y)
      2. Луч делится на 8px-сегменты
      3. Каждый сегмент отклоняется на случайный перпендикуляр
      4. С вероятностью line_width*2/num_steps создаётся ветка
      5. Ветки рекурсивно обрабатываются из стека branchArray
      6. Стирается через 8 кадров (вызов из SAEMP.enter_frame)

    Цвета:
      Линии:  белый (255,255,255)
      Свечение: голубой 0x221FFF → (34, 31, 255)
    """

    WIDTH = 16   # начальная толщина главного луча

    instance: Optional["ThunderMain"] = None

    def __init__(self):
        # Список сегментов для отрисовки: [(x1,y1,x2,y2,width)]
        self._segments: List[Tuple[float,float,float,float,float]] = []
        ThunderMain.instance = self

    def clear(self):
        """Стереть молнию (вызывается на кадр 8 из SAEMP)."""
        self._segments.clear()

    def thunder_rewrite(self, end_x: float, end_y: float):
        """
        Перерисовать молнию от (0,0) до (end_x, end_y).
        Порт thunderReWrite(Point).
        """
        self._segments.clear()
        branch_stack: List[BranchData] = []

        # Главная ветка
        root = BranchData(
            start_x=0.0, start_y=0.0,
            end_x=end_x, end_y=end_y,
            line_width=self.WIDTH
        )
        branch_stack.append(root)

        while branch_stack:
            b = branch_stack.pop()
            self._draw_thunder(b, branch_stack)

    def _draw_thunder(self, b: BranchData,
                      branch_stack: List[BranchData]):
        """
        Порт thunder() — рисует одну ветку молнии.
        Сегмент длиной 8px с случайным перпендикулярным отклонением.
        """
        SEGMENT_LEN = 8

        dx = b.end_x
        dy = b.end_y
        length = math.hypot(dx, dy)
        if length == 0:
            return

        num_steps = max(1, int(length / SEGMENT_LEN))
        branch_prob = b.line_width / num_steps  # вероятность ветвления за шаг

        # Нормализованный вектор к цели
        nx = dx / length * SEGMENT_LEN
        ny = dy / length * SEGMENT_LEN

        cx, cy   = b.start_x, b.start_y
        cur_width = b.line_width

        for _ in range(num_steps):
            # Случайное перпендикулярное отклонение
            perp = (random.random() - 0.5) * 2
            ox   = ny * perp
            oy   = -nx * perp
            # Итоговый вектор шага
            step_x = ox + nx
            step_y = oy + ny
            step_len = math.hypot(step_x, step_y)
            if step_len > 0:
                rand_len = random.random() * 2 * SEGMENT_LEN
                step_x = step_x / step_len * rand_len
                step_y = step_y / step_len * rand_len

            nx_new = cx + step_x
            ny_new = cy + step_y

            # Запоминаем сегмент
            self._segments.append((cx, cy, nx_new, ny_new, cur_width))

            # Ветвление
            if random.random() <= branch_prob * 2:
                branch_w = random.random() * cur_width
                cur_width -= branch_w / 50
                if cur_width < 0:
                    cur_width = 0
                BRANCH_SCALE = 6
                branch = BranchData(
                    start_x=cx,
                    start_y=cy,
                    end_x=step_x * branch_w * BRANCH_SCALE,
                    end_y=step_y * branch_w * BRANCH_SCALE,
                    line_width=branch_w
                )
                branch_stack.append(branch)

            cx, cy = nx_new, ny_new

    def draw(self, surface: pygame.Surface, camera_x: int = 0):
        """
        Нарисовать молнию на поверхности.
        Белые линии + голубое свечение (имитация GlowFilter).
        """
        if not self._segments:
            return

        # Слой свечения (толстые полупрозрачные голубые линии)
        glow_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        for x1, y1, x2, y2, w in self._segments:
            sx1 = int(x1 + camera_x)
            sx2 = int(x2 + camera_x)
            glow_w = max(1, int(w * 3))
            if glow_w > 0:
                pygame.draw.line(glow_surf,
                                 (34, 31, 255, 60),
                                 (sx1, int(y1)), (sx2, int(y2)),
                                 glow_w)
        surface.blit(glow_surf, (0, 0))

        # Белые линии
        for x1, y1, x2, y2, w in self._segments:
            sx1 = int(x1 + camera_x)
            sx2 = int(x2 + camera_x)
            lw = max(1, int(w))
            pygame.draw.line(surface,
                             (255, 255, 255),
                             (sx1, int(y1)), (sx2, int(y2)),
                             lw)

    @property
    def has_lightning(self) -> bool:
        return len(self._segments) > 0


# ─────────────────────────────────────────────
# Глобальные синглтоны (создаются при старте игры)
# ─────────────────────────────────────────────

def init_effects():
    """Инициализировать все эффекты. Вызвать один раз при старте."""
    EffectBase.init()
    ThunderMain()   # создаёт ThunderMain.instance


# ─────────────────────────────────────────────
# Интеграция с игровым циклом
# ─────────────────────────────────────────────
"""
В GameMain.enter_frame():
    EffectBase.update(camera_x)

В GameMain.draw():
    EffectBase.draw(surface, camera_x)
    ThunderMain.instance.draw(surface, camera_x)   # только если EMP активен

Создать дым (из bullet_system.py / unit_system.py):
    from effect_system import EffectBase, SMOKE_BIG, SMOKE_TINY
    EffectBase.smoke(SMOKE_BIG,  unit.x, unit.y)          # взрыв корабля
    EffectBase.smoke(SMOKE_TINY, bullet.x, bullet.y)       # попадание пули

Молния ЭМИ (из special_attacks.py):
    ThunderMain.instance.thunder_rewrite(STAGE_WIDTH, SCREEN_HEIGHT)
    # через 8 кадров:
    ThunderMain.instance.clear()

Отключить дым (настройки):
    EffectBase.set_smoke_enabled(False)
"""
