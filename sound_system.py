"""
sound_system.py — порт звуковой системы из Navy Battle Flash

Два класса:
  SEControl  — звуковые эффекты (SFX), до 5 одновременно
  BGMControl — фоновая музыка (BGM) + джинглы победы/поражения

─────────────────────────────────────────────────────────────
SE (Sound Effects) — 19 звуков
─────────────────────────────────────────────────────────────
Приоритеты (priority):
  PR_LOW    = -100  — пулемёт (может быть вытеснен)
  PR_MLOW   =  -50  — взрывы, ракеты, торпеды
  PR_MIDDLE =    0  — малые взрывы, лазер
  PR_HIGH   =  100  — спецатаки, ресурсы, тревога босса

Система каналов:
  - 5 одновременных каналов (playingSe[0..4])
  - Каждый кадр playArray сбрасывается: один и тот же звук не дублируется
  - Если все каналы заняты: вытесняем канал с меньшим приоритетом
  - Если вытеснить нечего — звук пропускается

Громкость SE:
  volume = se_volume / 10 / 2 * vol_mult
  (se_volume: 0-10, vol_mult: 1.0 для большинства,
   3.0 для EMP, 1.5 для атомной бомбы)

─────────────────────────────────────────────────────────────
BGM — 3 трека + 2 джингла
─────────────────────────────────────────────────────────────
  NORMAL    — основной игровой трек (зациклен)
  BOSS      — трек боссов (зациклен)
  INVENTORY — экран инвентаря/навыков (зациклен)
  WIN       — джингл победы (1 раз)
  LOSE      — джингл поражения (1 раз)

─────────────────────────────────────────────────────────────
Файлы (положить рядом с sound_system.py):
  sfx/gun00.ogg, bosu01.ogg, bom17c.ogg, bom18.ogg, bom11.ogg,
      gun13a.ogg, bom28b.ogg, bom03.ogg, bom19a.ogg, bom26b.ogg,
      swing03.ogg, kachi42.ogg, thunder.ogg, alarm00r.ogg,
      fighter.ogg, noise19.ogg, bom00.ogg, wood04.ogg, alarm01.ogg
  bgm/bgm_normal.ogg, bgm_boss.ogg, bgm_inventory.ogg,
      jingle_win.ogg, jingle_lose.ogg
"""

import os
import pygame
from typing import Optional, List


# ─────────────────────────────────────────────
# Инициализация pygame.mixer
# ─────────────────────────────────────────────

def init_sound(frequency: int = 44100):
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=frequency, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(16)


# ─────────────────────────────────────────────
# Константы SE
# ─────────────────────────────────────────────

class SE:
    MACHINE_GUN           = 0
    AASHARPNEL            = 1
    SMALL_UNIT_EXPLODE    = 2
    MISSLIE_EXPLODE       = 3   # опечатка сохранена из оригинала
    BOM                   = 4
    BATTLESHIP_BULLET     = 5
    TORPEDO_EXPLODE       = 6
    BATTLESHIP_BULLET_EXP = 7
    AASHARPNEL_EXP        = 8
    BATTERY_EXP           = 9
    SCREEN_TRNS           = 10
    SKILL_SET             = 11
    EMP                   = 12
    FLOATING_MINE         = 13
    HA_BOMBING            = 14
    SA_LASER              = 15
    AA_BOMB               = 16
    RESOURCE_MAX          = 17
    BOSS_ALARM            = 18


# Приоритеты
_PR_LOW    = -100
_PR_MLOW   =  -50
_PR_MIDDLE =    0
_PR_HIGH   =  100

