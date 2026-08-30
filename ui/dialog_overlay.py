"""
dialog_overlay.py — Kraliyet Strateji ve Diplomasi Diyalog Penceresi

Yapay zekanın (OpenAI & DeepSeek) o turdaki:
- Stratejik düşüncesini (Thought)
- Verdiği emirleri (Recruit, Move, Attack)
- Gönderdiği diplomatik mektubu (Envoy Letter)
- Kraliyet portresini
ekranda şık bir Orta Çağ diyalog kartı olarak gösterir.
"""
from __future__ import annotations

import pygame
from typing import Optional


class DialogOverlay:
    def __init__(self):
        self.font_title = pygame.font.SysFont("georgia", 18, bold=True)
        self.font_body = pygame.font.SysFont("consolas", 14)
        self.font_italic = pygame.font.SysFont("georgia", 14, italic=True)
        self.font_tip = pygame.font.SysFont("consolas", 11, bold=True)

        self.current_speaker: Optional[str] = None
        self.current_thought: Optional[str] = None
        self.current_orders: Optional[str] = None
        self.current_letter: Optional[str] = None
        self.turn: int = 1
        self.visible: bool = False
        self.auto_advance_timer: float = 0.0

    def show_turn_decision(
        self,
        speaker: str,
        thought: str,
        orders: str = "",
        letter: Optional[str] = None,
        turn: int = 1,
    ):
        self.current_speaker = speaker
        self.current_thought = thought
        self.current_orders = orders
        self.current_letter = letter
        self.turn = turn
        self.visible = True
        self.auto_advance_timer = 4.0  # 4 saniye sonra otomatik geçebilir

    def hide(self):
        self.visible = False

    def update(self, dt: float):
        if self.visible and self.auto_advance_timer > 0:
            self.auto_advance_timer -= dt

    def draw(self, screen: pygame.Surface, screen_w: int, screen_h: int):
        if not self.visible or not self.current_thought:
            return

        is_openai = ("openai" in self.current_speaker.lower() or "ai_a" in self.current_speaker.lower() or "alpha" in self.current_speaker.lower())
        theme_color = (65, 140, 245) if is_openai else (240, 75, 75)
        bg_card = (20, 24, 34)
        border_card = theme_color

        # Kart boyutları
        card_w = min(880, screen_w - 60)
        card_h = 160 if not self.current_letter else 200
        card_x = (screen_w - card_w) // 2
        card_y = screen_h - card_h - 70

        # 1. Drop Shadow
        pygame.draw.rect(screen, (8, 10, 15), (card_x + 5, card_y + 5, card_w, card_h), border_radius=10)
        # 2. Ana Kart Gövdesi
        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)
        pygame.draw.rect(screen, bg_card, card_rect, border_radius=10)
        pygame.draw.rect(screen, border_card, card_rect, 2, border_radius=10)

        # 3. Başlık & Rozet
        speaker_title = f"👑 {self.current_speaker} — Kraliyet Divanı (Tur {self.turn})"
        title_surf = self.font_title.render(speaker_title, True, theme_color)
        screen.blit(title_surf, (card_x + 20, card_y + 12))

        # Metin Sarmalayıcı (Word Wrap)
        def render_wrapped(text: str, font, color, max_w):
            words = text.split(' ')
            lines = []
            cur_line = []
            for w in words:
                test_line = ' '.join(cur_line + [w])
                if font.size(test_line)[0] < max_w:
                    cur_line.append(w)
                else:
                    if cur_line:
                        lines.append(' '.join(cur_line))
                    cur_line = [w]
            if cur_line:
                lines.append(' '.join(cur_line))
            return [font.render(l, True, color) for l in lines]

        max_text_w = card_w - 40
        curr_y = card_y + 40

        # 4. Stratejik Düşünce (Thought)
        thought_txt = f"🧠 Strateji: \"{self.current_thought}\""
        for surf in render_wrapped(thought_txt, self.font_body, (240, 245, 255), max_text_w)[:2]:
            screen.blit(surf, (card_x + 20, curr_y))
            curr_y += 20

        # 5. Askeri Emirler (Orders)
        if self.current_orders:
            orders_txt = f"⚔️ Emirler: {self.current_orders}"
            orders_surf = self.font_body.render(orders_txt, True, (255, 215, 80))
            screen.blit(orders_surf, (card_x + 20, curr_y + 2))
            curr_y += 22

        # 6. Diplomatik Elçi Mektubu (Letter)
        if self.current_letter:
            letter_txt = f"📜 Mektup: \"{self.current_letter}\""
            for surf in render_wrapped(letter_txt, self.font_italic, (130, 230, 255), max_text_w)[:2]:
                screen.blit(surf, (card_x + 20, curr_y + 2))
                curr_y += 18

        # 7. Alt Bilgi / Space İpucu
        tip_txt = "[ SPACE: Sonraki Tura Geç ]  •  [ Fare ile Haritayı Kaydır & Birlikleri İncele ]"
        tip_surf = self.font_tip.render(tip_txt, True, (160, 175, 195))
        screen.blit(tip_surf, (card_x + card_w - tip_surf.get_width() - 20, card_y + card_h - 22))