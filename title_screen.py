"""title_screen.py — port of the main menu from Navy Battle Flash.

Sources: TitlePlayBtn.as, TitleDemoBtn.as, TitleCredistBtn.as,
SaveClearBtn.as, SaveConfirm.as,
TitleSaveClearConfirmYesBtn.as, TitleSaveClearConfirmNoBtn.as
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from game_constants import GameConstants, GameParams, SaveLoad


MODE_DESCRIPTIONS = {
    GameConstants.GAME_MODE_CMPN_EASY: (
        "Easy",
        "This mode is a low difficulty with less number of enemies.",
    ),
    GameConstants.GAME_MODE_CMPN_NORMAL: (
        "Normal",
        "This mode is a normal difficulty.",
    ),
    GameConstants.GAME_MODE_CMPN_HARD: (
        "Hard",
        "This mode is a high difficulty with more number of enemies.",
    ),
    GameConstants.GAME_MODE_SURVIVAL: (
        "Survival",
        "Survival as long as possible.",
    ),
    GameConstants.GAME_MODE_CLIMAX: (
        "Climax",
        "Game starts from the flagship appearance and player's base is upgraded.",
    ),
}


class TitleScreen:
    """Pygame implementation of the title screen menu."""

    BTN_X = 80
    BTN_Y_START = 180
    BTN_W = 220
    BTN_H = 46
    BTN_GAP = 12

    BTN_DEMO_X = 80
    BTN_BOTTOM_Y = 470

    C_BG = (10, 18, 35)
    C_TITLE = (255, 255, 255)
    C_SUBTITLE = (130, 170, 220)
    C_BTN = {
        GameConstants.GAME_MODE_CMPN_EASY: (30, 90, 50),
        GameConstants.GAME_MODE_CMPN_NORMAL: (30, 60, 110),
        GameConstants.GAME_MODE_CMPN_HARD: (100, 30, 30),
        GameConstants.GAME_MODE_SURVIVAL: (80, 50, 10),
        GameConstants.GAME_MODE_CLIMAX: (70, 20, 90),
    }
    C_BTN_HOVER = {
        GameConstants.GAME_MODE_CMPN_EASY: (50, 140, 80),
        GameConstants.GAME_MODE_CMPN_NORMAL: (50, 100, 180),
        GameConstants.GAME_MODE_CMPN_HARD: (170, 50, 50),
        GameConstants.GAME_MODE_SURVIVAL: (140, 90, 20),
        GameConstants.GAME_MODE_CLIMAX: (120, 35, 160),
    }
    C_BTN_MISC = (35, 45, 65)
    C_BTN_MISC_H = (60, 80, 120)
    C_BTN_DANGER = (80, 20, 20)
    C_BTN_DANGER_H = (140, 35, 35)
    C_BTN_BORDER = (80, 100, 140)
    C_TEXT = (220, 220, 220)
    C_DESC = (170, 200, 240)
    C_VERSION = (60, 60, 80)

    _CONFIRM_HIDDEN = 0
    _CONFIRM_VISIBLE = 1

    def __init__(
        self,
        on_play: Callable[[int], None],
        on_demo: Callable[[], None],
        on_credits: Callable[[], None],
    ):
        self.on_play = on_play
        self.on_demo = on_demo
        self.on_credits = on_credits

        self._hover_mode: Optional[int] = None
        self._hover_demo = False
        self._hover_credits = False
        self._hover_clear = False
        self._hover_yes = False
        self._hover_no = False

        self._confirm_state = self._CONFIRM_HIDDEN
        self._desc_text = ""

        self._fonts_ready = False
        self._f_title = self._f_big = self._f_mid = self._f_sm = None

        self._mode_rects: dict[int, pygame.Rect] = {}
        y = self.BTN_Y_START
        for mode in [
            GameConstants.GAME_MODE_CMPN_EASY,
            GameConstants.GAME_MODE_CMPN_NORMAL,
            GameConstants.GAME_MODE_CMPN_HARD,
            GameConstants.GAME_MODE_SURVIVAL,
            GameConstants.GAME_MODE_CLIMAX,
        ]:
            self._mode_rects[mode] = pygame.Rect(self.BTN_X, y, self.BTN_W, self.BTN_H)
            y += self.BTN_H + self.BTN_GAP

        self._demo_rect = pygame.Rect(self.BTN_DEMO_X, self.BTN_BOTTOM_Y, 120, 34)
        self._credits_rect = pygame.Rect(self.BTN_DEMO_X + 136, self.BTN_BOTTOM_Y, 120, 34)
        self._clear_rect = pygame.Rect(self.BTN_DEMO_X + 272, self.BTN_BOTTOM_Y, 140, 34)

        sw, sh = GameConstants.STAGE_WIDTH, GameConstants.STAGE_HEIGHT
        dw, dh = 360, 160
        self._confirm_rect = pygame.Rect((sw - dw) // 2, (sh - dh) // 2, dw, dh)
        self._yes_rect = pygame.Rect(self._confirm_rect.x + 50, self._confirm_rect.y + 100, 110, 38)
        self._no_rect = pygame.Rect(self._confirm_rect.x + 200, self._confirm_rect.y + 100, 110, 38)

    def _init_fonts(self) -> None:
        if self._fonts_ready:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        self._f_title = pygame.font.SysFont("Arial", 46, bold=True)
        self._f_big = pygame.font.SysFont("Arial", 22, bold=True)
        self._f_mid = pygame.font.SysFont("Arial", 18)
        self._f_sm = pygame.font.SysFont("Arial", 15)
        self._fonts_ready = True

    def handle_event(self, event: pygame.event.Event) -> None:
        self._init_fonts()
        mx, my = pygame.mouse.get_pos()

        if self._confirm_state == self._CONFIRM_VISIBLE:
            self._handle_confirm_event(event, mx, my)
            return

        if event.type == pygame.MOUSEMOTION:
            self._hover_mode = None
            self._hover_demo = False
            self._hover_credits = False
            self._hover_clear = False
            self._desc_text = ""
            for mode, rect in self._mode_rects.items():
                if rect.collidepoint(mx, my):
                    self._hover_mode = mode
                    self._desc_text = MODE_DESCRIPTIONS[mode][1]
                    break
            self._hover_demo = self._demo_rect.collidepoint(mx, my)
            self._hover_credits = self._credits_rect.collidepoint(mx, my)
            self._hover_clear = self._clear_rect.collidepoint(mx, my)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._hover_mode is not None:
                GameParams.game_mode = self._hover_mode
                self.on_play(self._hover_mode)
            elif self._hover_demo:
                self.on_demo()
            elif self._hover_credits:
                self.on_credits()
            elif self._hover_clear:
                self._confirm_state = self._CONFIRM_VISIBLE

    def _handle_confirm_event(self, event: pygame.event.Event, mx: int, my: int) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hover_yes = self._yes_rect.collidepoint(mx, my)
            self._hover_no = self._no_rect.collidepoint(mx, my)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._hover_yes:
                SaveLoad.reset_all()
                self._confirm_state = self._CONFIRM_HIDDEN
                self._hover_yes = self._hover_no = False
            elif self._hover_no or not self._confirm_rect.collidepoint(mx, my):
                self._confirm_state = self._CONFIRM_HIDDEN
                self._hover_yes = self._hover_no = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._confirm_state = self._CONFIRM_HIDDEN

    def draw(self, surface: pygame.Surface) -> None:
        self._init_fonts()
        surface.fill(self.C_BG)

        title = self._f_title.render("NAVY BATTLE", True, self.C_TITLE)
        surface.blit(title, (self.BTN_X, 60))
        sub = self._f_sm.render("Naval Strategy Game", True, self.C_SUBTITLE)
        surface.blit(sub, (self.BTN_X, 118))

        for mode, rect in self._mode_rects.items():
            hovered = self._hover_mode == mode
            c_bg = self.C_BTN_HOVER.get(mode, self.C_BTN_MISC_H) if hovered else self.C_BTN.get(mode, self.C_BTN_MISC)
            pygame.draw.rect(surface, c_bg, rect, border_radius=6)
            pygame.draw.rect(surface, self.C_BTN_BORDER, rect, 1, border_radius=6)
            name = MODE_DESCRIPTIONS[mode][0]
            lbl = self._f_big.render(name, True, self.C_TEXT)
            surface.blit(lbl, (rect.x + 14, rect.y + (rect.h - lbl.get_height()) // 2))

        if self._desc_text:
            words = self._desc_text.split()
            lines = []
            line = ""
            for word in words:
                test = (line + " " + word).strip()
                if self._f_sm.size(test)[0] < 340:
                    line = test
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            desc_x = self.BTN_X + self.BTN_W + 30
            desc_y = self.BTN_Y_START
            for idx, ln in enumerate(lines):
                txt = self._f_sm.render(ln, True, self.C_DESC)
                surface.blit(txt, (desc_x, desc_y + idx * 22))

        self._draw_misc_btn(surface, self._demo_rect, "Demo", self._hover_demo)
        self._draw_misc_btn(surface, self._credits_rect, "Credits", self._hover_credits)
        self._draw_danger_btn(surface, self._clear_rect, "Save Clear", self._hover_clear)

        ver = self._f_sm.render("Navy Battle — Python Port", True, self.C_VERSION)
        surface.blit(ver, (surface.get_width() - ver.get_width() - 10, surface.get_height() - 22))

        if self._confirm_state == self._CONFIRM_VISIBLE:
            self._draw_confirm(surface)

    def _draw_misc_btn(self, surface: pygame.Surface, rect: pygame.Rect, label: str, hovered: bool) -> None:
        color = self.C_BTN_MISC_H if hovered else self.C_BTN_MISC
        pygame.draw.rect(surface, color, rect, border_radius=5)
        pygame.draw.rect(surface, self.C_BTN_BORDER, rect, 1, border_radius=5)
        lbl = self._f_sm.render(label, True, self.C_TEXT)
        surface.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2, rect.y + (rect.h - lbl.get_height()) // 2))

    def _draw_danger_btn(self, surface: pygame.Surface, rect: pygame.Rect, label: str, hovered: bool) -> None:
        color = self.C_BTN_DANGER_H if hovered else self.C_BTN_DANGER
        pygame.draw.rect(surface, color, rect, border_radius=5)
        pygame.draw.rect(surface, (160, 60, 60), rect, 1, border_radius=5)
        lbl = self._f_sm.render(label, True, (255, 180, 180))
        surface.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2, rect.y + (rect.h - lbl.get_height()) // 2))

    def _draw_confirm(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        rect = self._confirm_rect
        pygame.draw.rect(surface, (20, 30, 50), rect, border_radius=8)
        pygame.draw.rect(surface, (120, 60, 60), rect, 2, border_radius=8)

        t1 = self._f_mid.render("Clear all save data?", True, (255, 220, 220))
        t2 = self._f_sm.render("This cannot be undone.", True, (180, 120, 120))
        surface.blit(t1, (rect.x + (rect.w - t1.get_width()) // 2, rect.y + 22))
        surface.blit(t2, (rect.x + (rect.w - t2.get_width()) // 2, rect.y + 52))

        yes_color = self.C_BTN_DANGER_H if self._hover_yes else self.C_BTN_DANGER
        no_color = self.C_BTN_MISC_H if self._hover_no else self.C_BTN_MISC
        pygame.draw.rect(surface, yes_color, self._yes_rect, border_radius=5)
        pygame.draw.rect(surface, no_color, self._no_rect, border_radius=5)
        pygame.draw.rect(surface, (160, 60, 60), self._yes_rect, 1, border_radius=5)
        pygame.draw.rect(surface, self.C_BTN_BORDER, self._no_rect, 1, border_radius=5)

        yes_lbl = self._f_mid.render("YES", True, (255, 180, 180))
        no_lbl = self._f_mid.render("NO", True, self.C_TEXT)
        surface.blit(yes_lbl, (self._yes_rect.x + (self._yes_rect.w - yes_lbl.get_width()) // 2, self._yes_rect.y + 8))
        surface.blit(no_lbl, (self._no_rect.x + (self._no_rect.w - no_lbl.get_width()) // 2, self._no_rect.y + 8))
