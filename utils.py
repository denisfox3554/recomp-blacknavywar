"""
utils.py — порт утилит из Navy Battle Flash (game.utl.*)

Содержит:
  KeyCode     — коды клавиш (AS3 → pygame)
  MathUtl     — детерминированный LCG-генератор случайных чисел
  ColorConst  — цветовые константы
  FPSMeasure  — счётчик реального FPS
  InputManager— глобальный менеджер клавиатуры и мыши (замена BtnControl)

BtnControl и PreventClick — Flash-специфика (MovieClip), в Python не нужны.
Их роль выполняет InputManager.
"""

import time
import pygame
from typing import Set


# ─────────────────────────────────────────────
# KeyCode — соответствие AS3 → pygame
# ─────────────────────────────────────────────

class KeyCode:
    """
    Порт KeyCode.as.
    Константы клавиш в pygame (pygame.K_*).

    Использование:
        if InputManager.is_pressed(KeyCode.A):
            special_attack(SA_HA_BOMB)
    """
    # Стрелки
    UP    = pygame.K_UP
    DOWN  = pygame.K_DOWN
    LEFT  = pygame.K_LEFT
    RIGHT = pygame.K_RIGHT

    # Цифры (верхний ряд)
    NUM0 = pygame.K_0
    NUM1 = pygame.K_1
    NUM2 = pygame.K_2
    NUM3 = pygame.K_3
    NUM4 = pygame.K_4
    NUM5 = pygame.K_5
    NUM6 = pygame.K_6
    NUM7 = pygame.K_7
    NUM8 = pygame.K_8
    NUM9 = pygame.K_9

    # Цифровой блок (numpad)
    NUMPAD0 = pygame.K_KP0
    NUMPAD1 = pygame.K_KP1
    NUMPAD2 = pygame.K_KP2
    NUMPAD3 = pygame.K_KP3
    NUMPAD4 = pygame.K_KP4
    NUMPAD5 = pygame.K_KP5
    NUMPAD6 = pygame.K_KP6
    NUMPAD7 = pygame.K_KP7
    NUMPAD8 = pygame.K_KP8
    NUMPAD9 = pygame.K_KP9

    # Буквы
    A = pygame.K_a
    B = pygame.K_b
    C = pygame.K_c
    D = pygame.K_d
    E = pygame.K_e
    F = pygame.K_f
    G = pygame.K_g
    H = pygame.K_h
    I = pygame.K_i
    J = pygame.K_j
    K = pygame.K_k
    L = pygame.K_l
    M = pygame.K_m
    N = pygame.K_n
    O = pygame.K_o
    P = pygame.K_p
    Q = pygame.K_q
    R = pygame.K_r
    S = pygame.K_s
    T = pygame.K_t
    U = pygame.K_u
    V = pygame.K_v
    W = pygame.K_w
    X = pygame.K_x
    Y = pygame.K_y
    Z = pygame.K_z

    # Служебные
    SHIFT  = pygame.K_LSHIFT
    SPACE  = pygame.K_SPACE
    ESCAPE = pygame.K_ESCAPE
    CTRL   = pygame.K_LCTRL
    ENTER  = pygame.K_RETURN

    # Строковое представление (для иконок HUD)
    KEY_STR = {
        pygame.K_0: "0", pygame.K_1: "1", pygame.K_2: "2",
        pygame.K_3: "3", pygame.K_4: "4", pygame.K_5: "5",
        pygame.K_6: "6", pygame.K_7: "7", pygame.K_8: "8",
        pygame.K_9: "9",
        pygame.K_a: "A", pygame.K_b: "B", pygame.K_c: "C",
        pygame.K_d: "D", pygame.K_e: "E", pygame.K_f: "F",
        pygame.K_g: "G", pygame.K_h: "H", pygame.K_i: "I",
        pygame.K_j: "J", pygame.K_k: "K", pygame.K_l: "L",
        pygame.K_m: "M", pygame.K_n: "N", pygame.K_o: "O",
        pygame.K_p: "P", pygame.K_q: "Q", pygame.K_r: "R",
        pygame.K_s: "S", pygame.K_t: "T", pygame.K_u: "U",
        pygame.K_v: "V", pygame.K_w: "W", pygame.K_x: "X",
        pygame.K_y: "Y", pygame.K_z: "Z",
    }


# ─────────────────────────────────────────────
# MathUtl — детерминированный LCG генератор
# ─────────────────────────────────────────────

