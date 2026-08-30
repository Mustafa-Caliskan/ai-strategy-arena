"""
scoreboard.py — AI Strateji Arenası İstatistik ve Skor Paneli (Grand Strategy Theme)

Modern kart/panel tasarımı, renkli kaynak ikonları, diplomatik ilişki rozetleri
ve dinamik liderlik sıralaması sunar.
"""
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.country import Country
    from game.diplomacy import DiplomacySystem

# Modern Koyu Arayüz Renk Paleti
COLOR_BG        = (18,  20,  28)
COLOR_PANEL     = (24,  27,  38)
COLOR_CARD      = (32,  36,  50)
COLOR_CARD_ALT  = (28,  32,  44)
COLOR_BORDER    = (48,  54,  76)
COLOR_HEADER    = (70,  80, 110)
COLOR_TEXT      = (235, 238, 245)
COLOR_MUTED     = (145, 155, 175)
COLOR_GOLD      = (255, 205,  55)
COLOR_FOOD      = (110, 210, 110)
COLOR_WOOD      = (185, 140,  95)
COLOR_STONE     = (160, 170, 185)
COLOR_IRON      = (195, 200, 215)
COLOR_INFL      = (220, 150, 245)
COLOR_ARMY      = (235,  85,  85)
COLOR_LAND      = (100, 175, 235)
COLOR_TECH      = (175, 125, 235)
COLOR_SCORE     = (255, 220, 100)
COLOR_WIN       = (255, 215,   0)
COLOR_ELIM      = (110,  35,  35)


