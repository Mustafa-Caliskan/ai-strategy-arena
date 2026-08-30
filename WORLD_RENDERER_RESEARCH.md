# AI STRATEGY ARENA — WORLD SIMULATION & RENDERER RESEARCH

**Tarih:** 26 Ağustos 2026
**Rol:** Software Architect + Game Engine Researcher + Codebase Auditor
**Kapsam:** Yalnızca araştırma ve analiz. Kod değiştirilmedi, dosya oluşturulmadı/silinmedi, dependency değiştirilmedi, commit/push yapılmadı.

---

## 1. Executive Summary

Bu araştırma, mevcut LLM benchmark/simulation motorunu **koruyarak** projeyi görsel olarak yaşayan, izlenebilir ve WorldBox-benzeri bir strateji dünyasına dönüştürmek için doğru renderer/map/entity mimarisini belirlemeyi amaçlamaktadır.

**Kritik bulgular:**

1. **Mevcut renderer, simulation'dan ayrılmamıştır.** `ui/renderer.py` doğrudan `TurnManager`'ı (`self._manager`) okur ve `game_map`, `countries`, `diplomacy`, `events` nesnelerine erişir. Renderer sim'i mutate etmez (iyi), ancak renderer ile sim arasında temiz bir arayüz (view model) yoktur.

2. **Fiziksel varlıklar (ArmyEntity, EnvoyEntity) hiç render edilmiyor.** `ui/` klasöründe yapılan grep, yalnızca scoreboard'da ordu sayısının metin olarak gösterildiğini doğruladı. Saha orduları, elçiler, sancaklar, hedef noktaları, savaş/kuşatma animasyonları **görsel olarak yok**.

3. **Harita 20x20'dir ve her frame tamamen yeniden çizilir.** `map_view.py:60-79` her `draw()` çağrısında tüm tile'ları, yolları, binaları, sınırları ve başkentleri yeniden çizer. Viewport culling, chunk sistemi, cached surface **yoktur**.

4. **Kamera/zoom/pan yoktur.** `renderer.py:66-67` haritayı sabit offset ile ortalar. `map_view.py` zoom/pan desteklemez.

5. **En güçlü referans Mini WorldBox'tur** (Python + Pygame). Pre-rendered terrain surface + viewport culling (`subsurface`) + `smoothscale` zoom yaklaşımı, AI Strategy Arena'nın mevcut Pygame mimarisine en uygun ve en az maliyetli yükseltmedir.

6. **Marching Squares GEREKLİ DEĞİLDİR.** Mevcut 20x20 (ve hedeflenen 100x100) harita boyutunda, tile-based rendering + hafif jittered border yeterli görsel/performans oranı sağlar. Marching Squares yalnızca 250x250+ haritalarda ve "organik kıyı şeridi" estetiği kritikse düşünülmelidir.

7. **Renderer değiştirmek MANTIKLI DEĞİLDİR.** Mevcut Pygame korunmalıdır. PyOpenGL/Web migration, mevcut simülasyon+benchmark motorunu riske atar ve 4-8 AI desteği için gereksiz karmaşıklık ekler.

**Önerilen mimari:** AEON'un `src/sim` (otoriter state) / `src/render` (view) / `src/game` (controller) ayrımını Pygame'e uyarlayarak, mevcut `game/` ve `simulation/` klasörlerini **otoriter simülasyon** olarak koruyup, yeni bir `render/` katmanı (camera, view-model, cached terrain surface, entity sprites, fx) eklemek. Bu, mevcut benchmark motorunu hiç etkilemeden görsel katmanı izole eder.

---

## 2. Sovereign Analizi

