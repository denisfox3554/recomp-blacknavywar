"""
skill_system.py — порт системы навыков из Navy Battle Flash

─────────────────────────────────────────────────────────────
Структура навыков
─────────────────────────────────────────────────────────────
10 навыков (Skills.as), каждый от 0 до 5 звёзд (STAR_NUM=6 позиций: 0-5).
Навыки соответствуют спецатакам + одна пассивная (скорость):

  ID  Навык              Эффект
  ─────────────────────────────────────────────────────────
   0  HA_BOMBING         +10% бомб за звезду
   1  EMP                +10% длительности ЭМИ за звезду
   2  MINE               +10% мин за звезду
   3  SATELLITE          +10% лазеров за звезду
   4  ATOMIC_BOM         +10% урона атомной бомбы за звезду
   5  (резерв / скорость)
   ...

Очки навыков:
  - За каждый пройденный стейдж даётся 1 очко
  - availableSkillPoint = clearedStageNum + 1 - сумма всех звёзд
  - Максимум звёзд = 5 на навык

Разблокировка экрана навыков:
  SkillSetStarsWrap (обёртка навыка skillId):
    visible = (skillId * 2 <= clearedStageNum + 1)

  То есть:
    Навык 0 → доступен с стейджа -1 (всегда)
    Навык 1 → clearedStageNum >= 1  (после стейджа 1)
    Навык 2 → clearedStageNum >= 3  (после стейджа 3)
    Навык 3 → clearedStageNum >= 5  (после стейджа 5)
    Навык 4 → clearedStageNum >= 7  (после стейджа 7)

─────────────────────────────────────────────────────────────
Экран навыков (SkillStars UI)
─────────────────────────────────────────────────────────────
  - 6 звёзд на навык (0-5 закрашены)
  - Hover: preview сколько звёзд будет
  - Click: подтвердить
  - Нельзя вложить больше availableSkillPoint очков
"""

import pygame
from typing import Optional, List


# ─────────────────────────────────────────────
# Константы навыков (из Skills.as)
# ─────────────────────────────────────────────

class SkillID:
    HA_BOMBING  = 0   # Высотная бомбардировка
    EMP         = 1   # ЭМИ
    MINE        = 2   # Плавающие мины
    SATELLITE   = 3   # Спутниковая атака
    ATOMIC_BOM  = 4   # Атомная бомба

    COUNT       = 5   # всего навыков
    MAX_STARS   = 5   # максимум звёзд на навык
    STAR_NUM    = 6   # позиций в UI (0..5 = 6 штук)

    NAMES = {
        0: "High Altitude Bombing",
        1: "EMP",
        2: "Floating Mine",
        3: "Satellite Attack",
        4: "Atomic Bomb",
    }

    # Стейдж при котором разблокируется экран навыка
    # visible = (skill_id * 2 <= cleared_stage_num + 1)
    UNLOCK_STAGE = {
        0: -1,   # всегда
        1:  1,
        2:  3,
        3:  5,
        4:  7,
    }


# ─────────────────────────────────────────────
# Skills — хранение и логика навыков
# ─────────────────────────────────────────────

class Skills:
    """
    Порт Skills.as — глобальное состояние навыков.

    Использование:
        Skills.instance = Skills()
        Skills.instance.set_skill(SkillID.EMP, 3)
        lvl = Skills.instance.get_skill(SkillID.EMP)  # → 3
        pts = Skills.instance.available_skill_point    # очки для вложения
    """

    instance: Optional["Skills"] = None

    def __init__(self, cleared_stage_num: int = 0):
        self._skills = [0] * SkillID.COUNT   # уровень каждого навыка
        self._cleared_stage_num = cleared_stage_num
        Skills.instance = self

    # ── Доступные очки ────────────────────────────────────────────────

    @property
    def available_skill_point(self) -> int:
        """
        Очки которые ещё можно вложить.
        = (clearedStageNum + 1) - сумма всех звёзд
        """
        return (self._cleared_stage_num + 1) - sum(self._skills)

    def update_cleared_stage(self, cleared_stage_num: int):
        self._cleared_stage_num = cleared_stage_num

    # ── Геттер / сеттер навыка ────────────────────────────────────────

    def get_skill(self, skill_id: int) -> int:
        if 0 <= skill_id < SkillID.COUNT:
            return self._skills[skill_id]
        return 0

    def set_skill(self, level: int, skill_id: int):
        """
        Установить уровень навыка.
        Проверяет что хватает очков и уровень в диапазоне 0-MAX_STARS.
        """
        if not (0 <= skill_id < SkillID.COUNT):
            return
        level = max(0, min(SkillID.MAX_STARS, level))
        old   = self._skills[skill_id]
        delta = level - old
        if self.available_skill_point - delta >= 0:
            self._skills[skill_id] = level

    # ── Сериализация (save/load) ──────────────────────────────────────

    def to_dict(self) -> dict:
        return {"skills": list(self._skills)}

    def from_dict(self, data: dict):
        skills = data.get("skills", [0] * SkillID.COUNT)
        for i in range(SkillID.COUNT):
            self._skills[i] = skills[i] if i < len(skills) else 0

    # ── Разблокировка UI ─────────────────────────────────────────────

    def is_skill_unlocked(self, skill_id: int) -> bool:
        """
        Порт SkillSetStarsWrap:
          visible = (skillId * 2 <= clearedStageNum + 1)
        """
        return skill_id * 2 <= self._cleared_stage_num + 1


