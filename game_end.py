"""
game_end.py — порт системы завершения игры из Navy Battle Flash

Три исхода:
  GAME_OVER   — база игрока уничтожена
  STAGE_CLEAR — база врага уничтожена
  SURVIVAL    — режим выживания (база уничтожена — это и есть конец)

Подсчёт очков (Campaign):
  score  = GameParams.score  (очки за уничтожение юнитов)
  bonus  = score * scoreRate * 2
  total  = score + bonus
  Анимированный счётчик: сначала нарастает score, потом bonus, потом показывает total.

Подсчёт очков (Survival):
  high_score = GameParams.score  (без бонуса)

После завершения:
  Первое прохождение стейджа → переход на экран новых юнитов (WR_NEWUNIT)
  Повторное / Game Over       → возврат к выбору стейджа  (WR_STSELECT)

Anti-cheat (Flash-специфика):
  Счёт кодируется в base-17/18 и сравнивается при отправке в онлайн-рейтинг.
  В Python-версии онлайн-рейтинга нет — оставляем только локальный хайскор.
"""

import pygame
from enum import IntEnum
from typing import Optional, Callable

# ─────────────────────────────────────────────
# Константы режимов игры (из GameConstants)
# ─────────────────────────────────────────────
GAME_MODE_CMPN_EASY   = 1
GAME_MODE_CMPN_NORMAL = 2
GAME_MODE_CMPN_HARD   = 4
GAME_MODE_CAMPAIN     = GAME_MODE_CMPN_EASY | GAME_MODE_CMPN_NORMAL | GAME_MODE_CMPN_HARD
GAME_MODE_SURVIVAL    = 8
GAME_MODE_CLIMAX      = 16

GST_PLAYING   = 0
GST_GAME_OVER = 1


# ─────────────────────────────────────────────
# Состояние после окончания
# ─────────────────────────────────────────────
class WhichReturn(IntEnum):
    STAGE_SELECT = 0   # вернуться к выбору стейджа
    NEW_UNIT     = 1   # показать новый юнит (первое прохождение)


# ─────────────────────────────────────────────
# Анимированный счётчик очков
# ─────────────────────────────────────────────
class ScoreCounter:
    """
    Анимированный подсчёт очков на экране завершения Campaign-стейджа.

    Фазы:
      SCORE_ADDING → нарастает score (~1000 единиц за кадр)
      BONUS_ADDING → нарастает bonus
      END          → отображает итоговый total

    Итоговый счёт:
      bonus = score * score_rate * 2
      total = score + bonus
    """

    PHASE_SCORE = 0
    PHASE_BONUS = 1
    PHASE_END   = 2

    def __init__(self, score: int, score_rate: float):
        self.score      = score
        self.bonus      = int(score * score_rate * 2)
        self.total      = score + self.bonus
        # Шаг нарастания: round(total/1000)*10 единиц за кадр
        self.interval   = max(1, round(self.total / 1000) * 10)
        self._tsc       = 0   # текущее отображаемое score
        self._tbn       = 0   # текущее отображаемое bonus
        self._phase     = self.PHASE_SCORE
        self.done       = False

    def update(self):
        """Обновить один кадр. После завершения done=True."""
        if self._phase == self.PHASE_SCORE:
            self._tsc += self.interval
            if self._tsc >= self.score:
                self._tsc   = self.score
                self._phase = self.PHASE_BONUS
        elif self._phase == self.PHASE_BONUS:
            self._tbn += self.interval
            if self._tbn >= self.bonus:
                self._tbn   = self.bonus
                self._phase = self.PHASE_END
        else:
            self.done = True

    @property
    def display_score(self) -> int:
        return self._tsc

    @property
    def display_bonus(self) -> int:
        return self._tbn

    @property
    def display_total(self) -> int:
        return self.total if self.done else 0


