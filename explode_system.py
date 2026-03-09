"""
explode_system.py — порт системы взрывов из Navy Battle Flash

Три размера взрыва, все одинаковой длительности (13 кадров).
Спрайт-лист: imgSize*10 × imgSize*2  (10 колонок, 2 строки = 20 ячеек, но используется 14)
Кадр выбирается по счётчику: col = frmCnt % 10, row = frmCnt // 10

Типы:
  TINY_EXPLODE   = 1 — маленький (ракеты, пули),     imgSize=20
  SMALL_EXPLODE  = 2 — средний (корабли),             imgSize=30
  MIDDLE_EXPLODE = 3 — большой (линкоры, боссы),      imgSize=60

Использование из Python-кода:
    from explode_system import ExplodeControl, Explosion
    ExplodeControl.spawn(Explosion.SMALL, x, y)    # создать взрыв
    ExplodeControl.enter_frame()                    # обновить каждый кадр
    ExplodeControl.draw(surface, camera_x)          # нарисовать
"""

import pygame
import math
from typing import List, Optional

# ─────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────

TINY_EXPLODE   = 1
SMALL_EXPLODE  = 2
MIDDLE_EXPLODE = 3

IMG_X_NUM = 10   # колонок в спрайт-листе взрыва

# Данные типов взрывов
_EXPLODE_DATA = {
    TINY_EXPLODE:   {"frame_cnt": 13, "img_size": 20},
    SMALL_EXPLODE:  {"frame_cnt": 13, "img_size": 30},
    MIDDLE_EXPLODE: {"frame_cnt": 13, "img_size": 60},
}

# Цвета для дебажной отрисовки (без спрайтов)
_DEBUG_COLORS = {
    TINY_EXPLODE:   [(255, 200, 50), (255, 150, 0), (200, 80, 0)],
    SMALL_EXPLODE:  [(255, 220, 80), (255, 160, 20), (210, 90, 10)],
    MIDDLE_EXPLODE: [(255, 240, 100), (255, 180, 40), (220, 100, 20)],
}


# ─────────────────────────────────────────────
# Класс одного взрыва
# ─────────────────────────────────────────────

class ExplodeBase:
    """
    Один активный взрыв.

    Анимация: 13 кадров из спрайт-листа imgSize*10 × imgSize*2.
    Кадр выбирается по frmCnt: col = frmCnt % IMG_X_NUM, row = frmCnt // IMG_X_NUM.
    Отрисовывается центрированно: draw_x = x - imgSize/2, draw_y = y - imgSize/2.

    Без спрайтов — рисуется как расширяющийся полупрозрачный круг.
    """

    def __init__(self, explode_type: int):
        data = _EXPLODE_DATA[explode_type]
        self.explode_type = explode_type
        self.frame_cnt    = data["frame_cnt"]   # максимум кадров
        self.img_size     = data["img_size"]
        self.x            = 0.0
        self.y            = 0.0
        self._frm         = 0
        self._sprite      = None   # pygame.Surface — устанавливается извне

    def init_public(self):
        self._frm = 0

    def enter_frame(self) -> bool:
        """Обновление. Возвращает True пока взрыв активен."""
        self._frm += 1
        return self._frm <= self.frame_cnt

    def get_sprite_rect(self) -> tuple:
        """
        Возвращает (col, row) в спрайт-листе для текущего кадра.
        col = frmCnt % 10, row = frmCnt // 10
        """
        col = self._frm % IMG_X_NUM
        row = self._frm // IMG_X_NUM
        return col, row

    def draw(self, surface: pygame.Surface, camera_x: int,
             sprites: Optional[dict] = None):
        """
        Рисует взрыв.
        sprites — словарь {explode_type: pygame.Surface} со спрайт-листами.
        Без спрайтов рисует расширяющийся круг.
        """
        sx = int(self.x + camera_x)
        sy = int(self.y)

        if not (-(self.img_size) <= sx <= surface.get_width() + self.img_size):
            return

        if sprites and self.explode_type in sprites:
            sheet = sprites[self.explode_type]
            col, row = self.get_sprite_rect()
            src_rect = pygame.Rect(
                col * self.img_size,
                row * self.img_size,
                self.img_size,
                self.img_size
            )
            dst_x = sx - self.img_size // 2
            dst_y = sy - self.img_size // 2
            surface.blit(sheet, (dst_x, dst_y), src_rect)
        else:
            # Дебажная отрисовка: расширяющийся круг
            progress = self._frm / self.frame_cnt   # 0.0 → 1.0
            # Радиус: растёт до середины, потом немного сжимается
            if progress < 0.5:
                r = int(self.img_size / 2 * progress * 2)
            else:
                r = int(self.img_size / 2 * (1.0 - (progress - 0.5)))
            r = max(1, r)

            # Цвет: ярко-жёлтый → оранжевый → красный по ходу анимации
            colors = _DEBUG_COLORS[self.explode_type]
            ci = min(int(progress * len(colors)), len(colors) - 1)
            color = colors[ci]

            alpha = int(255 * (1.0 - progress * 0.7))
            tmp = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*color, alpha), (r, r), r)
            surface.blit(tmp, (sx - r, sy - r))


# ─────────────────────────────────────────────
# Менеджер взрывов (пул + итерация)
# ─────────────────────────────────────────────

class ExplodeControl:
    """
    Глобальный менеджер взрывов с object pooling.

    Использование:
        ExplodeControl.init()
        # каждый кадр:
        ExplodeControl.enter_frame()
        ExplodeControl.draw(surface, camera_x)
        # создать взрыв:
        ExplodeControl.spawn(SMALL_EXPLODE, x, y)
    """

    explode_array: List[ExplodeBase] = []
    stock_object:  dict = {}   # explode_type → [recycled ExplodeBase]
    sprites:       dict = {}   # explode_type → pygame.Surface (спрайт-лист)

    @classmethod
    def init(cls):
        cls.explode_array = []
        cls.stock_object  = {}

    @classmethod
    def load_sprites(cls, sprite_dict: dict):
        """
        Загрузить спрайт-листы для взрывов.
        sprite_dict: {TINY_EXPLODE: surface, SMALL_EXPLODE: surface, ...}
        """
        cls.sprites = sprite_dict

    @classmethod
    def spawn(cls, explode_type: int, x: float, y: float) -> ExplodeBase:
        """Создать взрыв в позиции (x, y)."""
        stock = cls.stock_object.setdefault(explode_type, [])
        if stock:
            e = stock.pop()
            e.init_public()
        else:
            e = ExplodeBase(explode_type)
        e.x = x
        e.y = y
        cls.explode_array.append(e)
        return e

    @classmethod
    def enter_frame(cls):
        """Обновить все взрывы. Завершённые — возвращаем в пул."""
        to_remove = []
        for e in cls.explode_array:
            alive = e.enter_frame()
            if not alive:
                to_remove.append(e)
        for e in to_remove:
            cls.explode_array.remove(e)
            cls.stock_object.setdefault(e.explode_type, []).append(e)

    @classmethod
    def draw(cls, surface: pygame.Surface, camera_x: int):
        for e in cls.explode_array:
            e.draw(surface, camera_x, cls.sprites)

    @classmethod
    def end(cls):
        cls.explode_array = []
        cls.stock_object  = {}


# ─────────────────────────────────────────────
# Удобные псевдонимы (используются из unit_system)
# ─────────────────────────────────────────────

class Explosion:
    """Константы для удобного вызова ExplodeControl.spawn()."""
    TINY   = TINY_EXPLODE
    SMALL  = SMALL_EXPLODE
    MIDDLE = MIDDLE_EXPLODE