# ─────────────────────────────────────────────
# SkillScreen — экран навыков для Pygame
# ─────────────────────────────────────────────

class SkillScreen:
    """
    Pygame-реализация экрана навыков.

    Порт SkillStars + SkillAvailablePoint + SkillSetStarsWrap.

    Показывает 5 строк навыков, каждая с 6 звёздами.
    Hover показывает preview, click подтверждает.

    Использование:
        screen = SkillScreen(skills_instance)
        # каждый кадр:
        screen.handle_event(event)
        screen.draw(surface)
        # проверить выход:
        if screen.done: ...
    """

    STAR_SIZE    = 28    # пиксели на звезду
    STAR_GAP     = 4
    ROW_HEIGHT   = 52
    MARGIN_LEFT  = 60
    MARGIN_TOP   = 80
    STAR_NUM     = 6     # позиций (0..5)

    COLOR_BG         = (20,  30,  50)
    COLOR_STAR_ON    = (255, 220, 50)
    COLOR_STAR_OFF   = (60,  60,  80)
    COLOR_STAR_HOVER = (255, 160, 30)
    COLOR_TEXT       = (200, 200, 200)
    COLOR_LOCKED     = (50,  50,  60)
    COLOR_POINTS     = (100, 255, 180)
    COLOR_TITLE      = (255, 255, 255)

    def __init__(self, skills: Skills):
        self.skills   = skills
        self.done     = False
        # Hover-состояние: (skill_id, preview_stars) или None
        self._hover:  Optional[tuple] = None
        self._font_big   = None
        self._font_mid   = None
        self._font_small = None

    def _init_fonts(self):
        if self._font_big is None:
            self._font_big   = pygame.font.SysFont("Arial", 26, bold=True)
            self._font_mid   = pygame.font.SysFont("Arial", 20)
            self._font_small = pygame.font.SysFont("Arial", 16)

    # ── Геометрия ─────────────────────────────────────────────────────

    def _row_y(self, skill_id: int) -> int:
        return self.MARGIN_TOP + skill_id * self.ROW_HEIGHT

    def _star_rect(self, skill_id: int, star_idx: int) -> pygame.Rect:
        x = self.MARGIN_LEFT + 200 + star_idx * (self.STAR_SIZE + self.STAR_GAP)
        y = self._row_y(skill_id) + 4
        return pygame.Rect(x, y, self.STAR_SIZE, self.STAR_SIZE)

    def _stars_in_row(self, skill_id: int, mx: int) -> int:
        """Сколько звёзд при позиции мыши mx в строке skill_id."""
        step = self.STAR_SIZE + self.STAR_GAP
        x0   = self.MARGIN_LEFT + 200
        idx  = (mx - x0) // step
        return max(0, min(self.STAR_NUM - 1, idx))

    def _row_rect(self, skill_id: int) -> pygame.Rect:
        x  = self.MARGIN_LEFT + 200
        y  = self._row_y(skill_id)
        w  = self.STAR_NUM * (self.STAR_SIZE + self.STAR_GAP)
        return pygame.Rect(x, y, w, self.ROW_HEIGHT - 4)

    # ── Обработка событий ─────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if not pygame.font.get_init():
            pygame.font.init()
        self._init_fonts()

        mx, my = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEMOTION:
            self._hover = None
            for sid in range(SkillID.COUNT):
                if not self.skills.is_skill_unlocked(sid):
                    continue
                if self._row_rect(sid).collidepoint(mx, my):
                    preview = self._stars_in_row(sid, mx) + 1
                    # Проверяем хватает ли очков
                    delta = preview - self.skills.get_skill(sid)
                    if self.skills.available_skill_point - delta >= 0:
                        self._hover = (sid, preview)
                    else:
                        # Максимум что можно
                        max_lvl = self.skills.get_skill(sid) + \
                                  self.skills.available_skill_point
                        self._hover = (sid, min(max_lvl, SkillID.MAX_STARS))
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._hover:
                sid, level = self._hover
                self.skills.set_skill(level, sid)
                from sound_system import SEControl, SE
                SEControl.se_play_except_game(SE.SKILL_SET)

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.done = True

    # ── Отрисовка ─────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        self._init_fonts()

        # Фон
        surface.fill(self.COLOR_BG)

        # Заголовок
        title = self._font_big.render("SKILL SET", True, self.COLOR_TITLE)
        surface.blit(title, (self.MARGIN_LEFT, 30))

        # Доступные очки
        pts_preview = self.skills.available_skill_point
        if self._hover:
            sid, lvl = self._hover
            pts_preview -= (lvl - self.skills.get_skill(sid))
        pts_preview = max(0, pts_preview)
        pts_surf = self._font_mid.render(
            f"Available Points: {pts_preview}", True, self.COLOR_POINTS)
        surface.blit(pts_surf, (surface.get_width() - pts_surf.get_width() - 20, 30))

        # Строки навыков
        for sid in range(SkillID.COUNT):
            self._draw_row(surface, sid)

        # Подсказка
        hint = self._font_small.render("Click to confirm  |  ESC / Enter to close",
                                       True, (100, 100, 120))
        surface.blit(hint, (self.MARGIN_LEFT,
                             surface.get_height() - 30))

    def _draw_row(self, surface: pygame.Surface, skill_id: int):
        unlocked = self.skills.is_skill_unlocked(skill_id)
        y        = self._row_y(skill_id)
        name     = SkillID.NAMES.get(skill_id, f"Skill {skill_id}")

        # Название навыка
        color = self.COLOR_TEXT if unlocked else self.COLOR_LOCKED
        lbl   = self._font_mid.render(name, True, color)
        surface.blit(lbl, (self.MARGIN_LEFT, y + 8))

        if not unlocked:
            lock = self._font_small.render(
                f"Unlock: stage {skill_id * 2}", True, (80, 80, 100))
            surface.blit(lock, (self.MARGIN_LEFT + 200, y + 10))
            return

        # Текущие звёзды
        current = self.skills.get_skill(skill_id)
        # Preview если hover на этой строке
        preview = None
        if self._hover and self._hover[0] == skill_id:
            preview = self._hover[1]

        display = preview if preview is not None else current

        for i in range(self.STAR_NUM):
            rect = self._star_rect(skill_id, i)
            if i < display:
                color = self.COLOR_STAR_HOVER if preview is not None \
                        else self.COLOR_STAR_ON
            else:
                color = self.COLOR_STAR_OFF
            pygame.draw.rect(surface, color, rect, border_radius=4)
            # Рамка
            pygame.draw.rect(surface, (100, 100, 120), rect, 1,
                             border_radius=4)

        # Числовой уровень
        lvl_txt = self._font_small.render(
            f"{display}/{SkillID.MAX_STARS}", True, self.COLOR_TEXT)
        x_after = self.MARGIN_LEFT + 200 + \
                  self.STAR_NUM * (self.STAR_SIZE + self.STAR_GAP) + 10
        surface.blit(lvl_txt, (x_after, y + 10))