class MathUtl:
    """
    Порт MathUtl.as — линейный конгруэнтный генератор (LCG).

    Параметры совпадают с оригиналом:
      a = 1103515245  (RND_ANUM)
      c = 12345       (RND_CNMU)
      m = 0xFFFFFFFF  (uint.MAX_VALUE)

    ВАЖНО: используется в оригинале везде вместо Math.random()
    для воспроизводимости поведения. В Python-версии можно
    использовать и стандартный random, но MathUtl нужен там,
    где важна совместимость с оригиналом (например, в тестах).

    Использование:
        MathUtl.set_random_seed(42)
        v = MathUtl.random()   # 0.0 ... 1.0
        s = MathUtl.get_sign(-5)  # -1
    """

    _RND_MOD  = 0xFFFFFFFF   # uint.MAX_VALUE
    _RND_A    = 1103515245
    _RND_C    = 12345
    _prev: int = 0

    @classmethod
    def set_random_seed(cls, seed: float):
        cls._prev = int(seed * cls._RND_MOD) & cls._RND_MOD

    @classmethod
    def random(cls) -> float:
        cls._prev = (cls._RND_A * cls._prev + cls._RND_C) % cls._RND_MOD
        return cls._prev / cls._RND_MOD

    @staticmethod
    def get_sign(value: float) -> int:
        """Возвращает 1 если value >= 0, иначе -1."""
        return 1 if value >= 0 else -1


# ─────────────────────────────────────────────
# ColorConst — цветовые константы
# ─────────────────────────────────────────────

class ColorConst:
    """
    Порт ColorConst.as.
    Цвета как pygame (R, G, B) кортежи.

    Оригинал хранил как uint 0xRRGGBB.
    Примечание: в оригинале CYAN ошибочно = 255 (совпадает с BLUE).
    """
    RED     = (255, 0,   0)
    BLUE    = (0,   0,   255)
    GREEN   = (0,   255, 0)
    YELLOW  = (255, 255, 0)
    MAGENTA = (255, 0,   255)   # MAZENDA в оригинале
    CYAN    = (0,   255, 255)   # в оригинале была опечатка (= BLUE)
    WHITE   = (255, 255, 255)
    BLACK   = (0,   0,   0)

    # Цвета для сторон (игрок = чёрный, враг = красный)
    FRIEND_COLOR = BLACK
    ENEMY_COLOR  = RED

    @staticmethod
    def from_uint(color: int) -> tuple:
        """Конвертировать 0xRRGGBB в (R, G, B)."""
        r = (color >> 16) & 0xFF
        g = (color >> 8)  & 0xFF
        b =  color        & 0xFF
        return (r, g, b)

    @staticmethod
    def with_alpha(color: tuple, alpha: int) -> tuple:
        """Добавить альфа-канал: (R,G,B) → (R,G,B,A)."""
        return (*color, alpha)


# ─────────────────────────────────────────────
# FPSMeasure — счётчик реального FPS
# ─────────────────────────────────────────────

class FPSMeasure:
    """
    Порт FPSMesure.as.
    Обновляет значение FPS каждые 500мс.

    Использование:
        fps_counter = FPSMeasure()
        # каждый кадр:
        current_fps = fps_counter.enter_frame()
    """
    UPDATE_INTERVAL = 0.5   # секунды (500ms в оригинале)

    def __init__(self):
        self._draw_count = 0
        self._fps        = 0.0
        self._last_time  = time.time()

    def enter_frame(self) -> float:
        """Вызывать каждый кадр. Возвращает текущий FPS."""
        self._draw_count += 1
        now     = time.time()
        elapsed = now - self._last_time
        if elapsed >= self.UPDATE_INTERVAL:
            self._fps        = round(self._draw_count / elapsed, 1)
            self._last_time  = now
            self._draw_count = 0
        return self._fps

    @property
    def fps(self) -> float:
        return self._fps


# ─────────────────────────────────────────────
# InputManager — замена BtnControl для Python
# ─────────────────────────────────────────────

