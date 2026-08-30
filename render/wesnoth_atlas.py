"""
wesnoth_atlas.py — Battle for Wesnoth Orijinal Yüksek Çözünürlüklü Sprite Atlası

Wesnoth'un resmi data/core/images/ klasöründeki 72x72 piksel gerçek şövalye,
okçu, atlı elçi, kale, köy, dağ ve nehir grafiklerini yükler ve önbelleğe alır.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import pygame

from game.entities import UnitClass

# Wesnoth Core Images Klasörü
WESNOTH_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "wesnoth" / "data" / "core" / "images"


class WesnothAtlas:
    _instance: Optional[WesnothAtlas] = None

    def __init__(self):
        self.sprites: dict[str, pygame.Surface] = {}
        self.base_dir = WESNOTH_IMAGES_DIR
        self._load_all_sprites()

    @classmethod
    def get(cls) -> WesnothAtlas:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_image(self, rel_path: str, fallback_color=(200, 200, 200), size=(72, 72)) -> pygame.Surface:
        full_path = self.base_dir / rel_path
        if full_path.exists():
            try:
                surf = pygame.image.load(str(full_path)).convert_alpha()
                return surf
            except Exception:
                pass

        # Fallback yüzey
        fallback = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(fallback, fallback_color, (size[0] // 2, size[1] // 2), size[0] // 3)
        return fallback

    def _load_all_sprites(self):
        # 1. Human / OpenAI Birlikleri
        self.sprites["human_infantry"] = self._load_image("units/human-loyalists/swordsman.png", (60, 120, 240))
        self.sprites["human_spearman"] = self._load_image("units/human-loyalists/spearman.png", (60, 120, 240))
        self.sprites["human_archer"] = self._load_image("units/human-loyalists/bowman.png", (60, 120, 240))
        self.sprites["human_cavalry"] = self._load_image("units/human-loyalists/horseman/horseman.png", (60, 120, 240))
        self.sprites["human_mage"] = self._load_image("units/human-magi/mage.png", (60, 120, 240))
        self.sprites["human_general"] = self._load_image("units/human-loyalists/general.png", (60, 120, 240))

        # 2. Elf / DeepSeek Birlikleri
        self.sprites["elf_infantry"] = self._load_image("units/elves-wood/captain.png", (220, 60, 60))
        self.sprites["elf_archer"] = self._load_image("units/elves-wood/archer.png", (220, 60, 60))
        self.sprites["elf_cavalry"] = self._load_image("units/human-loyalists/horseman/horseman.png", (220, 60, 60))
        self.sprites["elf_mage"] = self._load_image("units/human-magi/white-mage.png", (220, 60, 60))
        self.sprites["elf_general"] = self._load_image("units/elves-wood/captain.png", (220, 60, 60))

        # 3. Kara Sancaklı Haydutlar (Bandits / Raiders)
        self.sprites["bandit_infantry"] = self._load_image("units/orcs/grunt.png", (30, 30, 30))
        self.sprites["bandit_archer"] = self._load_image("units/orcs/archer.png", (30, 30, 30))
        self.sprites["bandit_cavalry"] = self._load_image("units/orcs/warrior.png", (30, 30, 30))
        self.sprites["bandit_mage"] = self._load_image("units/undead-necromancers/dark-adept.png", (30, 30, 30))
        self.sprites["bandit_general"] = self._load_image("units/orcs/leader.png", (30, 30, 30))

        # 4. Elçiler (Envoy)
        self.sprites["envoy_human"] = self._load_image("units/human-loyalists/horseman/horseman.png", (100, 200, 255))
        self.sprites["envoy_elf"] = self._load_image("units/human-loyalists/horseman/horseman.png", (255, 120, 120))

        # 5. Arazi & Yapılar (Terrain & Structures)
        self.sprites["castle"] = self._load_image("terrain/castle/encampment/regular-tile.png", (180, 160, 130))
        self.sprites["village"] = self._load_image("terrain/village/human-tile.png", (220, 190, 120))
        self.sprites["mountain"] = self._load_image("terrain/mountains/basic-tile.png", (140, 140, 150))
        self.sprites["ruins"] = self._load_image("scenery/castle-ruins.png", (160, 150, 140))

    def get_unit_sprite(self, owner: str, unit_class: UnitClass, is_leader: bool = False) -> pygame.Surface:
        if owner == "BANDITS":
            prefix = "bandit"
        elif owner == "AI_A" or "openai" in owner.lower() or "alpha" in owner.lower():
            prefix = "human"
        else:
            prefix = "elf"

        if is_leader:
            return self.sprites.get(f"{prefix}_general", self.sprites[f"{prefix}_infantry"])

        if unit_class == UnitClass.INFANTRY:
            return self.sprites.get(f"{prefix}_infantry")
        elif unit_class == UnitClass.ARCHER:
            return self.sprites.get(f"{prefix}_archer")
        elif unit_class == UnitClass.CAVALRY:
            return self.sprites.get(f"{prefix}_cavalry")
        elif unit_class == UnitClass.CATAPULT:
            return self.sprites.get(f"{prefix}_mage")
        return self.sprites.get(f"{prefix}_infantry")

    def get_envoy_sprite(self, owner: str) -> pygame.Surface:
        is_openai = (owner == "AI_A" or "openai" in owner.lower() or "alpha" in owner.lower())
        return self.sprites.get("envoy_human" if is_openai else "envoy_elf")

    def get_terrain_sprite(self, name: str) -> pygame.Surface:
        return self.sprites.get(name, self.sprites["village"])