# (priority, filename, end_time_ms, volume_mult)
_SE_DATABASE = {
    SE.MACHINE_GUN:           (_PR_LOW,    "sfx/gun00.ogg",      200, 1.0),
    SE.AASHARPNEL:            (_PR_MLOW,   "sfx/bosu01.ogg",     300, 1.0),
    SE.SMALL_UNIT_EXPLODE:    (_PR_MIDDLE, "sfx/bom17c.ogg",    1000, 1.0),
    SE.MISSLIE_EXPLODE:       (_PR_MLOW,   "sfx/bom18.ogg",      500, 1.0),
    SE.BOM:                   (_PR_MLOW,   "sfx/bom11.ogg",     1000, 1.0),
    SE.BATTLESHIP_BULLET:     (_PR_MLOW,   "sfx/gun13a.ogg",     500, 1.0),
    SE.TORPEDO_EXPLODE:       (_PR_MLOW,   "sfx/bom28b.ogg",     500, 1.0),
    SE.BATTLESHIP_BULLET_EXP: (_PR_MLOW,   "sfx/bom03.ogg",      400, 1.0),
    SE.AASHARPNEL_EXP:        (_PR_MLOW,   "sfx/bom19a.ogg",     400, 1.0),
    SE.BATTERY_EXP:           (_PR_MLOW,   "sfx/bom26b.ogg",     400, 1.0),
    SE.SCREEN_TRNS:           (_PR_MLOW,   "sfx/swing03.ogg",    100, 1.0),
    SE.SKILL_SET:             (_PR_MLOW,   "sfx/kachi42.ogg",    100, 1.0),
    SE.EMP:                   (_PR_HIGH,   "sfx/thunder.ogg",   4000, 3.0),
    SE.FLOATING_MINE:         (_PR_HIGH,   "sfx/alarm00r.ogg",  4000, 1.0),
    SE.HA_BOMBING:            (_PR_HIGH,   "sfx/fighter.ogg",   4000, 1.0),
    SE.SA_LASER:              (_PR_MIDDLE, "sfx/noise19.ogg",   2000, 1.0),
    SE.AA_BOMB:               (_PR_HIGH,   "sfx/bom00.ogg",     2000, 1.5),
    SE.RESOURCE_MAX:          (_PR_HIGH,   "sfx/wood04.ogg",     600, 1.0),
    SE.BOSS_ALARM:            (_PR_HIGH,   "sfx/alarm01.ogg",   1500, 1.0),
}


# ─────────────────────────────────────────────
# Один активный SE-канал (порт SEPlayData)
# ─────────────────────────────────────────────

class _SEChannel:
    def __init__(self):
        self.channel:  Optional[pygame.mixer.Channel] = None
        self.priority: int  = _PR_LOW
        self.end_time: int  = 0
        self.start_ms: int  = 0
        self.playing:  bool = False

    @property
    def elapsed_ms(self) -> int:
        if not self.playing:
            return 999999
        return pygame.time.get_ticks() - self.start_ms

    @property
    def is_done(self) -> bool:
        if not self.playing:
            return True
        if self.channel and not self.channel.get_busy():
            self.playing = False
            return True
        return self.elapsed_ms > self.end_time

    def stop(self):
        if self.channel:
            self.channel.stop()
        self.playing = False

    def play(self, sound: pygame.mixer.Sound,
             priority: int, end_time: int, volume: float) -> bool:
        ch = pygame.mixer.find_channel()
        if ch is None:
            return False
        ch.set_volume(min(1.0, volume))
        ch.play(sound)
        self.channel  = ch
        self.priority = priority
        self.end_time = end_time
        self.start_ms = pygame.time.get_ticks()
        self.playing  = True
        return True


# ─────────────────────────────────────────────
# SEControl
# ─────────────────────────────────────────────

