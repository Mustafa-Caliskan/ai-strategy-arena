"""
entities.py — Fiziksel Varlık ve Taktiksel Savaş Sistemi (ArmyEntity, EnvoyEntity ve EntityManager)

Haritada koordinatı, hedefi, yolu ve hareket durumu olan dinamik nesneler.
4 Farklı Asker Sınıfı (Piyade, Okçu, Süvari, Mancınık), Can Barları (HP),
Menzil, Zırh ve Özel Taktik Yetenekleri (Shield Wall, Fire Arrow, Charge, Siege) içerir.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional, Any
from collections import defaultdict

from game.pathfinding import find_path

if TYPE_CHECKING:
    from game.map import GameMap, Tile
    from game.country import Country
    from game.combat import CombatSystem
    from game.diplomacy import DiplomacySystem
    from simulation.event_system import EventSystem


class UnitClass(Enum):
    INFANTRY = "infantry"      # 🛡️ Yüksek Can & Zırh, Yakın Dövüş, Kalkan Duvarı
    ARCHER = "archer"          # 🏹 Uzak Menzil (3 kare), Zayıf Zırh, Ateş Oku
    CAVALRY = "cavalry"        # 🐎 Hızlı Hareket (3 kare), Kuşatma Bonusu, Hücum
    CATAPULT = "catapult"      # ☄️ Uzun Menzil (4 kare), Ağır Kuşatma Hasarı


class ArmyStatus(Enum):
    IDLE = "idle"
    MOVING = "moving"
    ENGAGED = "engaged"
    GARRISONED = "garrisoned"
    SIEGING = "sieging"


class EnvoyStatus(Enum):
    TRAVELING = "traveling"
    DELIVERED = "delivered"
    INTERCEPTED = "intercepted"
    RETURNED = "returned"


@dataclass
class ArmyEntity:
    id: str
    owner: str
    x: int
    y: int
    size: int = 20
    unit_class: UnitClass = UnitClass.INFANTRY
    hp: float = 120.0
    max_hp: float = 120.0
    attack_power: float = 20.0
    defense_power: float = 15.0
    attack_range: int = 1
    movement_speed: int = 1
    destination_x: Optional[int] = None
    destination_y: Optional[int] = None
    status: ArmyStatus = ArmyStatus.IDLE
    morale: float = 100.0
    experience: int = 0
    skills: list[str] = field(default_factory=list)
    is_fortified: bool = False
    cooldowns: dict[str, int] = field(default_factory=dict)
    path: list[tuple[int, int]] = field(default_factory=list)
    creation_turn: int = 1

    def is_alive(self) -> bool:
        return self.hp > 0 and self.size > 0

    def take_damage(self, amount: float) -> float:
        """Hasar al ve gerçek düşen HP miktarını döndür."""
        actual_dmg = max(1.0, amount)
        self.hp = max(0.0, self.hp - actual_dmg)
        # HP oranına göre asker sayısı da orantılı güncellenir
        self.size = max(0, int((self.hp / max(1.0, self.max_hp)) * (self.size if self.size > 0 else 20)))
        if self.hp <= 0:
            self.size = 0
            self.status = ArmyStatus.IDLE
        return actual_dmg

    def set_target(self, dest_x: int, dest_y: int, game_map: "GameMap") -> bool:
        """Hedef belirle ve A* yolunu hesapla."""
        self.destination_x = dest_x
        self.destination_y = dest_y
        calculated_path = find_path(game_map, (self.x, self.y), (dest_x, dest_y))
        if calculated_path:
            self.path = calculated_path
            self.status = ArmyStatus.MOVING
            return True
        elif (self.x, self.y) == (dest_x, dest_y):
            self.path = []
            self.status = ArmyStatus.IDLE
            return True
        return False

    def step(self, game_map: "GameMap") -> Optional[tuple[int, int, int, int]]:
        """Hızı kadar kare ilerle. Dönüş: (old_x, old_y, new_x, new_y) veya None."""
        if not self.path or self.status not in (ArmyStatus.MOVING, ArmyStatus.IDLE):
            return None

        old_x, old_y = self.x, self.y
        steps_to_take = min(self.movement_speed, len(self.path))
        for _ in range(steps_to_take):
            if self.path:
                next_tile = self.path.pop(0)
                self.x, self.y = next_tile

        if not self.path:
            self.status = ArmyStatus.IDLE

        return (old_x, old_y, self.x, self.y)

    def split(self, amount: int, new_id: str, turn: int = 1) -> Optional["ArmyEntity"]:
        """Ordudan belirli miktarda askeri ayırıp yeni bir ArmyEntity oluşturur."""
        if amount <= 0 or amount >= self.size:
            return None
        self.size -= amount
        new_army = ArmyEntity(
            id=new_id,
            owner=self.owner,
            x=self.x,
            y=self.y,
            size=amount,
            unit_class=self.unit_class,
            hp=(self.hp * (amount / (self.size + amount))),
            max_hp=self.max_hp,
            attack_power=self.attack_power,
            defense_power=self.defense_power,
            attack_range=self.attack_range,
            movement_speed=self.movement_speed,
            status=ArmyStatus.IDLE,
            morale=self.morale,
            experience=self.experience,
            skills=list(self.skills),
            creation_turn=turn,
        )
        return new_army


@dataclass
class EnvoyEntity:
    id: str
    owner: str
    target_agent_id: str
    x: int
    y: int
    destination_x: int
    destination_y: int
    payload_message: Optional[str] = None
    payload_contract: Optional[dict] = None
    status: EnvoyStatus = EnvoyStatus.TRAVELING
    movement_speed: int = 2
    path: list[tuple[int, int]] = field(default_factory=list)
    dispatch_turn: int = 1

    def step(self, game_map: "GameMap") -> Optional[tuple[int, int, int, int]]:
        """Elçiyi hedefe doğru ilerlet."""
        if not self.path or self.status != EnvoyStatus.TRAVELING:
            return None

        old_x, old_y = self.x, self.y
        steps_to_take = min(self.movement_speed, len(self.path))
        for _ in range(steps_to_take):
            if self.path:
                next_tile = self.path.pop(0)
                self.x, self.y = next_tile

        if not self.path or (self.x, self.y) == (self.destination_x, self.destination_y):
            self.status = EnvoyStatus.DELIVERED

        return (old_x, old_y, self.x, self.y)


class EntityManager:
    """Oyun dünyasındaki tüm fiziksel ordu ve elçi varlıklarını yönetir."""

    def __init__(self):
        self.armies: dict[str, ArmyEntity] = {}
        self.envoys: dict[str, EnvoyEntity] = {}
        self._army_counter: int = 0
        self._envoy_counter: int = 0

    def spawn_army(
        self,
        owner: str,
        x: int,
        y: int,
        size: int = 20,
        unit_class: UnitClass = UnitClass.INFANTRY,
        turn: int = 1,
    ) -> ArmyEntity:
        """Yeni bir taktiksel ordu birliği oluştur."""
        self._army_counter += 1
        prefix = {
            UnitClass.INFANTRY: "INF",
            UnitClass.ARCHER: "ARC",
            UnitClass.CAVALRY: "CAV",
            UnitClass.CATAPULT: "CAT",
        }.get(unit_class, "ARM")

        army_id = f"{prefix}_{owner}_{self._army_counter:03d}"

        # Sınıfa özel taktiksel statlar
        if unit_class == UnitClass.INFANTRY:
            hp, max_hp, atk, df, rng, spd, skills = 120.0, 120.0, 22.0, 16.0, 1, 1, ["shield_wall"]
        elif unit_class == UnitClass.ARCHER:
            hp, max_hp, atk, df, rng, spd, skills = 80.0, 80.0, 26.0, 6.0, 3, 1, ["fire_arrow"]
        elif unit_class == UnitClass.CAVALRY:
            hp, max_hp, atk, df, rng, spd, skills = 100.0, 100.0, 30.0, 10.0, 1, 3, ["charge"]
        elif unit_class == UnitClass.CATAPULT:
            hp, max_hp, atk, df, rng, spd, skills = 70.0, 70.0, 48.0, 2.0, 4, 1, ["siege_barrage"]
        else:
            hp, max_hp, atk, df, rng, spd, skills = 100.0, 100.0, 20.0, 10.0, 1, 1, []

        army = ArmyEntity(
            id=army_id,
            owner=owner,
            x=x,
            y=y,
            size=size,
            unit_class=unit_class,
            hp=hp,
            max_hp=max_hp,
            attack_power=atk,
            defense_power=df,
            attack_range=rng,
            movement_speed=spd,
            status=ArmyStatus.IDLE,
            skills=skills,
            creation_turn=turn,
        )
        self.armies[army_id] = army
        return army

    def split_army(self, army_id: str, amount: int, turn: int = 1) -> Optional[ArmyEntity]:
        """Var olan bir orduyu böl."""
        army = self.armies.get(army_id)
        if not army:
            return None
        self._army_counter += 1
        new_id = f"ARMY_{army.owner}_{self._army_counter:03d}"
        new_army = army.split(amount, new_id, turn=turn)
        if new_army:
            self.armies[new_id] = new_army
        return new_army

    def dispatch_envoy(
        self,
        owner: str,
        target_agent_id: str,
        start_x: int,
        start_y: int,
        dest_x: int,
        dest_y: int,
        message: Optional[str],
        contract_data: Optional[dict],
        turn: int,
        game_map: "GameMap",
    ) -> EnvoyEntity:
        """Yeni bir elçi yola çıkar."""
        self._envoy_counter += 1
        envoy_id = f"ENV_{owner}_{self._envoy_counter:03d}"
        path = find_path(game_map, (start_x, start_y), (dest_x, dest_y)) or []

        envoy = EnvoyEntity(
            id=envoy_id,
            owner=owner,
            target_agent_id=target_agent_id,
            x=start_x,
            y=start_y,
            destination_x=dest_x,
            destination_y=dest_y,
            payload_message=message,
            payload_contract=contract_data,
            path=path,
            dispatch_turn=turn,
        )
        self.envoys[envoy_id] = envoy
        return envoy

    def get_armies_at(self, x: int, y: int) -> list[ArmyEntity]:
        return [a for a in self.armies.values() if a.is_alive() and a.x == x and a.y == y]

    def get_armies_for(self, owner: str) -> list[ArmyEntity]:
        return [a for a in self.armies.values() if a.is_alive() and a.owner == owner]

    def step_all(
        self,
        game_map: "GameMap",
        turn: int,
        events: "EventSystem",
        countries: list["Country"],
        combat: "CombatSystem",
    ) -> None:
        """Tüm varlıkları hareket ettirir, menzilli ve yakın dövüş taktiksel çatışmalarını çözer."""
        # 1. Elçilerin Hareketi ve Teslimatları
        for envoy in list(self.envoys.values()):
            if envoy.status == EnvoyStatus.TRAVELING:
                envoy.step(game_map)
                if envoy.status == EnvoyStatus.DELIVERED:
                    target_c = next((c for c in countries if c.agent_id == envoy.target_agent_id), None)
                    if target_c and envoy.payload_message:
                        target_c.receive_message(envoy.owner, envoy.payload_message, turn)
                        events.add_narrative(
                            turn,
                            f"📜 [ENVOY_DELIVERED] Envoy {envoy.id} delivered diplomatic dispatch from {envoy.owner} to {envoy.target_agent_id}!"
                        )
                    if envoy.id in self.envoys:
                        del self.envoys[envoy.id]

        # 2. Orduların Hareketi
        for army in list(self.armies.values()):
            if army.is_alive() and army.status in (ArmyStatus.MOVING, ArmyStatus.IDLE):
                army.step(game_map)

        # 3. Taktiksel Saldırı Taraması (Menzilli Okçular / Mancınıklar ve Yakın Dövüş)
        for army in list(self.armies.values()):
            if not army.is_alive():
                continue

            # Menzildeki en yakın düşman birliğini ara
            best_target: Optional[ArmyEntity] = None
            best_dist = 999.0

            for other in self.armies.values():
                if other.is_alive() and other.owner != army.owner:
                    dist = math.hypot(army.x - other.x, army.y - other.y)
                    if dist <= army.attack_range and dist < best_dist:
                        best_dist = dist
                        best_target = other

            if best_target:
                # Taktiksel saldırıyı çöz
                res = combat.resolve_tactical_attack(army, best_target, game_map)
                army.status = ArmyStatus.ENGAGED
                best_target.status = ArmyStatus.ENGAGED
                for ev in res.events:
                    events.add_narrative(turn, ev)

        # 4. Ölüleri Temizle
        self.cleanup_dead()

    def cleanup_dead(self) -> None:
        """Ölü birlikleri temizle."""
        dead_armies = [aid for aid, a in self.armies.items() if not a.is_alive()]
        for aid in dead_armies:
            del self.armies[aid]

        delivered_envoys = [eid for eid, e in self.envoys.items() if e.status in (EnvoyStatus.DELIVERED, EnvoyStatus.INTERCEPTED)]
        for eid in delivered_envoys:
            del self.envoys[eid]