class InputManager:
    """
    Глобальный менеджер ввода — замена Flash BtnControl/PreventClick.

    Отслеживает:
      - Нажатые клавиши (held)
      - Только что нажатые (just_pressed) — срабатывает один раз
      - Только что отпущенные (just_released)
      - Позицию и клики мыши

    Использование в игровом цикле:
        # В начале каждого кадра:
        InputManager.update()

        # В обработчике событий:
        for event in pygame.event.get():
            InputManager.handle_event(event)

        # Проверки:
        if InputManager.just_pressed(KeyCode.A):    # спецатака
        if InputManager.is_held(KeyCode.LEFT):      # скролл камеры
        if InputManager.is_held(KeyCode.SHIFT):     # быстрый скролл
        mouse_x, mouse_y = InputManager.mouse_pos()
    """

    _held:          Set[int] = set()
    _just_pressed:  Set[int] = set()
    _just_released: Set[int] = set()
    _mouse_pos:     tuple    = (0, 0)
    _mouse_held:    Set[int] = set()
    _mouse_just_dn: Set[int] = set()
    _mouse_just_up: Set[int] = set()

    @classmethod
    def update(cls):
        """Сбросить одноразовые состояния. Вызывать в начале каждого кадра."""
        cls._just_pressed.clear()
        cls._just_released.clear()
        cls._mouse_just_dn.clear()
        cls._mouse_just_up.clear()

    @classmethod
    def handle_event(cls, event):
        """Передать pygame-событие в менеджер."""
        if event.type == pygame.KEYDOWN:
            cls._held.add(event.key)
            cls._just_pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            cls._held.discard(event.key)
            cls._just_released.add(event.key)
        elif event.type == pygame.MOUSEMOTION:
            cls._mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            cls._mouse_held.add(event.button)
            cls._mouse_just_dn.add(event.button)
            cls._mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONUP:
            cls._mouse_held.discard(event.button)
            cls._mouse_just_up.add(event.button)
            cls._mouse_pos = event.pos

    @classmethod
    def is_held(cls, key: int) -> bool:
        """Клавиша удерживается."""
        return key in cls._held

    @classmethod
    def just_pressed(cls, key: int) -> bool:
        """Клавиша нажата именно в этом кадре."""
        return key in cls._just_pressed

    @classmethod
    def just_released(cls, key: int) -> bool:
        """Клавиша отпущена именно в этом кадре."""
        return key in cls._just_released

    @classmethod
    def mouse_pos(cls) -> tuple:
        return cls._mouse_pos

    @classmethod
    def mouse_held(cls, button: int = 1) -> bool:
        """Кнопка мыши удерживается (1=левая, 3=правая)."""
        return button in cls._mouse_held

    @classmethod
    def mouse_just_clicked(cls, button: int = 1) -> bool:
        return button in cls._mouse_just_up

    @classmethod
    def shift_held(cls) -> bool:
        return (cls.K_LSHIFT in cls._held or
                pygame.K_RSHIFT in cls._held)

    # Псевдоним для удобства
    K_LSHIFT = pygame.K_LSHIFT


# ─────────────────────────────────────────────
# Полная таблица управления игрой (справочник)
# ─────────────────────────────────────────────
"""
УПРАВЛЕНИЕ (из консоли и AvailableUnitData):

Скролл камеры:
  ← →          — скролл 10px/кадр
  Shift + ← →  — скролл 40px/кадр (×4)
  Мышь у края 10% — скролл ×4
  Мышь у края 20% — скролл ×1

Покупка юнитов:
  1 — Patrol Boat          (доступно с начала)
  2 — Frigate              (доступно с начала)
  3 — Submarine            (доступно с начала)
  4 — Helicopter           (доступно с начала)
  5 — AA-Gun Ship          (доступно с начала)
  6 — Torpedo Boat         (стейдж 1+)
  7 — Torpedo Bomber       (стейдж 1+)
  8 — Destroyer            (стейдж 3+)
  9 — Anti-sub Helicopter  (стейдж 4+)
  0 — Fighter              (стейдж 5+)
  Q — Cruiser              (стейдж 6+)
  W — Battleship           (стейдж 7+)
  E — Atomic Submarine     (стейдж 8+)
  R — Bomber               (стейдж 9+)
  T — Carrier              (стейдж 10+)

Батареи:
  Y — Artillery Battery    (доступно с начала)
  U — MachineGun Battery   (стейдж 2+)
  I — Missile Battery      (стейдж 4+)
  O — Torpedo Battery      (стейдж 6+)
  P — Sub-Fortress         (стейдж 11+)

Строения (экономика):
  Z — Supply Line          (ресурсы/время)
  X — Recycler             (ресурсы за убийства)
  C — Factory              (скорость создания юнитов)
  V — Repairman            (восстановление базы)
  B — Warehouse            (макс. ресурсы)
  N — Base Upgrade         (HP базы + слоты батарей)

Специальные атаки:
  A — High Altitude Bombing  (reload 300)
  S — EMP                    (reload 300)
  D — Floating Mines         (reload 300)
  F — Satellite Attack       (reload 300)
  G — Atomic Bomb            (reload 500)

Прочее:
  M       — переключить скорость игры (LOW/NORMAL/HIGH = 24/30/40 fps)
  Shift+1 — добавить 2 юнита в очередь (стек до 10)
  Escape  — пауза / меню опций
"""