class SEControl:
    """
    Порт SEControl.as — система звуковых эффектов.

    Использование:
        SEControl.init()          # один раз при старте
        SEControl.enter_frame()   # каждый кадр (сброс дедупликации)
        SEControl.se_play(SE.MACHINE_GUN)
        SEControl.se_volume = 7   # громкость 0-10
    """

    NUM_CHANNELS = 5
    se_volume: int = 7

    _sounds:     dict = {}
    _channels:   List[_SEChannel] = []
    _play_frame: set = set()

    @classmethod
    def init(cls, sound_dir: str = "."):
        cls._channels   = [_SEChannel() for _ in range(cls.NUM_CHANNELS)]
        cls._play_frame = set()
        cls._sounds     = {}
        for se_id, (_, filename, _, _) in _SE_DATABASE.items():
            path = os.path.join(sound_dir, filename)
            if os.path.exists(path):
                try:
                    cls._sounds[se_id] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"[SEControl] не удалось загрузить {path}: {e}")

    @classmethod
    def enter_frame(cls):
        """Сброс дедупликации — вызывать каждый кадр."""
        cls._play_frame.clear()

    @classmethod
    def se_play(cls, se_id: int):
        """Воспроизвести звук. Один и тот же звук — не более 1 раза за кадр."""
        if cls.se_volume == 0:
            return
        if se_id in cls._play_frame:
            return
        cls._play_frame.add(se_id)

        if se_id not in _SE_DATABASE:
            return
        priority, _, end_time, vol_mult = _SE_DATABASE[se_id]
        volume = (cls.se_volume / 10 / 2) * vol_mult

        sound = cls._sounds.get(se_id)
        if sound is None:
            return

        slot = cls._find_slot(priority)
        if slot < 0:
            return
        cls._channels[slot].play(sound, priority, end_time, volume)

    @classmethod
    def _find_slot(cls, new_priority: int) -> int:
        """Порт searchSe() — найти свободный или вытесняемый канал."""
        # Сортируем: самый старый первым
        order = sorted(range(cls.NUM_CHANNELS),
                       key=lambda i: cls._channels[i].elapsed_ms,
                       reverse=True)
        # 1. Свободный канал
        for i in order:
            if cls._channels[i].is_done:
                return i
        # 2. Вытеснить с низшим приоритетом
        for i in order:
            if cls._channels[i].priority < new_priority:
                cls._channels[i].stop()
                return i
        return -1

    @classmethod
    def se_play_except_game(cls, se_id: int):
        """Воспроизвести вне игрового цикла (сбрасывает дедупликацию)."""
        cls.enter_frame()
        cls.se_play(se_id)


# ─────────────────────────────────────────────
# BGMControl
# ─────────────────────────────────────────────

class BGM:
    NORMAL    = "normal"
    BOSS      = "boss"
    INVENTORY = "inventory"
    WIN       = "win"
    LOSE      = "lose"