# ─────────────────────────────────────────────
# Таблица эффектов навыков (справка)
# ─────────────────────────────────────────────
"""
Как навыки влияют на спецатаки (+10% за каждую звезду):

  SkillID.HA_BOMBING (0):
    bomb_num = 30 * (1 + 0.1 * level)
    level=5 → 45 бомб вместо 30

  SkillID.EMP (1):
    duration = 180 * (1 + 0.1 * level)
    level=5 → 270 кадров (9 сек при 30fps)

  SkillID.MINE (2):
    mine_num = 25 * (1 + 0.1 * level)
    level=5 → 37 мин

  SkillID.SATELLITE (3):
    laser_num = 15 * (1 + 0.1 * level)
    level=5 → 22 лазера

  SkillID.ATOMIC_BOM (4):
    max_damage = 800 * (1 + 0.1 * level)
    level=5 → 1200 урона в центре

Разблокировка (cleared_stage_num):
  Навык 0 → всегда
  Навык 1 → stage 1+
  Навык 2 → stage 3+
  Навык 3 → stage 5+
  Навык 4 → stage 7+

Очки навыков:
  available = cleared_stage_num + 1 - sum(all skill levels)
  Макс 12 стейджей × 1 очко = 12 очков всего
  Макс вложить = 5 навыков × 5 звёзд = 25 звёзд
  Но очков только 12 → нельзя прокачать всё до максимума!
"""