class Scoreboard:
    """Modern grand strategy yan paneli: Kaynak kartları, diplomatik durum ve zafer takibi."""

    PADDING = 12
    ROW_H   = 20

    def __init__(self, font_small, font_medium, font_large):
        self.font_s = font_small
        self.font_m = font_medium
        self.font_l = font_large

    def draw(
        self,
        surface: pygame.Surface,
        countries: list["Country"],
        diplomacy: "DiplomacySystem",
        turn: int,
        max_turns: int,
        winner: str | None,
        rect: pygame.Rect,
    ) -> None:
        """Scoreboard'u modern kart düzeninde çiz."""
        # Ana panel arka planı
        pygame.draw.rect(surface, COLOR_PANEL, rect)
        pygame.draw.rect(surface, COLOR_BORDER, rect, 1)

        x = rect.x + self.PADDING
        y = rect.y + self.PADDING
        panel_w = rect.width - self.PADDING * 2

        # 1. Başlık Kartı
        header_rect = pygame.Rect(x, y, panel_w, 54)
        pygame.draw.rect(surface, COLOR_CARD, header_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, header_rect, 1, border_radius=6)

        title = self.font_l.render("AI STRATEGY ARENA", True, (255, 240, 180))
        surface.blit(title, (x + 10, y + 6))

        # Tur ve zafer durumu
        turn_color = COLOR_WIN if winner else COLOR_MUTED
        turn_text = f"Turn: {turn} / {max_turns}"
        t = self.font_s.render(turn_text, True, turn_color)
        surface.blit(t, (x + 10, y + 30))

        if winner:
            w_text = f"WINNER: {winner}" if winner != "draw" else "DRAW"
            wt = self.font_s.render(w_text, True, COLOR_WIN)
            surface.blit(wt, (x + panel_w - wt.get_width() - 10, y + 30))

        y += 62

        # 2. Ülke Kartları (Her ülke için modern strateji kartı)
        for country in countries:
            y = self._draw_country_card(surface, country, x, y, panel_w)
            y += 10

        # 3. Diplomatik İlişkiler Kartı
        y = self._draw_diplomacy_card(surface, countries, diplomacy, x, y, panel_w)

    def _draw_country_card(self, surface: pygame.Surface, country: "Country", x: int, y: int, width: int) -> int:
        r = country.resources
        is_elim = not country.is_active()

        card_h = 104 if not is_elim else 26
        card_rect = pygame.Rect(x, y, width, card_h)
        pygame.draw.rect(surface, COLOR_CARD, card_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, card_rect, 1, border_radius=6)

        # Ülke başlık şeridi (Faction rengi aksan çizgisi)
        accent_color = COLOR_ELIM if is_elim else country.color
        pygame.draw.rect(surface, accent_color, (x, y, width, 20), border_top_left_radius=6, border_top_right_radius=6)

        name_text = f"{'[ELIMINATED] ' if is_elim else ''}{country.name} ({country.agent_id})"
        nt = self.font_m.render(name_text, True, (255, 255, 255))
        surface.blit(nt, (x + 8, y + 2))

        if is_elim:
            return y + card_h

        # Skor ve Başkent bilgisi
        sy = y + 24
        score_val = country.calculate_score()
        score_txt = self.font_s.render(f"Score: {score_val:.0f}", True, COLOR_SCORE)
        cap_txt = self.font_s.render(f"Capital: ({country.capital_x},{country.capital_y})", True, COLOR_MUTED)
        surface.blit(score_txt, (x + 8, sy))
        surface.blit(cap_txt, (x + width - cap_txt.get_width() - 8, sy))

        # 2 Sütunlu Kaynaklar Izgarası
        col1_x = x + 8
        col2_x = x + width // 2 + 4
        ry = sy + 16

        res_col1 = [
            (f"Gold: {r.gold:.0f}", COLOR_GOLD),
            (f"Food: {r.food:.0f}", COLOR_FOOD),
            (f"Wood: {r.wood:.0f}", COLOR_WOOD),
        ]
        res_col2 = [
            (f"Army: {r.army:.0f}", COLOR_ARMY),
            (f"Iron: {r.iron:.0f}", COLOR_IRON),
            (f"Land: {r.territory}", COLOR_LAND),
        ]

        for text, col in res_col1:
            lbl = self.font_s.render(text, True, col)
            surface.blit(lbl, (col1_x, ry))
            ry += 14

        ry2 = sy + 16
        for text, col in res_col2:
            lbl = self.font_s.render(text, True, col)
            surface.blit(lbl, (col2_x, ry2))
            ry2 += 14

        return y + card_h

    def _draw_diplomacy_card(
        self,
        surface: pygame.Surface,
        countries: list["Country"],
        diplomacy: "DiplomacySystem",
        x: int,
        y: int,
        width: int,
    ) -> int:
        """Diplomatik anlaşmalar ve ilişkiler kartı."""
        card_rect = pygame.Rect(x, y, width, 120)
        pygame.draw.rect(surface, COLOR_CARD, card_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BORDER, card_rect, 1, border_radius=6)

        # Başlık
        lbl = self.font_m.render("DIPLOMATIC RELATIONS", True, (200, 210, 235))
        surface.blit(lbl, (x + 8, y + 6))

        curr_y = y + 28
        if len(countries) >= 2:
            a, b = countries[0].agent_id, countries[1].agent_id
            rel = diplomacy.get_relation(a, b)
            status = rel.status.value.upper()
            rel_val = rel.score

            st_color = (100, 220, 120) if "PEACE" in status or "ALLIANCE" in status else ((240, 80, 80) if "WAR" in status else (220, 220, 100))

            t1 = self.font_s.render(f"Status: {status}", True, st_color)
            t2 = self.font_s.render(f"Relation Score: {rel_val:+.0f}", True, COLOR_MUTED)
            surface.blit(t1, (x + 8, curr_y))
            surface.blit(t2, (x + 8, curr_y + 16))
            curr_y += 36

            # Aktif Anlaşmalar (Contracts)
            contracts = diplomacy.contracts.get_active_contracts_for(a)
            contracts_ab = [c for c in contracts if (c.initiator == b or c.target == b)]
            if contracts_ab:
                ct_lbl = self.font_s.render(f"Active Deals ({len(contracts_ab)}):", True, (255, 215, 100))
                surface.blit(ct_lbl, (x + 8, curr_y))
                curr_y += 15
                for c in contracts_ab[:2]:
                    d_txt = self.font_s.render(f"• {c.contract_type.value.upper()} (Left: {c.turns_remaining}T)", True, (180, 220, 255))
                    surface.blit(d_txt, (x + 16, curr_y))
                    curr_y += 14
            else:
                none_txt = self.font_s.render("No formal treaties active.", True, (120, 125, 140))
                surface.blit(none_txt, (x + 8, curr_y))

        return curr_y