class BGMControl:
    """
    Порт BGMControl.as — фоновая музыка.

    Использование:
        BGMControl.init()
        BGMControl.play_bgm(BGM.NORMAL)     # старт стейджа
        BGMControl.play_bgm(BGM.BOSS)       # появился босс
        BGMControl.play_gingle(BGM.WIN)     # победа
        BGMControl.play_gingle(BGM.LOSE)    # поражение
        BGMControl.set_volume(7)            # громкость 0-10
    """

    bgm_volume: int = 7

    _BGM_FILES = {
        BGM.NORMAL:    "bgm/bgm_normal.ogg",
        BGM.BOSS:      "bgm/bgm_boss.ogg",
        BGM.INVENTORY: "bgm/bgm_inventory.ogg",
    }
    _GINGLE_FILES = {
        BGM.WIN:  "bgm/jingle_win.ogg",
        BGM.LOSE: "bgm/jingle_lose.ogg",
    }

    _sounds:      dict = {}
    _gingles:     dict = {}
    _now_playing: str  = ""
    _channel:     Optional[pygame.mixer.Channel] = None

    @classmethod
    def init(cls, sound_dir: str = "."):
        cls._sounds  = {}
        cls._gingles = {}
        for name, filename in cls._BGM_FILES.items():
            path = os.path.join(sound_dir, filename)
            if os.path.exists(path):
                try:
                    cls._sounds[name] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"[BGMControl] не удалось загрузить {path}: {e}")
        for name, filename in cls._GINGLE_FILES.items():
            path = os.path.join(sound_dir, filename)
            if os.path.exists(path):
                try:
                    cls._gingles[name] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"[BGMControl] не удалось загрузить {path}: {e}")

    @classmethod
    def _get_volume(cls) -> float:
        return cls.bgm_volume / 10

    @classmethod
    def play_bgm(cls, bgm_id: str):
        """Запустить зацикленный трек. Повторный вызов того же — игнорируется."""
        if cls._now_playing == bgm_id and cls._channel is not None:
            return
        cls.stop()
        sound = cls._sounds.get(bgm_id)
        if sound is None:
            return
        sound.set_volume(cls._get_volume())
        cls._channel     = sound.play(loops=-1)
        cls._now_playing = bgm_id

    @classmethod
    def play_gingle(cls, gingle_id: str):
        """Остановить BGM и воспроизвести джингл один раз."""
        cls.stop()
        sound = cls._gingles.get(gingle_id)
        if sound is None:
            return
        sound.set_volume(cls._get_volume())
        sound.play(loops=0)

    @classmethod
    def stop(cls):
        if cls._channel is not None:
            cls._channel.stop()
            cls._channel = None
        cls._now_playing = ""

    @classmethod
    def set_volume(cls, volume: int):
        cls.bgm_volume = max(0, min(10, volume))
        sound = cls._sounds.get(cls._now_playing)
        if sound:
            sound.set_volume(cls._get_volume())


# ─────────────────────────────────────────────
# Инициализация всего звука
# ─────────────────────────────────────────────

def init_all_sound(sound_dir: str = "."):
    """
    Вызвать один раз после pygame.init().
    sound_dir — папка где лежат подпапки sfx/ и bgm/.
    Если файлов нет — игра работает без звука.
    """
    init_sound()
    SEControl.init(sound_dir)
    BGMControl.init(sound_dir)


# ─────────────────────────────────────────────
# Когда какой звук играет (справка)
# ─────────────────────────────────────────────
"""
SE.MACHINE_GUN         — каждый выстрел пулемёта корабля/батареи
SE.AASHARPNEL          — запуск AAS-ракеты
SE.SMALL_UNIT_EXPLODE  — гибель малого корабля/вертолёта
SE.MISSLIE_EXPLODE     — взрыв ракеты (missile)
SE.BOM                 — взрыв бомбы (Bomber, HA Bombing)
SE.BATTLESHIP_BULLET   — выстрел линкора / parabola battery
SE.TORPEDO_EXPLODE     — взрыв торпеды
SE.BATTLESHIP_BULLET_EXP — попадание снаряда линкора
SE.AASHARPNEL_EXP      — взрыв шрапнели AAS
SE.BATTERY_EXP         — выстрел artillery батареи
SE.SCREEN_TRNS         — переход между экранами
SE.SKILL_SET           — улучшение навыка
SE.EMP                 — активация ЭМИ  (PR_HIGH, vol×3)
SE.FLOATING_MINE       — сброс плавающих мин
SE.HA_BOMBING          — высотная бомбардировка
SE.SA_LASER            — удар спутникового лазера (каждые 10 кадров)
SE.AA_BOMB             — ядерный взрыв  (PR_HIGH, vol×1.5)
SE.RESOURCE_MAX        — ресурсы переполнены
SE.BOSS_ALARM          — появление босса

BGM.NORMAL    → play_bgm() при старте стейджа
BGM.BOSS      → play_bgm() когда появляется босс (из AIStage._spawn_boss)
BGM.INVENTORY → play_bgm() на экране навыков/инвентаря
BGM.WIN       → play_gingle() при stage_clear()
BGM.LOSE      → play_gingle() при game_over() (кроме Survival)
"""
