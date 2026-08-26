"""
entities.py — Fiziksel Varlık Sistemi (ArmyEntity, EnvoyEntity ve EntityManager)
Haritada koordinatı, hedefi, yolu ve hareket durumu olan dinamik nesneler.
Saha çatışmaları, birleşme (merge), bölünme (split) ve kuşatma (siege) mekanikleri içerir.
"""
from __future__ import annotations
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
    size: int
    destination_x: Optional[int] = None
    destination_y: Optional[int] = None
    status: ArmyStatus = ArmyStatus.IDLE
    movement_speed: int = 1
    morale: float = 100.0
    experience: int = 0
    path: list[tuple[int, int]] = field(default_factory=list)
    creation_turn: int = 1

    def is_alive(self) -> bool:
        return self.size > 0

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
            status=ArmyStatus.IDLE,
            movement_speed=self.movement_speed,
            morale=self.morale,
            experience=self.experience,
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
        size: int,
        turn: int = 1,
    ) -> ArmyEntity:
        """Yeni bir ordu birliği oluştur."""
        self._army_counter += 1
        army_id = f"ARMY_{owner}_{self._army_counter:03d}"
        army = ArmyEntity(
            id=army_id,
            owner=owner,
            x=x,
            y=y,
            size=size,
            status=ArmyStatus.IDLE,
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
        envoy_id = f"ENV_{owner}_TO_{target_agent_id}_{self._envoy_counter:03d}"
        path = find_path(game_map, (start_x, start_y), (dest_x, dest_y))
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
            status=EnvoyStatus.TRAVELING,
            path=path,
            dispatch_turn=turn,
        )
        self.envoys[envoy_id] = envoy
        return envoy

    def get_armies_for(self, owner: str) -> list[ArmyEntity]:
        return [a for a in self.armies.values() if a.owner == owner and a.is_alive()]

    def get_total_field_army_for(self, owner: str) -> int:
        """Bir ülkenin sahadaki tüm ordularının asker toplamı."""
        return sum(a.size for a in self.get_armies_for(owner))

    def merge_same_owner_armies(self, event_system: Optional["EventSystem"] = None, turn: int = 1) -> None:
        """Aynı koordinattaki aynı sahibe ait orduları tek bir birlikte birleştirir."""
        tile_armies: dict[tuple[int, int, str], list[ArmyEntity]] = defaultdict(list)
        for a in self.armies.values():
            if a.is_alive():
                tile_armies[(a.x, a.y, a.owner)].append(a)

        for (x, y, owner), armies in tile_armies.items():
            if len(armies) > 1:
                main_army = armies[0]
                total_size = sum(a.size for a in armies)
                weighted_morale = sum(a.morale * a.size for a in armies) / total_size
                main_army.size = total_size
                main_army.morale = weighted_morale

                for other in armies[1:]:
                    other.size = 0
                    if other.id in self.armies:
                        del self.armies[other.id]

                if event_system:
                    event_system.add_narrative(
                        turn,
                        f"🛡️ [ARMY_MERGED] Armies of {owner} merged at ({x},{y}) [Total Size: {total_size}]"
                    )

    def resolve_encounters(
        self,
        game_map: "GameMap",
        combat_system: Optional["CombatSystem"] = None,
        event_system: Optional["EventSystem"] = None,
        countries: Optional[list["Country"]] = None,
        turn: int = 1,
    ) -> None:
        """
        Aynı tile'daki düşman ordularının çatışmasını ve şehir kuşatmalarını çözer.
        """
        if not combat_system:
            return

        # 1. Aynı tile'daki dost orduları birleştir
        self.merge_same_owner_armies(event_system, turn)

        # 2. Tile'lara göre orduları grupla
        tile_map: dict[tuple[int, int], list[ArmyEntity]] = defaultdict(list)
        for a in list(self.armies.values()):
            if a.is_alive():
                tile_map[(a.x, a.y)].append(a)

        country_lookup = {c.agent_id: c for c in (countries or [])}

        for (tx, ty), armies in tile_map.items():
            alive_armies = [a for a in armies if a.is_alive()]
            if len(alive_armies) >= 2:
                # Farklı sahipler mi?
                owners = set(a.owner for a in alive_armies)
                if len(owners) > 1:
                    army_a = alive_armies[0]
                    army_b = alive_armies[1]
                    tile = game_map.get_tile(tx, ty)
                    if not tile:
                        continue

                    tech_a = country_lookup[army_a.owner].resources.technology if army_a.owner in country_lookup else 1
                    tech_b = country_lookup[army_b.owner].resources.technology if army_b.owner in country_lookup else 1

                    if event_system:
                        event_system.add_narrative(
                            turn,
                            f"⚔️ [BATTLE_STARTED] {army_a.id} ({army_a.owner}) clashed with {army_b.id} ({army_b.owner}) at ({tx},{ty})!"
                        )

                    res = combat_system.resolve_unit_clash(
                        army_a, army_b, tile, tech_a=tech_a, tech_b=tech_b, game_map=game_map
                    )

                    if event_system:
                        event_system.add_narrative(
                            turn,
                            f"💥 [BATTLE_ENDED] {res['winner_id']} won! Losses: {res['losses_a']} / {res['losses_b']}"
                        )

                    if not army_a.is_alive():
                        if event_system:
                            event_system.add_narrative(turn, f"💀 [ARMY_DESTROYED] {army_a.id} was destroyed!")
                        if army_a.id in self.armies:
                            del self.armies[army_a.id]

                    if not army_b.is_alive():
                        if event_system:
                            event_system.add_narrative(turn, f"💀 [ARMY_DESTROYED] {army_b.id} was destroyed!")
                        if army_b.id in self.armies:
                            del self.armies[army_b.id]

            # Şehir Kuşatması: Ordu düşman CITY tile'ında mı?
            for a in [arm for arm in armies if arm.is_alive()]:
                tile = game_map.get_tile(a.x, a.y)
                if tile and tile.tile_type.value == "city" and tile.owner and tile.owner != a.owner:
                    defending_country = country_lookup.get(tile.owner)
                    if defending_country and defending_country.garrison_army > 0:
                        tech_att = country_lookup[a.owner].resources.technology if a.owner in country_lookup else 1
                        tech_def = defending_country.resources.technology

                        if event_system:
                            event_system.add_narrative(
                                turn,
                                f"🏰 [SIEGE_STARTED] {a.id} is besieging {tile.owner}'s city at ({a.x},{a.y})!"
                            )

                        s_res = combat_system.resolve_city_siege(
                            a, defending_country, tile, tech_att=tech_att, tech_def=tech_def, game_map=game_map
                        )

                        if event_system:
                            if s_res["city_captured"]:
                                event_system.add_narrative(
                                    turn,
                                    f"🏆 [CITY_CAPTURED] {a.owner} captured city at ({a.x},{a.y}) from {tile.owner}!"
                                )
                            else:
                                event_system.add_narrative(
                                    turn,
                                    f"🛡️ [SIEGE_REPELLED] {tile.owner} repelled the siege at ({a.x},{a.y})."
                                )

                        if not a.is_alive():
                            if event_system:
                                event_system.add_narrative(turn, f"💀 [ARMY_DESTROYED] {a.id} was destroyed in siege!")
                            if a.id in self.armies:
                                del self.armies[a.id]

    def step_all(
        self,
        game_map: "GameMap",
        current_turn: int,
        event_system: Optional["EventSystem"] = None,
        countries: Optional[list["Country"]] = None,
        combat_system: Optional["CombatSystem"] = None,
    ) -> list[dict]:
        """
        Tüm varlıkları 1 adım ilerletir, çatışmaları çözer ve olayları üretir.
        """
        events_generated = []

        # 1. Orduları hareket ettir
        dead_armies = []
        for army in list(self.armies.values()):
            if not army.is_alive():
                dead_armies.append(army.id)
                continue

            if army.status == ArmyStatus.MOVING and army.path:
                move_res = army.step(game_map)
                if move_res:
                    ox, oy, nx, ny = move_res
                    if event_system:
                        event_system.add_narrative(
                            current_turn,
                            f"🚩 [ARMY_MOVED] {army.id} ({army.owner}) moved to ({nx},{ny}) [Size: {army.size}]"
                        )
                    if not army.path:
                        if event_system:
                            event_system.add_narrative(
                                current_turn,
                                f"🏁 [ARMY_ARRIVED] {army.id} reached destination ({army.x},{army.y})"
                            )

        for da in dead_armies:
            if da in self.armies:
                del self.armies[da]

        # 2. Elçileri hareket ettir ve varışta mesajları teslim et
        delivered_envoys = []
        for envoy in list(self.envoys.values()):
            if envoy.status == EnvoyStatus.TRAVELING:
                move_res = envoy.step(game_map)
                if move_res:
                    ox, oy, nx, ny = move_res
                    if event_system:
                        event_system.add_narrative(
                            current_turn,
                            f"🐎 [ENVOY_MOVED] {envoy.id} traveled to ({nx},{ny})"
                        )

            if envoy.status == EnvoyStatus.DELIVERED:
                if countries:
                    target_country = next((c for c in countries if c.agent_id == envoy.target_agent_id), None)
                    if target_country and envoy.payload_message:
                        target_country.receive_message(envoy.owner, envoy.payload_message, current_turn)
                        if event_system:
                            event_system.add_narrative(
                                current_turn,
                                f"📜 [DIPLOMATIC_MESSAGE_DELIVERED] Envoy {envoy.id} delivered letter to {envoy.target_agent_id}: \"{envoy.payload_message}\""
                            )
                delivered_envoys.append(envoy.id)

        for de in delivered_envoys:
            if de in self.envoys:
                del self.envoys[de]

        # 3. Çatışmaları ve Kuşatmaları Çöz
        self.resolve_encounters(game_map, combat_system, event_system, countries, current_turn)

        # 4. Ülkelerin toplam ordu sayısını senkronize et
        if countries:
            for country in countries:
                field_total = self.get_total_field_army_for(country.agent_id)
                country.resources.army = country.garrison_army + field_total

        return events_generated