# ─────────────────────────────────────────────
# Главный класс завершения игры
# ─────────────────────────────────────────────
class GameEnd:
    """
    Управляет экраном завершения игры.

    Использование:
        # В GameMain — когда база уничтожена:
        GameEnd.instance.game_over()    # игрок проиграл
        GameEnd.instance.stage_clear()  # игрок победил

        # Каждый кадр пока visible:
        GameEnd.instance.update()
        GameEnd.instance.draw(surface)

        # Проверка нажатия кнопки возврата:
        if GameEnd.instance.return_pressed:
            if GameEnd.instance.which_return == WhichReturn.NEW_UNIT:
                # показать экран нового юнита
            else:
                # вернуться к выбору стейджа
    """

    _INIT      = 0
    _GAMEOVER  = 1
    _STAGECLEAR = 2

    instance: Optional["GameEnd"] = None

    def __init__(self, game_params, stage_record):
        """
        game_params   — объект с полями: score, score_rate, game_mode,
                        stage_num, cleared_stage_num, pause_flg, game_status
        stage_record  — объект с методом set_high_score(stage, total)
        """
        self.gp           = game_params
        self.sr           = stage_record
        self.visible      = False
        self._which_go    = self._INIT
        self.which_return = WhichReturn.STAGE_SELECT
        self.return_pressed = False

        # Счётчики очков
        self.score_counter: Optional[ScoreCounter] = None
        self.survival_score = 0

        # Анимация (кадры отображения заголовка до появления счёта)
        self._frm         = 0
        self.INTRO_FRAMES = 30   # кадров "Game Over" / "Stage Clear" до счёта

        GameEnd.instance = self

    # ── Публичные методы триггера ──────────────────────────────────────

    def game_over(self):
        """Вызывается когда база игрока уничтожена."""
        if self._which_go != self._INIT:
            return
        self.gp.game_status  = GST_GAME_OVER
        self.gp.pause_flg    = True
        self.which_return    = WhichReturn.STAGE_SELECT
        self.visible         = True
        self._which_go       = self._GAMEOVER
        self._frm            = 0
        # Survival: счёт сохраняется даже при game over
        if self.gp.game_mode == GAME_MODE_SURVIVAL:
            self._init_survival_score()

    def stage_clear(self):
        """Вызывается когда база врага уничтожена."""
        if self._which_go != self._INIT:
            return
        self.gp.game_status = GST_GAME_OVER
        self.gp.pause_flg   = True
        self.visible        = True
        self._which_go      = self._STAGECLEAR
        self._frm           = 0

        # Первое прохождение этого стейджа?
        if self.gp.stage_num <= self.gp.cleared_stage_num:
            self.which_return = WhichReturn.STAGE_SELECT
        else:
            self.which_return            = WhichReturn.NEW_UNIT
            self.gp.cleared_stage_num    = self.gp.stage_num

        if self.gp.game_mode == GAME_MODE_SURVIVAL:
            self._init_survival_score()
        else:
            self._init_campaign_score()

    def reset(self):
        """Сброс перед новым стейджем."""
        self.visible         = False
        self._which_go       = self._INIT
        self.return_pressed  = False
        self.score_counter   = None
        self.survival_score  = 0
        self._frm            = 0

    # ── Подсчёт очков ─────────────────────────────────────────────────

    def _init_campaign_score(self):
        sc = ScoreCounter(self.gp.score, self.gp.score_rate)
        self.score_counter = sc
        self.sr.set_high_score(self.gp.stage_num, sc.total)

    def _init_survival_score(self):
        self.survival_score = self.gp.score
        self.sr.set_high_score(self.gp.stage_num, self.survival_score)

    # ── Состояние экрана ──────────────────────────────────────────────

    @property
    def is_game_over(self) -> bool:
        return self._which_go == self._GAMEOVER

    @property
    def is_stage_clear(self) -> bool:
        return self._which_go == self._STAGECLEAR

    @property
    def is_survival(self) -> bool:
        return self.gp.game_mode == GAME_MODE_SURVIVAL

    # ── Обновление ────────────────────────────────────────────────────

    def update(self):
        if not self.visible:
            return
        self._frm += 1
        # Анимируем счётчик после вступления
        if self._frm > self.INTRO_FRAMES and self.score_counter:
            self.score_counter.update()

    def on_return_press(self):
        """Вызвать когда игрок нажал кнопку возврата (Enter/Space/клик)."""
        if not self.visible:
            return
        # Ускорить счётчик — если ещё не завершён, завершить мгновенно
        if self.score_counter and not self.score_counter.done:
            self.score_counter._tsc   = self.score_counter.score
            self.score_counter._tbn   = self.score_counter.bonus
            self.score_counter._phase = ScoreCounter.PHASE_END
            self.score_counter.done   = True
            return
        self.return_pressed = True

    # ── Отрисовка ─────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        W = surface.get_width()
        H = surface.get_height()

        # Затемнение фона
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        font_big   = pygame.font.SysFont("Arial", 48, bold=True)
        font_mid   = pygame.font.SysFont("Arial", 30)
        font_small = pygame.font.SysFont("Arial", 22)

        cy = H // 2

        # ── Заголовок ─────────────────────────────────────────────────
        if self.is_survival:
            title_text  = "GAME OVER"
            title_color = (255, 80, 80)
        elif self.is_game_over:
            title_text  = "GAME OVER"
            title_color = (255, 80, 80)
        else:
            title_text  = "STAGE CLEAR!"
            title_color = (255, 220, 50)

        title_surf = font_big.render(title_text, True, title_color)
        surface.blit(title_surf, (W // 2 - title_surf.get_width() // 2,
                                   cy - 120))

        # ── Счёт ──────────────────────────────────────────────────────
        if self._frm > self.INTRO_FRAMES:
            if self.is_survival:
                self._draw_survival_score(surface, font_mid, font_small, W, cy)
            elif self.score_counter:
                self._draw_campaign_score(surface, font_mid, font_small, W, cy)

        # ── Подсказка кнопки ──────────────────────────────────────────
        if self._frm > self.INTRO_FRAMES + 60:
            hint = "Press ENTER to continue"
            if self.score_counter and not self.score_counter.done:
                hint = "Press ENTER to skip"
            hint_surf = font_small.render(hint, True, (180, 180, 180))
            surface.blit(hint_surf,
                         (W // 2 - hint_surf.get_width() // 2, cy + 130))

    def _draw_campaign_score(self, surface, font_mid, font_small, W, cy):
        sc = self.score_counter
        rows = [
            ("Score:",  f"{sc.display_score:,}",  (255, 255, 255)),
            ("Bonus:",  f"{sc.display_bonus:,}",   (100, 220, 255)),
        ]
        if sc.done:
            rows.append(("Total:", f"{sc.display_total:,}", (255, 220, 50)))

        for i, (label, value, color) in enumerate(rows):
            y = cy - 40 + i * 44
            lbl_surf = font_small.render(label, True, (160, 160, 160))
            val_surf = font_mid.render(value, True, color)
            surface.blit(lbl_surf, (W // 2 - 160, y))
            surface.blit(val_surf, (W // 2 + 10, y))

    def _draw_survival_score(self, surface, font_mid, font_small, W, cy):
        lbl_surf = font_small.render("Score:", True, (160, 160, 160))
        val_surf = font_mid.render(f"{self.survival_score:,}", True,
                                   (255, 220, 50))
        surface.blit(lbl_surf, (W // 2 - 160, cy - 20))
        surface.blit(val_surf, (W // 2 + 10, cy - 20))


# ─────────────────────────────────────────────
# Интеграция с GameMain (псевдокод)
# ─────────────────────────────────────────────
"""
Как подключить в GameMain:

    from game_end import GameEnd, WhichReturn

    # При инициализации стейджа:
    self.game_end = GameEnd(self.game_params, self.stage_record)

    # В enter_frame, каждый кадр:
    self.game_end.update()

    # Проверка условий окончания:
    if player_fortress.life <= 0:
        self.game_end.game_over()
    elif enemy_fortress.life <= 0:
        self.game_end.stage_clear()

    # Обработка ввода (в handle_events):
    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
        self.game_end.on_return_press()

    if self.game_end.return_pressed:
        if self.game_end.which_return == WhichReturn.NEW_UNIT:
            self.show_next_available_unit()
        else:
            self.goto_stage_select()

    # В draw():
    self.game_end.draw(surface)
"""