**Kaynak:** [Sovereign](https://github.com/CodeByBryant/Sovereign) — TypeScript + Electron + Canvas, MIT lisansı.

### Mimari
```
sovereign/
├── src/core/
│   ├── camera/Camera.ts        # Pan/zoom state + koordinat dönüşümleri
│   ├── rendering/Renderer.ts   # Chunked Canvas 2D draw loop
│   ├── simulation/Simulation.ts
│   ├── terrain/TerrainGenerator.ts  # Multi-layer noise terrain
│   ├── world/WorldMap.ts       # Struct-of-arrays tile storage
│   └── entities/Nation.ts      # Nation class
```

### Önemli tasarım kararları

**1. Struct-of-Arrays tile veri yapısı** (`WorldMap.ts`):
- 8 typed-array katmanı (Float32Array/Uint8Array) — 4M JS nesnesi yerine.
- `at(x, y)` ergonomik erişimci, `TileInfo` snapshot döndürür.
- 2000x2000 harita = 4M tile, ~68 MB IndexedDB.
- **AI Strategy Arena için:** Mevcut `game/map.py` `list[list[Tile]]` (nesne listesi) kullanır. 20x20'de sorun yok, ancak 250x250+ için typed-array'e geçiş gerekir.

**2. Chunked ImageBitmap rendering** (`Renderer.ts`):
- Harita tile-boyutlu `ImageBitmap` chunk'lara bölünür.
- Her frame yalnızca viewport ile örtüşen chunk'lar çizilir (frustum culling).
- `imageSmoothingEnabled = false` pixel-art görünümü korur.
- **AI Strategy Arena için:** Pygame'de `Surface` chunk'ları + `blit` ile aynı yaklaşım uygulanabilir.

**3. Kamera** (`Camera.ts`):
- `pan(deltaX, deltaY)`, `zoomAt(scale, anchorX, anchorY, ...)` — imleç altındaki dünya noktası sabit kalır.
- `applyTransform(ctx, ...)` — translate + scale + translate.
- `screenToWorld` / `worldToScreen` dönüşümleri.
- **AI Strategy Arena için:** Bu kamera modeli Pygame'e doğrudan uyarlanabilir.

**4. Terrain üretimi** (`TerrainGenerator.ts`):
- Simplex noise (fBm) — elevation, temperature, humidity, biome-variation.
- Her katman bağımsız seed'lenir (`${seed}-elevation` vb.).
- 26 biyom, organik jittered sınırlar.
- Nehirler: noise zero-crossing algoritması.
- **AI Strategy Arena için:** Mevcut `game/map.py` basit rastgele yerleştirme kullanır. Noise-based terrain, daha organik haritalar için en iyi yükseltmedir.

**5. Overlay modları:** Elevation, Temperature, Humidity, Biome, Strategic, Resource, Political. **AI Strategy Arena için:** Political overlay (ülke renkleri + sınırlar) zaten mevcut; Resource overlay eklenebilir.

**6. Simulation-render ayrımı:** `Simulation.ts` ayrı, `Renderer.ts` yalnızca chunk'ları çizer. Zustand store tek doğruluk kaynağı.

---

## 3. AEON Analizi

**Kaynak:** [AEON](https://github.com/lordbasilaiassistant-sudo/aeon) — JavaScript (ES modules), browser, MIT lisansı.

### Mimari (en önemli referans)
```
src/
├── sim/       # Otoriter simülasyon state'i
│   ├── world.js, brain.js, agent.js, sim.js, tech.js,
│   ├── civics.js, culture.js, anthropology.js, settlement.js,
│   ├── territory.js, resources.js, animals.js, diplomacy.js, heritage.js
├── render/    # Görsel katman (view)
│   ├── renderer.js  + visuals.js (stylized canvas), camera.js, fx.js
├── game/      # Controller
│   ├── game.js, governance.js (simetrik human/AI API), ui.js, input.js
```

### Kritik sözleşmeler (ARCHITECTURE.md)
1. **Perception** (Mechanics → Cognition): sim her tick'te agent başına `Float32Array` duyular doldurur.
2. **Action** (Cognition → Mechanics): beyin `Float32Array` eylem sürücüleri üretir.
3. **WorldView** (Mechanics → Frontend): **Frontend yalnızca sim state'i OKUR (world tiles, pooled agents, settlements, territory, nations, fx). Frontend asla sim'i mutate etmez.** ← AI Strategy Arena için en kritik ders.
4. **GovernanceAPI** (Statecraft ↔ everyone): insan ve AI aynı fonksiyonları çağırır (`setPolicy`, `declareWar`, `proposeAlliance`, `trade`, `rally/migrate`). ← AI Strategy Arena'nın `TurnManager`'ına benzer.
5. **Events/Lore** (Statecraft → Frontend): `sim.emit(...)` ile UI'a olaylar.

### Renderer (`renderer.js`)
- **Pre-rendered terrain:** `bakeTerrain()` — 1px/tile offscreen canvas. `W.dirty` ise yeniden bake edilir.
- **Viewport culling:** `cam.viewBounds()` ile görünür tile aralığı hesaplanır, yalnızca o aralık çizilir.
- **Quality governor:** `setQuality('low'|'high'|'auto')` — dpr clamp, bloom kapatma, particle inceltme. Zayıf donanımda FPS korur.
- **Katmanlı çizim sırası:** terrain → water shimmer → food → territory → borders → resources → animals → settlements → agents → selection → army target → command → ghost → FX → clouds → post (day/night, vignette, bloom).
- **Minimap:** cached terrain+territory base, ~2s'de bir yeniden build edilir; canlı viewport dikdörtgeni üstüne çizilir.
- **FX (`fx.js`):** particles, rings, floating text, screenshake, full-flash. "Juice en ucuz 'harika grafik' çarpanıdır."

### Kamera (`camera.js`)
- **Smooth kamera:** `update()` içinde `k = 0.18` ile hedefe yumuşak interpolasyon (lerp).
- `zoomAt` imleç altındaki noktayı sabitler.
- `viewBounds()` culling için görünür tile dikdörtgeni döndürür.
- `follow` — bir ajana/nasyona takip.

### Simulation-render ayrımı
- `sim.js` otoriter state'i tutar; `renderer.js` yalnızca okur.
- `game.js` (controller) hem sim'i hem render'ı koordine eder.
- **AI Strategy Arena için:** Bu, mevcut `TurnManager` (sim) + yeni `render/` katmanı (view) + `main.py` (controller) ayrımına birebir uyar.

---

## 4. Mini WorldBox Analizi

**Kaynak:** [Mini WorldBox](https://github.com/dani931004/worldbox) — Python + Pygame, en doğrudan referans.

### Mimari
```
main.py → src/game.py (Game class)
src/
├── game.py      # Ana döngü, event handling, rendering
├── world.py     # World class (terrain, entities, spatial grid)
├── entity.py    # Human, Animal, Child, House, Tree
├── camera.py    # Camera class (pan/zoom)
├── constants.py # Renkler, boyutlar, terrain map
```

### Önemli tasarım kararları

**1. Pre-rendered terrain surface** (`world.py:_build_terrain_surface`):
- `self.terrain_surface = pygame.Surface((MAP_WIDTH, MAP_HEIGHT))` — tüm harita bir kez çizilir.
- `_variant_color(base, x, y)` — deterministik per-tile renk varyasyonu (hash tabanlı, `(x ^ y) % 21 - 10`).
- Terrain değiştiğinde (`set_terrain`) yalnızca o tile yeniden çizilir.
- **AI Strategy Arena için:** Mevcut `map_view.py` her frame tüm haritayı çizer. Bu, pre-rendered surface'a geçişle çözülür.

**2. Viewport culling + zoom** (`game.py:draw_world`):
```python
src_rect = self.camera.get_src_rect()
src_rect = src_rect.clip(pygame.Rect(0, 0, MAP_WIDTH, MAP_HEIGHT))
subsurface = self.world.terrain_surface.subsurface(src_rect)
if self.camera.zoom < 1.0:
    scaled = pygame.transform.smoothscale(subsurface, (viewport_w, viewport_h))
else:
    scaled = pygame.transform.scale(subsurface, (viewport_w, viewport_h))
self.screen.blit(scaled, (0, 0))
```
- `subsurface` yalnızca görünür bölgeyi alır.
- `smoothscale` zoom<1 için, `scale` zoom>=1 için.
- **AI Strategy Arena için:** Bu, Pygame'de viewport culling + zoom'un en basit ve en etkili yolu.

**3. Kamera** (`camera.py`):
- `get_src_rect()` — viewport/zoom'dan kaynak dikdörtgen.
- `world_to_screen` / `screen_to_world`.
- `clamp()` — kamera dünya sınırları içinde kalır.
- `zoom_by(dz)` — additive, `[MIN_ZOOM, MAX_ZOOM]` aralığında.

**4. Entity rendering** (`game.py:draw_world`):
- Entity'ler yalnızca `src_rect` içindeyse çizilir (culling).
- `entity.draw(self.screen, self.camera)`.

**5. Spatial grid** (`world.py`):
- `self.spatial_grid` — 5x5 hücreler, `get_entities_in_radius` için O(1) komşu arama.
- **AI Strategy Arena için:** ArmyEntity/EnvoyEntity çarpışma ve görünürlük için faydalı.

**6. FPS benchmark** (`game.py`): F1 ile 300 frame örnekleme, avg/min/max gösterir.

**7. Headless test:** `headless_test.py` — 100 tick, avg tick ~0.037s. **AI Strategy Arena için:** Mevcut `--headless` modu zaten var; renderer'dan bağımsız çalışır.

---

## 5. WorldBox Gameplay/UX

**Kaynak:** [WorldBox Steam](https://store.steampowered.com/app/1206560/) + [superworldbox.com](https://superworldbox.com). WorldBox proprietary'dir; kod kopyalanmaz, yalnızca gameplay/UX referansı olarak kullanılır.

### WorldBox özellikleri ve sınıflandırma

**MUST HAVE (AI Strategy Arena için kritik):**
- **Yaşayan dünya / canlı harita:** Terrain, binalar, sınırlar, başkentler. → Mevcut `map_view.py` bunu kısmen yapar.
- **Kamera pan + zoom:** WorldBox'ın temel etkileşimi. → Mevcut renderer'da YOK.
- **Entity görselleştirme:** Ordular, elçiler, sancaklar. → Mevcut renderer'da YOK.
- **Zaman kontrolü (pause/speed):** WorldBox'ın temel kontrolü. → Mevcut `controls.py` bunu yapar.
- **Siyasi harita overlay (ülke renkleri + sınırlar):** → Mevcut `map_view.py` bunu yapar.
- **Bilgi paneli (ülke kaynakları, diplomasi):** → Mevcut `scoreboard.py` bunu yapar.

**NICE TO HAVE (değer katar, kritik değil):**
- **Minimap:** Civ tarzı stratejik genel bakış. → AEON'da var, eklenebilir.
- **Particles/effects:** Savaş patlamaları, kuşatma göstergeleri, elçi hareket izleri. → AEON `fx.js`'te var.
- **Organik sınırlar / jittered borders:** WorldBox'ın imza görünümü. → Marching Squares veya hafif jitter ile.
- **Nehirler:** Haritaya doğal akış. → Sovereign'da noise zero-crossing ile.
- **Biyom çeşitliliği:** Çöl, orman, dağ, okyanus. → Mevcut `map.py`'de kısmen var.
- **Seçim + bilgi tooltip:** Bir ülkeye/ordusuna tıklayınca detay. → AEON'da var.

**NOT RECOMMENDED (kaçınılmalı):**
- **God powers (yıldırım, tornado, nükleer):** AI Strategy Arena bir benchmark aracıdır; tanrı güçleri benchmark'ı bozar.
- **Fantastik ırklar (elf, ork, cüce):** Benchmark'ın determinizmini bozar.
- **Tam WorldBox mekanik kopyası:** Proprietary ve benchmark amacıyla uyumsuz.
- **Gerçek zamanlı bireysel varlık simülasyonu:** AI Strategy Arena tur tabanlıdır; WorldBox'ın gerçek zamanlı akışı uymaz.

---

## 6. Mevcut AI Strategy Arena Mimarisi

### Simulation state nerede?
- **Otoriter state:** `game/` (GameMap, Country, Resources, Combat, Diplomacy, Contracts, Economy, Entities) + `simulation/turn_manager.py` (TurnManager).
- `TurnManager` tüm sistemleri koordine eder: `self.diplomacy`, `self.economy`, `self.combat`, `self.entities`, `self.state_builder`, `self.win_checker`, `self.prompt_builder`, `self.parser`, `self.validator`, `self.events`.
- `GameMap.tiles` — `list[list[Tile]]`, her Tile bir dataclass (owner, building, has_road, vb.).
- `EntityManager` (`game/entities.py`) — `self.armies: dict[str, ArmyEntity]`, `self.envoys: dict[str, EnvoyEntity]`.

### Rendering state nerede?
- **`ui/` klasörü:** `renderer.py` (GameRenderer), `map_view.py` (MapView), `scoreboard.py`, `event_log.py`, `controls.py`.
- `GameRenderer` doğrudan `TurnManager`'ı (`self._manager`) tutar ve `m.game_map`, `m.countries`, `m.diplomacy`, `m.events`, `m.current_turn` okur.

### Birbirlerine ne kadar bağlı?
- **Renderer → Simulation:** `renderer.py:139` `m = self._manager`; `renderer.py:145-151` `self.map_view.draw(map_surf, m.game_map, m.countries, ...)`. Renderer, sim'in iç yapısını (GameMap.tiles, Country.resources, DiplomacySystem.relations) doğrudan okur.
- **Simulation → Renderer:** `main.py:211-214` `asyncio.gather(manager.run_game_async(), renderer.run_async(manager))`. Simulation, renderer'ı bilmez; yalnızca `on_turn_complete` callback'i ve `speed_multiplier`/`is_paused`/`is_running` bayrakları üzerinden etkileşir.
- **Sonuç:** Renderer, simulation'ı **çok iyi bilir** (iç yapıya erişir), simulation renderer'ı **hiç bilmez**. Bu, AEON'un "Frontend sim'i okur, mutate etmez" sözleşmesine kısmen uyar, ancak temiz bir view-model arayüzü yoktur.

### Renderer simulation kodunu ne kadar biliyor?
- `map_view.py` `game.map.TileType`, `game.buildings.BuildingType` import eder.
- `scoreboard.py` `country.resources`, `diplomacy.get_relation`, `diplomacy.contracts` okur.
- Renderer, sim'in dataclass'larına ve enum'larına doğrudan bağımlıdır.

### Yeni renderer eklemek ne kadar kolay?
- **Orta zorlukta.** Renderer, sim'i mutate etmez (iyi), ancak sim'in iç yapısına sıkı bağlıdır (kötü). Yeni bir renderer, sim'in public API'sini (getter'lar) kullanmalıdır. Mevcut `Country.to_dict()`, `GameMap.get_tiles_owned_by()` gibi metotlar yardımcı olur.
- `main.py`'de renderer'ı değiştirmek kolaydır (`run_ui` fonksiyonu), ancak `renderer.py`'nin sim'e erişim şekli yeniden düşünülmelidir.

### Mevcut mimarinin darboğazları
1. **Her frame tüm haritayı çizmek** (`map_view.py:60-79`) — 20x20'de ~400 tile, 100x100'de 10,000 tile. Viewport culling yok.
2. **Entity rendering yok** — ArmyEntity/EnvoyEntity görsel olarak yok.
3. **Kamera/zoom/pan yok** — harita sabit offset ile ortalanır.
4. **Sim-render arayüzü yok** — renderer sim'in iç yapısına bağımlı.
5. **Tur başına 1s yapay uyku** (`turn_manager.py:119`) — bu, renderer'dan bağımsız bir performans sorunudur (önceki forensic raporda tespit edildi).

---

## 7. Mevcut Renderer Denetimi

### Map nasıl çiziliyor?
- `map_view.py:60-62` — `for col in game_map.tiles: for tile in col: self._draw_tile(...)`. Her tile için `pygame.draw.rect`.

### Tile'lar nasıl çiziliyor?
- `_draw_tile` (`map_view.py:81-104`): base renk → ülke sahipliği renk karışımı (blend) → terrain detayı (ağaç, dağ, maden, su) → border.
- `_draw_terrain_detail` (`map_view.py:106-125`): FOREST için üçlü ağaç, MOUNTAIN için çift dağ, MINE için daireler, WATER için çizgiler.

### Her frame ne yeniden çiziliyor?
- **Tüm harita** (`map_view.py:60-79`): zemin, yollar, binalar, sınırlar, başkentler. Her `draw()` çağrısında.
- `renderer.py:143-152` — her frame yeni bir `pygame.Surface` oluşturulur, `map_view.draw` ile doldurulur, `blit` edilir.

### Entity rendering nasıl?
- **YOK.** `ui/` klasöründe ArmyEntity/EnvoyEntity render edilmez. Yalnızca scoreboard'da ordu sayısı metin olarak gösterilir.

### Camera/zoom/pan var mı?
- **YOK.** `renderer.py:66-67` `map_offset_x/y` sabit offset (haritayı ortalar). `map_view.py` zoom/pan desteklemez.

### Viewport culling var mı?
- **YOK.** Tüm tile'lar her frame çizilir.

### Chunk sistemi var mı?
- **YOK.** Harita tek parça çizilir.

### Cached surface var mı?
- **YOK.** Her frame yeni surface oluşturulur (`renderer.py:143`).

### Sprite/animation sistemi var mı?
- **YOK.** Statik `pygame.draw` çağrıları. Animation yok.

### UI nasıl çiziliyor?
- `renderer.py:178-204`: scoreboard (sağ panel), event log (alt panel), controls (alt bar), speed göstergesi. Hepsi her frame yeniden çizilir.

### Muhtemel FPS darboğazları
1. **Her frame tüm haritayı çizmek** — 20x20'de ~400 `draw.rect` + detay çizimleri. 100x100'de 10,000+ çizim → FPS düşer.
2. **Her frame yeni Surface oluşturmak** (`renderer.py:143`) — bellek tahsisi.
3. **Font render** — her frame metin render edilir (scoreboard, event log). Font render CPU yoğundur.
4. **Tur başına 1s uyku** — renderer'dan bağımsız, ancak UI'ın "canlı" hissetmesini engeller.

---

## 8. Feature Mapping (WorldBox → AI Strategy Arena)

| WorldBox | AI Strategy Arena (mevcut kod) | Durum |
|---|---|---|
| Kingdom | `Country` (`game/country.py`) | ✅ Var |
| Army | `ArmyEntity` (`game/entities.py`) | ✅ Sim'de var, ❌ Render'da yok |
| Envoy/Diplomacy | `EnvoyEntity` + `DiplomacySystem` (`game/entities.py`, `game/diplomacy.py`) | ✅ Sim'de var, ❌ Render'da yok |
| Territory | `GameMap` + `Tile.owner` (`game/map.py`) | ✅ Var |
| Resources | `Resources` (`game/resources.py`) + `EconomySystem` (`game/economy.py`) | ✅ Var |
| Wars | `CombatSystem` (`game/combat.py`) + `DiplomacySystem` | ✅ Var |
| Cities | `BuildingType.CITY` + `Building` (`game/buildings.py`) | ✅ Var |
| Roads | `Tile.has_road` + `pathfinding.py` | ✅ Var |
| Borders | `_draw_borders` (`ui/map_view.py:184-198`) | ✅ Render'da var (basit) |
| Villages | `BuildingType.FARM/LUMBER_MILL/MINE/FORT` | ✅ Var |
| Population | `Resources.population` | ✅ Var |
| Contracts/Pacts | `ContractManager` (`game/contracts.py`) | ✅ Var |
| Minimap | — | ❌ Yok |
| Camera/zoom/pan | — | ❌ Yok |
| Particles/effects | — | ❌ Yok |
| Entity animation | — | ❌ Yok |
| Selection/info panel | — | ❌ Yok (yalnızca statik scoreboard) |
| Map overlays | — | ❌ Yok (yalnızca siyasi) |

---

## 9. Gap Analysis

| Eksik | Şiddet | Kaynak Referans | Açıklama |
|---|---|---|---|
| Entity rendering (army/envoy) | **CRITICAL** | [AEON] `drawAgents`, [Mini WorldBox] `entity.draw` | LLM kararlarının görsel sonucu (ordu hareketi, elçi) görünmez. Benchmark'ın "izlenebilirliği" için kritik. |
| Kamera pan/zoom | **CRITICAL** | [Sovereign] `Camera.ts`, [AEON] `camera.js`, [Mini WorldBox] `camera.py` | WorldBox-benzeri etkileşimin temeli. |
| Viewport culling | **HIGH** | [Sovereign] `Renderer.ts`, [Mini WorldBox] `subsurface` | 100x100+ haritalarda FPS için zorunlu. |
| Pre-rendered terrain surface | **HIGH** | [Mini WorldBox] `_build_terrain_surface`, [AEON] `bakeTerrain` | Her frame tüm haritayı çizmeyi önler. |
| Simulation-render arayüzü (view-model) | **HIGH** | [AEON] WorldView contract | Renderer'ın sim'in iç yapısına bağımlılığını azaltır. |
| Organic/jittered borders | **MEDIUM** | [Sovereign] biome jitter, [WorldBox] | Siyasi sınırların daha doğal görünümü. |
| Terrain variation / biomes | **MEDIUM** | [Sovereign] `TerrainGenerator.ts`, [Mini WorldBox] `_variant_color` | Per-tile renk varyasyonu + daha fazla biyom. |
| Rivers | **MEDIUM** | [Sovereign] `rivers.ts` | Haritaya doğal akış. |
| Particles/effects | **MEDIUM** | [AEON] `fx.js` | Savaş/kuşatma/elçi görsel geri bildirimi. |
| Minimap | **LOW** | [AEON] `drawMinimap` | Stratejik genel bakış. |
| Selection/info panel | **LOW** | [AEON] `drawSelection` | Ülke/ordusuna tıklayınca detay. |
| Map overlays (resource, diplomasi) | **LOW** | [Sovereign] 7 overlay modu | Kaynak/diplomasi görselleştirme. |
| Large map support (250x250+) | **LOW** | [Sovereign] 2000x2000 | Mevcut hedef 100x100; 250x250+ sonraki aşama. |

---

## 10. Teknoloji Kararı

### Karşılaştırma

| Kriter | Pygame (mevcut) | Pygame + optimized | PyOpenGL | Web/Canvas |
|---|---|---|---|---|
| Performans | Orta | Yüksek (culling + cached) | Çok yüksek | Yüksek |
| Geliştirme maliyeti | Düşük | Düşük-Orta | Yüksek | Yüksek (migration) |
| Python uyumluluğu | ✅ | ✅ | ✅ | ❌ (JS) |
| Mevcut mimariye entegrasyon | ✅ | ✅ | Orta | ❌ (tam yeniden yazım) |
| Karmaşıklık | Düşük | Düşük-Orta | Yüksek | Yüksek |
| Map/entity rendering | ✅ | ✅ | ✅ | ✅ |
| Animation | Orta | Orta | Yüksek | Yüksek |
| Camera | Orta | Orta | Yüksek | Yüksek |
| Large maps | Orta | Yüksek | Çok yüksek | Yüksek |
| 4-8 AI desteği | ✅ | ✅ | ✅ | ✅ |

### NET KARAR: **Mevcut Pygame KORUNMALIDIR.**

**Teknik gerekçe:**
1. **Mevcut simülasyon + benchmark motoru Pygame'den bağımsızdır.** `main.py --headless` ve `--batch` modları renderer olmadan çalışır. Pygame yalnızca `run_ui` modunda kullanılır. Bu, renderer'ı optimize etmenin benchmark'ı hiç etkilemeyeceği anlamına gelir.
2. **PyOpenGL migration gereksizdir.** 100x100 harita (10,000 tile) için viewport culling + pre-rendered surface yeterlidir. OpenGL'in GPU avantajı yalnızca 250x250+ ve çok sayıda animasyonlu varlıkta belirginleşir; bu, mevcut hedefin ötesindedir.
3. **Web/Canvas migration en kötü seçenektir.** Python simülasyon motorunu JS'e yeniden yazmak, benchmark'ı riske atar ve büyük maliyet gerektirir. AEON/Sovereign web'dedir çünkü onlar zaten JS ile yazılmıştır; AI Strategy Arena Python'dur.
4. **Mini WorldBox, Pygame'de WorldBox-benzeri görünümün kanıtıdır.** Pre-rendered surface + subsurface culling + smoothscale zoom, Pygame'de yüksek performans sağlar.

**Öneri:** Pygame'i koru, ancak `ui/` klasörünü yeniden yapılandır: `render/` (camera, view-model, cached terrain, entity sprites, fx) + `ui/` (scoreboard, event log, controls, minimap). Bu, mevcut benchmark motorunu korurken görsel katmanı izole eder.

---

## 11. Organic Borders / Marching Squares Kararı

### Karşılaştırma

| Yöntem | Görsel | Performans | Karmaşıklık | Uygunluk |
|---|---|---|---|---|
| Tile-by-tile (mevcut) | Basit | Düşük (her frame) | Düşük | 20x20 |
| Pre-rendered + culling | Orta | Yüksek | Düşük | 100x100 |
| Jittered borders | Orta-Yüksek | Yüksek | Düşük-Orta | 100x100 |
| Polygon borders | Yüksek | Orta | Orta | 250x250+ |
| Marching Squares | Çok yüksek | Orta | Yüksek | 250x250+ |
| Noise-based terrain | Yüksek | Yüksek | Orta | 100x100+ |

### "MARCHING SQUARES GERÇEKTEN GEREKLİ Mİ?"

**HAYIR, mevcut hedef için gerekli değildir.**

**Gerekçe:**
1. **Amaç en karmaşık çözüm değil, en iyi görsel/performans oranıdır.** Mevcut 20x20 haritada tile-based rendering zaten çalışıyor; hedeflenen 100x100'de pre-rendered surface + viewport culling yeterlidir.
2. **Marching Squares, "organik kıyı şeridi" estetiği için tasarlanmıştır.** AI Strategy Arena'nın haritası çoğunlukla kara + sınırlı su kenarıdır. Kıyı şeridi estetiği kritik değildir.
3. **Marching Squares, her tile'ın 4 komşusunu değerlendirir ve poligon üretir.** Bu, tile-based rendering'den daha karmaşıktır ve 100x100'de gereksizdir.
4. **Daha basit alternatifler yeterlidir:**
   - **Jittered borders:** Sınır çizgilerine hafif rastgele sapma ekleyerek organik görünüm. [Sovereign] biome jitter yaklaşımı.
   - **Noise-based terrain:** Simplex noise ile doğal biyom dağılımı. [Sovereign] `TerrainGenerator.ts`.
   - **Per-tile renk varyasyonu:** `_variant_color` ile deterministik renk farkı. [Mini WorldBox] `world.py`.

**Sonuç:** Marching Squares yalnızca 250x250+ haritalarda ve "organik kıyı şeridi" estetiği birincil hedefse düşünülmelidir. Mevcut hedef için **jittered borders + noise-based terrain + per-tile color variation** en iyi görsel/performans oranını verir.

---

## 12. Map Architecture

### Harita boyutları ve önerilen yaklaşım

| Boyut | Tile sayısı | Yaklaşım | Darboğazlar |
|---|---|---|---|
| 30x30 | 900 | Tile-by-tile (mevcut) | Düşük; her frame çizim kabul edilebilir |
| 100x100 | 10,000 | Pre-rendered surface + viewport culling | Orta; her frame tüm haritayı çizmek FPS düşürür |
| 250x250 | 62,500 | Chunk rendering + cached surfaces | Yüksek; pathfinding ve entity arama maliyeti |
| 500x500 | 250,000 | Chunk rendering + typed-array + spatial grid | Çok yüksek; bellek ve CPU |

### Karşılaştırma

| Yöntem | Açıklama | Avantaj | Dezavantaj |
|---|---|---|---|
| Tile-by-tile | Her tile ayrı `draw.rect` | Basit | Her frame tüm haritayı çizer |
| Pre-rendered surface | Tüm harita bir kez çizilir, `subsurface` ile culling | Hızlı, basit | Terrain değişince yeniden bake |
| Dirty rectangles | Yalnızca değişen bölgeleri yeniden çizer | Çok hızlı | Karmaşık, hata riski |
| Chunk rendering | Harita chunk'lara bölünür, yalnızca görünür chunk'lar çizilir | Ölçeklenebilir | Chunk yönetimi |
| Cached surfaces | Binalar/sınırlar ayrı surface'larda önbelleklenir | Hızlı | Bellek kullanımı |
| Sprite batching | Aynı sprite'ları tek `blit` ile çizer | Çok hızlı | Pygame'de sınırlı destek |

### Önerilen yaklaşım (AI Strategy Arena için)
1. **30x30:** Mevcut tile-by-tile yeterli; yalnızca pre-rendered surface'a geç (kolay kazanım).
2. **100x100:** Pre-rendered terrain surface + `subsurface` viewport culling + `smoothscale` zoom. [Mini WorldBox] yaklaşımı.
3. **250x250+:** Chunk rendering + cached surfaces. [Sovereign] `Renderer.ts` yaklaşımı. Pathfinding için spatial grid.
4. **500x500+:** Typed-array tile veri yapısı + spatial grid. [Sovereign] `WorldMap.ts` yaklaşımı.

**Darboğazlar:**
- **CPU:** Her frame tüm haritayı çizmek (100x100+). → Viewport culling ile çözülür.
- **GPU:** Pygame CPU-based'dir; çok sayıda `draw` çağrısı GPU'yu değil CPU'yu yorar. → Pre-rendered surface ile azaltılır.
- **Memory:** 500x500'de `list[list[Tile]]` (nesne listesi) çok bellek kullanır. → Typed-array'e geçiş.
- **Pathfinding:** A* her çağrıda tüm haritayı tarar. 250x250+ için spatial grid + flow-field gerekir.
- **Entity/animation:** Çok sayıda entity her frame çizilirse FPS düşer. → Viewport culling + sprite batching.

---

## 13. Renderer Architecture

### Önerilen katmanlı mimari (AEON'dan uyarlama)

```
render/                     # Yeni görsel katman (view)
├── camera.py               # Pan/zoom state + koordinat dönüşümleri [Sovereign] Camera.ts
├── view_model.py           # Sim state'ten render için snapshot üretir [AEON] WorldView contract
├── terrain_renderer.py     # Pre-rendered terrain surface + viewport culling [Mini WorldBox]
├── entity_renderer.py      # ArmyEntity/EnvoyEntity sprite rendering [AEON] drawAgents
├── fx.py                   # Particles, rings, floating text, screenshake [AEON] fx.js
├── minimap.py              # Stratejik genel bakış [AEON] drawMinimap
└── renderer.py             # Ana render döngüsü (katmanlı çizim sırası)
```

### Simulation-render ayrımı (kritik)

**Simulation = gerçek oyun state** (otoriter)
- `game/` + `simulation/turn_manager.py` — değişmez, benchmark motoru korunur.

**Renderer = görsel representation** (view)
- `render/` — sim state'i OKUR, asla mutate etmez. [AEON] WorldView contract.

**Animation = visual interpolation** (ayrı katman)
- `render/animation.py` — sim'in discrete tur adımlarını (turn-based) yumuşak görsel hareketlere dönüştürür.
- Örnek: `ArmyEntity` tur başına 1 tile hareket eder (sim). Renderer, iki tur arasında ordunun konumunu interpolasyonla yumuşatır (visual). Sim state'i değişmez.

**Kritik kural:** Renderer/animation, sim state'ini ASLA değiştirmez. Sim, renderer'ın varlığından habersizdir. Bu, benchmark'ın determinizmini korur.

### Katmanlı çizim sırası (AEON'dan uyarlama)
1. Terrain (pre-rendered surface)
2. Territory/borders (ülke renkleri + sınırlar)
3. Buildings (binalar)
4. Roads (yollar)
5. Entities (armies, envoys)
6. Selection/highlight
7. FX (particles, effects)
8. UI overlay (scoreboard, minimap, event log)

### Mevcut klasör yapısını koruma
- `game/`, `simulation/`, `ai/`, `benchmark/` — **değişmez.**
- `ui/` — mevcut scoreboard, event_log, controls korunur.
- Yeni `render/` katmanı eklenir.
- `main.py` — `run_ui` fonksiyonu yeni renderer'ı kullanacak şekilde güncellenir (küçük değişiklik).

---

## 14. Army/Envoy Rendering

### Mevcut sistemler
- `ArmyEntity` (`game/entities.py:38-106`): `x, y, size, destination_x/y, status, path, morale, experience`. `step()` her turda `movement_speed` kadar tile ilerler.
- `EnvoyEntity` (`game/entities.py:109-139`): `x, y, destination_x/y, payload_message, status, path, movement_speed=2`. `step()` her turda 2 tile ilerler.
- `EntityManager` (`game/entities.py:142-436`): `armies: dict[str, ArmyEntity]`, `envoys: dict[str, EnvoyEntity]`.

### Görsel katmanda nasıl gösterilmeli?

**Hareketli birlikler (armies):**
- Her `ArmyEntity` için bir sprite (ülke renginde bayrak/asker simgesi).
- Konum: `world_to_screen(army.x, army.y)`.
- Boyut: `army.size` ile orantılı (daha büyük ordu = daha büyük sprite).
- Durum göstergesi: `MOVING` (hareket animasyonu), `ENGAGED` (savaş), `SIEGING` (kuşatma), `IDLE` (bekleme).

**Sancaklar (banners):**
- Başkentlerde ülke renginde sancak. Mevcut `_draw_capital` (`map_view.py:200-206`) bunu yapar; genişletilebilir.

**Elçiler (envoys):**
- `EnvoyEntity` için küçük bir at/elçi simgesi.
- `payload_message` varsa, elçi üzerinde küçük bir mektup/zarf göstergesi.
- Hedefe varınca (`DELIVERED`) kaybolur.

**Hedef noktaları:**
- `ArmyEntity.destination_x/y` için hedef işareti. [AEON] `drawArmyTarget` — pulsing rally marker.

**Savaş animasyonları:**
- `CombatSystem.resolve_attack` sonucunda patlama/çarpışma efekti. [AEON] `fx.burst()`.
- `resolve_unit_clash` / `resolve_city_siege` sonucunda kuşatma göstergesi.

**Kuşatma göstergeleri:**
- `ArmyStatus.SIEGING` durumunda şehir üzerinde kuşatma halkası. [AEON] `drawSelection` ring.

### Simulation vs Visual state ayrımı (kritik)

**Simulation state (otoriter):**
- `ArmyEntity.x, y` — tur başına discrete adım. `step()` ile güncellenir.

**Visual state (renderer):**
- Renderer, `army.x, y`'yi okur ve ekranda çizer.

**Animation (interpolation):**
- İki tur arasında ordunun konumunu yumuşatmak için renderer, önceki ve sonraki konumu interpolasyonla birleştirir.
- Örnek: Tur N'de ordu (2,3)'te, Tur N+1'de (3,3)'te. Renderer, `t` (0..1) interpolasyon parametresiyle (2+t, 3) konumunda çizer.
- **Sim state'i DEĞİŞMEZ.** Bu, benchmark'ın determinizmini korur.

**Uygulanabilir mimari:**
- `render/entity_renderer.py` — `EntityManager`'ı okur, her entity için sprite çizer.
- `render/animation.py` — interpolasyonlu konum hesaplar (sim state'ini mutate etmeden).
- `render/fx.py` — savaş/kuşatma efektleri üretir (sim state'ini mutate etmeden).

---

## 15. Performance Strategy

### Katmanlı performans stratejisi

| Katman | Teknik | Kaynak |
|---|---|---|
| Terrain | Pre-rendered surface + `subsurface` culling | [Mini WorldBox] |
| Zoom | `smoothscale` (zoom<1) / `scale` (zoom>=1) | [Mini WorldBox] |
| Chunk | Chunk rendering (250x250+) | [Sovereign] |
| Entity | Viewport culling + sprite batching | [AEON] |
| Animation | Interpolation (sim state'ini mutate etmeden) | [AEON] |
| FX | Particle budget cap + quality tier | [AEON] `fx.js` |
| Font | Metin render önbellekleme (cache rendered text) | — |
| Minimap | Cached base + ~2s'de bir rebuild | [AEON] |

### FPS hedefleri
- **30x30:** 60 FPS kolay (mevcut renderer bile).
- **100x100:** 60 FPS (pre-rendered surface + culling ile).
- **250x250:** 30-60 FPS (chunk rendering + cached surfaces).
- **500x500:** 30 FPS (typed-array + spatial grid + chunk).

### Kritik performans notu
- **Tur başına 1s yapay uyku** (`turn_manager.py:119`) renderer'dan bağımsızdır, ancak UI'ın "canlı" hissetmesini engeller. Bu, renderer çalışmasından ÖNCE çözülmelidir (headless/batch modda 0, UI modda yapılandırılabilir).

---

## 16. License Analysis

| Proje | Lisans | Commercial | Modification | Redistribution | Attribution | Copyleft |
|---|---|---|---|---|---|---|
| [Sovereign](https://github.com/CodeByBryant/Sovereign) | MIT | ✅ | ✅ | ✅ | ✅ (lisans metni korunmalı) | ❌ |
| [AEON](https://github.com/lordbasilaiassistant-sudo/aeon) | MIT | ✅ | ✅ | ✅ | ✅ (lisans metni korunmalı) | ❌ |
| [Mini WorldBox](https://github.com/dani931004/worldbox) | MIT (README'de belirtilmiş; repo kökünde LICENSE dosyası doğrulanamadı) | ✅ | ✅ | ✅ | ✅ | ❌ |
| WorldBox | Proprietary (Maxim Karpenko) | ❌ | ❌ | ❌ | — | — |

**Not:** Kod kopyalamıyoruz. Yalnızca mimari desenler ve tasarım yaklaşımları referans alınır. MIT lisanslı projelerden mimari desen öğrenmek serbesttir; ancak doğrudan kod kopyalarsak, lisans metnini korumak gerekir. WorldBox proprietary'dir; kod kopyalanamaz, yalnızca gameplay/UX referansı olarak kullanılır.

---

## 17. Implementation Roadmap

### Phase 1 — Renderer/Camera Temeli
- **Amaç:** Kamera pan/zoom + pre-rendered terrain surface + viewport culling.
- **İlgili sistemler:** `render/camera.py`, `render/terrain_renderer.py`, `render/renderer.py`.
- **Risk:** Düşük. Mevcut `map_view.py`'nin yerini alır, sim'i etkilemez.
- **Teknik zorluk:** Orta. `subsurface` + `smoothscale` zoom.
- **Neden ilk?** WorldBox-benzeri etkileşimin temeli; diğer tüm görsel özellikler buna bağlı.

### Phase 2 — Organic Terrain/Borders
- **Amaç:** Noise-based terrain + jittered borders + per-tile color variation.
- **İlgili sistemler:** `game/map.py` (terrain üretimi), `render/terrain_renderer.py`.
- **Risk:** Orta. `game/map.py`'nin terrain üretimi değişirse, benchmark determinizmi etkilenebilir. **Dikkat:** Terrain üretimi sim'in bir parçasıdır; değişiklik benchmark'ı etkiler. Bu yüzden terrain üretimi ayrı bir modüle taşınmalı veya seed korunmalıdır.
- **Teknik zorluk:** Orta. Simplex noise (Python'da `noise` veya `opensimplex`).
- **Neden bu sırada?** Organik harita, görsel kalitenin en büyük sıçraması.

### Phase 3 — Biome/River
- **Amaç:** Daha fazla biyom + nehirler.
- **İlgili sistemler:** `game/map.py`, `render/terrain_renderer.py`.
- **Risk:** Orta. Nehirler pathfinding'i etkiler (`pathfinding.py`).
- **Teknik zorluk:** Yüksek. Noise zero-crossing nehir üretimi.
- **Neden bu sırada?** Terrain temelinden sonra.

### Phase 4 — Army/Envoy Rendering
- **Amaç:** ArmyEntity/EnvoyEntity sprite rendering + hedef noktaları.
- **İlgili sistemler:** `render/entity_renderer.py`, `render/animation.py`.
- **Risk:** Düşük. Sim'i etkilemez.
- **Teknik zorluk:** Düşük-Orta. Sprite çizimi + interpolasyon.
- **Neden bu sırada?** LLM kararlarının görsel sonucu (ordu hareketi, elçi) kritik izlenebilirlik sağlar.

### Phase 5 — Animation/Effects
- **Amaç:** Savaş/kuşatma animasyonları + particles + screenshake.
- **İlgili sistemler:** `render/fx.py`, `render/animation.py`.
- **Risk:** Düşük.
- **Teknik zorluk:** Orta. Particle sistemi.
- **Neden bu sırada?** Entity rendering'den sonra, görsel geri bildirim ekler.

### Phase 6 — Large-Map Optimization
- **Amaç:** 100x100+ harita desteği (chunk rendering, spatial grid).
- **İlgili sistemler:** `game/map.py`, `game/pathfinding.py`, `render/terrain_renderer.py`.
- **Risk:** Yüksek. Harita boyutu benchmark'ı etkiler.
- **Teknik zorluk:** Yüksek. Typed-array + spatial grid.
- **Neden bu sırada?** Görsel temel tamamlandıktan sonra ölçekleme.

### Phase 7 — 4-8 AI Visualization
- **Amaç:** Çoklu AI ülkesi görselleştirme (renkler, sınırlar, diplomasi).
- **İlgili sistemler:** `render/`, `ui/scoreboard.py`.
- **Risk:** Orta. `DiplomacySystem` çoklu ülke ilişkilerini destekler.
- **Teknik zorluk:** Orta. Renk paleti, sınır çizimi.
- **Neden bu sırada?** Tekil görsel temel tamamlandıktan sonra çoklu ülke.

---

## 18. What NOT To Do

1. **Gereksiz engine migration yapma.** Pygame'i koru. PyOpenGL/Web migration, mevcut simülasyon+benchmark motorunu riske atar.
2. **Simulation/render coupling yapma.** Renderer sim'i asla mutate etmesin. [AEON] WorldView contract.
3. **Her frame tüm map'i çizme.** Pre-rendered surface + viewport culling kullan. [Mini WorldBox].
4. **Aşırı karmaşık sprite sistemi kurma.** Mevcut `pygame.draw` çağrıları yeterli; sprite sheet/atlas gerekmez.
5. **Benchmark'ı renderer'a bağlama.** `--headless` ve `--batch` modları renderer'sız çalışmalı; benchmark sonuçları renderer'dan bağımsız olmalı.
6. **WorldBox'ın tüm mekaniklerini kopyalama.** God powers, fantastik ırklar, gerçek zamanlı bireysel varlık simülasyonu benchmark amacıyla uyumsuz.
7. **Gereksiz dependency ekleme.** Pygame zaten var; `noise`/`opensimplex` (terrain için) ve belki `numpy` (performans için) dışında yeni dependency gerekmez.
8. **Terrain üretimini benchmark'ı bozacak şekilde değiştirme.** Terrain üretimi sim'in parçasıdır; seed korunmalı, determinizm bozulmamalı.
9. **Tur başına 1s uykuyu renderer'la karıştırma.** Bu ayrı bir performans sorunudur; renderer çalışmasından önce çözülmelidir.
10. **Marching Squares'a erken geçme.** Mevcut hedef için gereksiz karmaşıklık.

---

## 19. Final Recommendation

**Mevcut Pygame renderer'ı korunmalı ve optimize edilmelidir.** Renderer değişikliği gerekmez; mevcut simülasyon + benchmark motoru Pygame'den bağımsızdır ve korunmalıdır.

**Önerilen mimari:** AEON'un `src/sim` / `src/render` / `src/game` ayrımını Pygame'e uyarlayarak:
- `game/` + `simulation/` = **otoriter simülasyon** (değişmez, benchmark motoru korunur).
- Yeni `render/` katmanı = **görsel view** (camera, view-model, cached terrain, entity sprites, fx). Sim'i asla mutate etmez.
- `ui/` = mevcut scoreboard, event_log, controls (korunur).
- `main.py` = controller (küçük güncelleme).

**Öncelik sırası:**
1. Kamera pan/zoom + pre-rendered terrain + viewport culling (en büyük görsel/performans kazanımı).
2. Organic terrain/borders (noise + jitter).
3. Army/Envoy rendering (LLM kararlarının görsel sonucu).
4. Animation/effects.
5. Large-map optimization (100x100+).
6. 4-8 AI visualization.

**Kritik ön koşul:** Tur başına 1s yapay uyku (`turn_manager.py:119`) renderer çalışmasından önce çözülmelidir; aksi halde UI "canlı" hissetmez.

**Ana hedef:** LLM'lerin stratejik kararlarını yaşayan, görsel olarak anlaşılır, izlenebilir ve benchmark sonuçlarını destekleyen bir dünya simülasyonuna dönüştürmek. Mevcut simulation + benchmark motorunu korumak birincil önceliktir.

---

*Bu rapor yalnızca araştırma ve analiz içerir. Kod değiştirilmedi, dosya oluşturulmadı/silinmedi, dependency değiştirilmedi, commit/push yapılmadı. Tüm bulgular gerçek kaynak kod ve referans projelerin gerçek source code'u ile doğrulanmıştır.*
