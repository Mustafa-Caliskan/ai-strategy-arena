"""
scoreboard.py — AI istatistik paneli
Her ülkenin kaynaklarını ve skoru gösterir.
"""
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.country import Country
    from game.diplomacy import DiplomacySystem

COLOR_BG        = (20,  20,  35)
COLOR_PANEL     = (30,  30,  50)
COLOR_HEADER    = (60,  60,  90)
COLOR_TEXT      = (220, 220, 230)
COLOR_MUTED     = (140, 140, 160)
COLOR_GOLD      = (255, 200,  50)
COLOR_FOOD      = (100, 200, 100)
COLOR_ARMY      = (200,  80,  80)
COLOR_TERRITORY = (80,  160, 220)
COLOR_TECH      = (180, 100, 220)
COLOR_SCORE     = (255, 220, 100)
COLOR_WIN       = (255, 215,   0)
COLOR_ELIM      = (120,  40,  40)


class Scoreboard:
    """Yan panel: her ülkenin kaynakları, skoru ve diplomatik durumu."""

    PADDING = 10
    ROW_H   = 22

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
        """Scoreboard'u verilen rect alanına çiz."""
        pygame.draw.rect(surface, COLOR_PANEL, rect)
        pygame.draw.rect(surface, COLOR_HEADER, rect, 1)

        x = rect.x + self.PADDING
        y = rect.y + self.PADDING

        # Başlık
        title = self.font_l.render("AI STRATEGY ARENA", True, COLOR_TEXT)
        surface.blit(title, (x, y))
        y += title.get_height() + 4

        # Tur bilgisi
        turn_color = COLOR_WIN if winner else COLOR_MUTED
        turn_text = f"Turn: {turn} / {max_turns}"
        t = self.font_m.render(turn_text, True, turn_color)
        surface.blit(t, (x, y))
        y += t.get_height() + 12

        if winner:
            w_text = f"WINNER: {winner}" if winner != "draw" else "DRAW"
            wt = self.font_m.render(w_text, True, COLOR_WIN)
            surface.blit(wt, (x, y))
            y += wt.get_height() + 8

        # Her ülke için panel
        panel_w = rect.width - self.PADDING * 2
        for country in countries:
            y = self._draw_country_panel(surface, country, x, y, panel_w)
            y += 12

        # Diplomatik ilişkiler
        y = self._draw_diplomacy(surface, countries, diplomacy, x, y, panel_w)

    def _draw_country_panel(self, surface, country, x, y, width) -> int:
        r = country.resources
        is_elim = not country.is_active()

        # Başlık arka planı
        header_rect = pygame.Rect(x, y, width, self.ROW_H + 2)
        hcol = COLOR_ELIM if is_elim else country.color
        pygame.draw.rect(surface, hcol, header_rect, border_radius=4)

        name_text = f"{'[ELIMINATED] ' if is_elim else ''}{country.name} ({country.agent_id})"
        nt = self.font_m.render(name_text, True, (255, 255, 255))
        surface.blit(nt, (x + 6, y + 4))
        y += self.ROW_H + 6

        if is_elim:
            return y

        COLOR_WOOD      = (190, 140,  90)
        COLOR_STONE     = (180, 180, 190)
        COLOR_IRON      = (140, 190, 230)
        COLOR_INFL      = (220, 140, 240)

        # Kaynak satırları (Catan + Endless Legend çoklu kaynak)
        rows = [
            (f"Gold: {r.gold:.0f}  | Food: {r.food:.0f}",       COLOR_GOLD),
            (f"Wood: {r.wood:.0f} | Stone: {r.stone:.0f}",     COLOR_WOOD),
            (f"Iron: {r.iron:.0f} | Infl: {r.influence:.0f}",  COLOR_IRON),
            (f"Pop: {r.population} | Army: {r.army}",           COLOR_TEXT),
            (f"Territory: {r.territory} | Tech: Lv{r.technology}", COLOR_TERRITORY),
            (f"Score: {country.calculate_score():.0f}",         COLOR_SCORE),
        ]
        for text, color in rows:
            t = self.font_s.render(text, True, color)
            surface.blit(t, (x + 8, y))
            y += self.ROW_H - 4

        return y + 4

    def _draw_diplomacy(self, surface, countries, diplomacy, x, y, width) -> int:
        if len(countries) < 2:
            return y

        header = self.font_m.render("Diplomacy", True, COLOR_MUTED)
        surface.blit(header, (x, y))
        y += header.get_height() + 4

        for i, ca in enumerate(countries):
            for cb in countries[i+1:]:
                rel = diplomacy.get_relation(ca.agent_id, cb.agent_id)
                status = rel.status.value.upper()
                score  = rel.score

                status_colors = {
                    "WAR":      (220,  60,  60),
                    "PEACE":    (100, 200, 100),
                    "TRADE":    (255, 200,  50),
                    "ALLIANCE": (100, 150, 255),
                    "NEUTRAL":  (160, 160, 180),
                }
                col = status_colors.get(status, COLOR_TEXT)

                line = f"{ca.agent_id} vs {cb.agent_id}: {status} ({score:+.0f})"
                t = self.font_s.render(line, True, col)
                surface.blit(t, (x + 4, y))
                y += self.ROW_H - 4

        # Aktif Paktlar
        if hasattr(diplomacy, "contracts"):
            active_pacts = [c for c in diplomacy.contracts.contracts.values() if c.is_active()]
            if active_pacts:
                y += 4
                pact_header = self.font_m.render("Active Pacts", True, (215, 140, 255))
                surface.blit(pact_header, (x, y))
                y += pact_header.get_height() + 2
                for p in active_pacts:
                    pline = f"📜 {p.initiator}<->{p.target}: {p.turns_remaining} turns left"
                    pt = self.font_s.render(pline, True, (230, 180, 255))
                    surface.blit(pt, (x + 4, y))
                    y += self.ROW_H - 6

        return y
