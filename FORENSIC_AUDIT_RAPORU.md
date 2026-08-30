# AI Strategy Arena — Bağımsız Adli (Forensic) Denetim Raporu

**Denetim Tarihi:** 26 Ağustos 2026
**Denetim Türü:** Bağımsız kaynak kodu + runtime doğrulaması
**Denetçi Notu:** Bu rapor, daha önce projeyi inceleyen herhangi bir AI'ın sonuçlarına güvenilmeden, repository'deki gerçek kod, config dosyaları, testler ve canlı runtime davranışı üzerinden bağımsız olarak hazırlanmıştır.

---

## Yönetici Özeti

Bu, **bağımsız** bir adli denetimdir. Önceki hiçbir AI raporuna dayanılmamıştır. Gerçek kaynak kodu, config dosyaları, testler incelenmiş ve OpenAI ile DeepSeek'e **gerçek canlı API çağrıları** dahil runtime deneyleri yapılmıştır.

**Başlıca bulgular:**

1. **LLM API entegrasyonu GERÇEKTİR.** OpenAI (`gpt-4o-mini`) ve DeepSeek (`deepseek-chat`) ile yapılan canlı çağrılar başarılı olmuş, SDK tarafından geçerli token kullanımı (usage) metadata'sı dönmüştür. Her iki model de geçerli, parse edilebilir ve motor tarafından uygulanan kararlar üretmiştir. Canlı testlerde **0 fallback** yaşanmıştır.

2. **LLM kararları oyun motorunu gerçekten etkilemektedir.** Kontrollü EXPAND vs DEFEND testi ölçülebilir şekilde farklı oyun durumları üretmiştir (bölge 100 vs 90, altın 1738 vs 1734).

3. **README'deki "64 passed" iddiası YANLIŞTIR.** Mevcut test paketinde **en az 2 başarısız test** vardır: `test_turn_manager_delivers_diplomatic_message` ve `test_always_economy_vs_balanced` (bu test gerçek bir **dominant strateji hatası** tespit etmiştir — sürekli ECONOMY oynayan bot random'a karşı 5/5 kazanmaktadır).

4. **KRİTİK performans hatası:** Tur döngüsünde **tur başına 1 saniyelik yapay uyku** vardır (`turn_manager.py:119`), bu da her oyunu ~0.93 sn/tur yapmaktadır. 200 turluk bir oyun ~3 dakika sürer. Test paketi 20+ dakika sürmektedir; bu da README'deki "11.60s" iddiasıyla çelişir.

5. **Model adı uyumsuzluğu:** README/yorum "DeepSeek V4 Flash" iddia etmektedir ancak gerçek API model ID'si `deepseek-chat`'tir. "DeepSeek V4 Flash" ve "DeepSeek V4 Pro" kodda **hiçbir yerde** gerçek model ID'si olarak bulunmamaktadır.

---

## 1. Mimari

**Giriş noktası:** `main.py` — `--provider-a/b`, `--batch`, `--turns`, `--seed`, `--headless` parametreli CLI.

**Tur yaşam döngüsü** (`simulation/turn_manager.py:130-168`):
1. `entities.step_all()` — orduları/elçileri hareket ettirir, çatışmaları/kuşatmaları çözer (satır 138)
2. Her aktif ülke için: `_process_agent_turn()` — durum oluştur → prompt → API çağrısı → parse → doğrula → uygula (satır 141-150)
3. Tüm ülkeler için ekonomi güncellemesi (satır 153-156)
4. Bölge sayımı güncellemesi (satır 159)
5. Diplomasi/pakt tick (satır 162-164)
6. Hayatta kalma sayacı (satır 167-168)

**AI karar akışı** (`_process_agent_turn`, `turn_manager.py:170-294`):
- Fog-of-war ile durum oluşturma: `game_state.py:46-147`
- Prompt oluşturma: `prompt_builder.py:55-67`
- Retry mekanizmalı API çağrısı: `turn_manager.py:195-205`
- Parse: `response_parser.py:90-127`
- Doğrulama: `action_validator.py:33-162`
- Uygulama: `_execute_action`, `turn_manager.py:296-385`

**Fallback:** API hatası → DEFEND (`turn_manager.py:206-219`); parse hatası → DEFEND (`response_parser.py:88`); doğrulama hatası → eyleme özel fallback (`action_validator.py:164-169`).

**Baseline botlar:** `baseline_agents.py` — Greedy, Defensive, Economic, Random. Hepsi kural tabanlıdır, API çağrısı yapmaz.

**Benchmark:** `benchmark/` — Elo, round-robin runner, davranışsal profiler.

---

## 2. Gerçek Teknolojiler

| Bileşen | Teknoloji | Kanıt |
|---|---|---|
| Dil | Python 3.12.1 | runtime |
| LLM SDK | `openai` 3.3.1 (AsyncOpenAI) | requirements.txt:8, runtime |
| Doğrulama | Pydantic 2.13.3 | requirements.txt:2 |
| Config | YAML (runtime'da yüklenmiyor) | config/*.yaml |
| Env | python-dotenv | main.py:18-21 |
| UI | Pygame | requirements.txt:1 |
| Async | asyncio | genelinde |

**Önemli:** `config/agents_config.yaml` ve `config/game_config.yaml` dosyaları kod tarafından **hiçbir zaman yüklenmemektedir.** Provider'lar `main.py:51-103` içinde hard-coded'dur. Config dosyaları yalnızca dokümantasyon amaçlıdır.

---

## 3. Provider / Model Doğrulaması

### OpenAI (`ai/openai_provider.py`)
| Özellik | Değer |
|---|---|
| SDK | `AsyncOpenAI` (openai 3.x) |
| Endpoint | varsayılan OpenAI |
| Model ID | `gpt-4o-mini` (satır 11) |
| Env değişkeni | `OPENAI_API_KEY` |
| temperature | 0.3 |
| max_tokens | 256 |
| timeout/retry | provider'da yok (retry TurnManager'da) |
| fallback | DEFEND (TurnManager üzerinden) |

### DeepSeek (`ai/deepseek_provider.py`)
| Özellik | Değer |
|---|---|
| SDK | `AsyncOpenAI` + `base_url=https://api.deepseek.com` (satır 14) |
| Model ID | `deepseek-chat` (satır 15, varsayılan) |
| Env değişkeni | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| temperature | 0.3 |
| max_tokens | 256 |
| timeout/retry | provider'da yok |

### README ile model adı karşılaştırması
- **`gpt-4o-mini`** — README:27 ile kod `openai_provider.py:11` eşleşiyor. **DOĞRULANDI.**
- **`gpt-4o`** (tam sürüm) — **Kodda YOK.** Yalnızca `gpt-4o-mini` mevcut.
- **`deepseek-chat`** — README:28 ve kod `deepseek_provider.py:15`. **DOĞRULANDI.**
- **"DeepSeek V4 Flash"** — yalnızca bir kod yorumunda (`deepseek_provider.py:15`) ve README:28'de geçiyor. **API model ID'si DEĞİLDİR.** Gerçek model `deepseek-chat`'tir.
- **"DeepSeek V4 Pro"** — **Kodda hiçbir yerde YOK.** Doğrulanamadı.

---

## 4. Canlı API Doğrulaması

`.env` dosyasında her iki API anahtarı da mevcuttur (varlığını doğruladım, değerlerini YAZDIRMADIM). Canlı testler her biri 2 tur olacak şekilde çalıştırıldı.

### OpenAI (`gpt-4o-mini`) vs Random
| Çağrı | Gecikme | Prompt token | Completion | Toplam | Eylem |
|---|---|---|---|---|---|
| 1 | 3.84s | 1111 | 59 | 1170 | EXPAND |
| 2 | 2.02s | 1111 | 62 | 1173 | EXPAND |

**Fallback: 0.** API başarılı. Token kullanımı SDK metadata'sından alındı.

### DeepSeek (`deepseek-chat`) vs Random
| Çağrı | Gecikme | Prompt token | Completion | Toplam | Eylem |
|---|---|---|---|---|---|
| 1 | 2.83s | 1126 | 69 | 1195 | EXPAND |
| 2 | 2.05s | 1126 | 69 | 1195 | ECONOMY |

**Fallback: 0.** API başarılı. Token kullanımı SDK metadata'sından alındı.

**Karar: API çağrıları %100 GERÇEKTİR.** Her iki provider da gerçek ağ çağrısı yapmış, geçerli JSON kararlar dönmüş ve bu kararlar motor tarafından parse edilip doğrulanıp uygulanmıştır. Token kullanımı doğrudan SDK yanıt nesnelerinden alınmıştır.

---

## 5. Prompt Adli İncelemesi

LLM'e gönderilen gerçek prompt (durum dökümüyle doğrulandı):

**Mevcut bilgiler:**
- kaynaklar (altın, gıda, odun, taş, demir, nüfuz, nüfus, ordu, bölge, teknoloji, skor) ✓
- bölge ✓
- askeri (ordu) ✓
- diplomasi ✓
- sözleşmeler (active_contracts, pending_proposals) ✓
- görünür düşmanlar (other_players) ✓
- diplomatic_inbox (önceki olaylar) ✓
- tur numarası ✓
- **binalar: doğrudan YOK** (yalnızca `action_notes` bina tiplerinden bahseder, bina envanteri yok)

**Fog-of-war değerlendirmesi:**
- Düşman `known_army: 0` — **doğru şekilde gizlenmiş** (AI_A, AI_B'nin ordusunu göremez). ✓
- Düşman `known_territory: 88` — **kesin bölge sayısı SIZDIRILMIŞTIR.** Model, rakip tile'larını görememesine rağmen rakibin kesin bölge sayısını görür. **ORTA şiddette sızıntı.**
- Düşman altın/gıda/ordu — **SIZDIRILMAMIŞTIR** (other_players yalnızca id, known_army, known_territory, relation_score, relation_status içerir). ✓

**Fog-of-war KISMEN uygulanmıştır.** Ordu gizlenmiştir ancak kesin bölge sayısı açığa çıkmaktadır.

---

## 6. LLM → Parser → Validator → Motor Zinciri

**Kontrollü test (aynı seed, aynı başlangıç durumu):**

| Test | Parse | Validator | Uygulanan |
|---|---|---|---|
| A: EXPAND | geçerli | geçerli | EXPAND |
| B: DEFEND | geçerli | geçerli | DEFEND |

**Tam oyun kanıtı (10 tur, seed=42):**
- EXPAND-vs-DEFEND: bölge_A=100, altın_A=1738
- DEFEND-vs-DEFEND: bölge_A=90, altın_A=1734
- **Bölge farklı (100 vs 90), altın farklı (1738 vs 1734).**

**DOĞRULANDI: LLM kararı oyun durumunu gerçekten etkilemektedir.** Farklı kararlar farklı sonuçlar üretmektedir. Parser → Validator → TurnManager → Motor zinciri doğru çalışmaktadır.

---

## 7. Zamanlama Analizi

**Tur başına ölçülen maliyet: ~0.93s** (5 tur = 4.17s; 10 tur = 9.26s).

**Kök neden:** `turn_manager.py:119`: `delay = max(0.05, 1.0 / self.speed_multiplier)` ve `speed_multiplier = 1.0` → **tur başına 1.0s uyku.** Bu yapay bir gecikmedir, model düşünme süresi değildir.

**API gecikme dökümü (canlı):**
- OpenAI: 3.84s, 2.02s
- DeepSeek: 2.83s, 2.05s

**Önemli:** API gecikmesi yalnızca "model düşünme süresi" DEĞİLDİR. Ağ gidiş-dönüşü + sunucu kuyruğu + inference + token üretimini içerir. Gecikmenin tamamını model bilişine atfetmedim.

**Tur başına 1s uyku, API çağrılarından değil, baskın darboğazdır.** Model hızından bağımsız olarak 200 turluk bir oyun ~3 dakika sürer.

---

## 8. Sıralı / Paralel Analizi

**Kod kanıtı:** `turn_manager.py:141-150` — `for country in active:` döngüsü `await self._process_agent_turn()` çağrısını sıralı yapar. Her ajanın kararı, bir sonraki başlamadan önce beklenir.

**Runtime kanıtı (random-vs-random):**
```
AI_A call#1 end=11.900
AI_B call#1 start=11.908   (AI_A bitişinden sonra)
AI_A call#2 end=12.934
AI_B call#2 start=12.941   (AI_A bitişinden sonra)
```

**DOĞRULANDI: SIRALIDIR.** AI_B, aynı tur içinde AI_A bitmeden başlamaz. Paralelleştirme yoktur. (Talimat gereği paralelleştirme yapılmadı.)

---

## 9. Fallback Analizi

| Senaryo | Ham yanıt | Parser | Validator | Son eylem | Fallback türü |
|---|---|---|---|---|---|
| Geçerli JSON | `{"action":"DEFEND"}` | geçerli | geçerli | DEFEND | yok |
| Geçersiz JSON | `this is not json {broken` | fallback (JSON yok) | — | DEFEND | PARSER FALLBACK |
| Geçersiz eylem | `{"action":"FLY"}` | fallback (doğrulama hatası) | — | DEFEND | PARSER FALLBACK |
| Yetersiz kaynak | `{"action":"EXPAND"}` (altın=10) | geçerli | **reddedildi** (yetersiz altın) | DEFEND | VALIDATION CORRECTION |
| API istisnası | simüle edilmiş kesinti | — | — | DEFEND | API ERROR FALLBACK |

**Üç farklı fallback yolu doğrulandı:**
1. **API ERROR FALLBACK** (`turn_manager.py:206-219`): tüm retry'lar başarısız → DEFEND
2. **PARSER FALLBACK** (`response_parser.py:88`): geçersiz JSON/eylem → DEFEND
3. **VALIDATION CORRECTION** (`action_validator.py:164-169`): geçerli parse ama yasadışı eylem → eyleme özel fallback (çoğunlukla DEFEND/ECONOMY)

---

## 10. Baseline Analizi

**Random, Greedy, Defensive, Economic** — hepsi kural tabanlıdır, API çağrısı yapmaz (`baseline_agents.py` ve `random_provider.py` içinde doğrulandı).

**Determinizm testi (3 tekrar, aynı seed=99):**
- Greedy: **özdeş** ✓
- Defensive: **özdeş** ✓
- Economic: **özdeş** ✓

**BULUNAN HATA:** `RandomProvider` (`random_provider.py:44-55`) BUILD eylemleri için asla `sub_action` üretmez. BUILD seçtiğinde validator onu reddeder (`action_validator.py:126-127` sub_action gerektirir), böylece random bot reddedilen BUILD eylemlerinde tur harcar. Bu, random baseline'ı zayıflatır ve ECONOMY fallback sayısını şişirir.

---

## 11. Benchmark / Elo / Davranışsal Profiler Denetimi

**Elo sistemi** (`elo_system.py`):
- `expected_score`: `1/(1+10^((Rb-Ra)/400))` — **standart FIDE formülü** ✓ (satır 52)
- Güncelleme: `elo += K*(actual-expected)` — **standart** ✓ (satır 91-92)
- K=32 varsayılan ✓ (satır 40)
- Sıfır toplamlı doğrulandı: `new_a + new_b == 2400` (test geçti) ✓
- **DOĞRULANDI: FIDE uyumlu Elo.**

**Round-robin** (`benchmark_runner.py:71`): `itertools.combinations(agent_names, 2)` — doğru ikili üretim. Her maç 2 oyunculudur. `rounds_per_pair=2` varsayılan.

**Davranışsal profiler** (`behavioral_profiler.py`):
- AGG: attacks*3 + recruits*1.5 + expands*1 + kills*10, normalize
- ECO: builds*2.5 + trades*2 + economy*1.2
- TRU: 75 + alliances*8 - betrayals*40
- ADP: eylem dağılımının Shannon entropisi
- DEC: betrayals*45 + koşullu bonus
- LTP: researches*15 + tech*18 + builds*1.5

**Değerlendirme:** 6 boyut GERÇEKTEN oyun olaylarından hesaplanmaktadır (AGG/ECO/TRU/ADP/DEC/LTP kodla eşleşiyor). Ancak **ağırlıklar keyfi sezgiseldir ve bilimsel doğrulaması yoktur.** "6D davranışsal benchmark" **teknik olarak uygulanmıştır ancak bilimsel olarak doğrulanmamıştır.** Skorlar hiçbir gerçek referans değerine karşı ölçülmemiştir.

---

## 12. Test Paketi Denetimi

**Toplanan: 64 test** (`--collect-only` ile doğrulandı).

**Gerçek sonuçlar:**
- 57 geçti (balance dışı)
- **1 BAŞARISIZ:** `test_turn_manager_delivers_diplomatic_message` (elçi 3 turda 15 tile yol alamaz)
- 6 balance testi: 3 geçti (attack, defend, diplomacy), **1 BAŞARISIZ** (`test_always_economy_vs_balanced` — dominant strateji), 1 geçti (diversity), 1 zaman aşımına uğradı (termination)

**Kategoriler:**
- **UNIT TESTS:** action_validator, buildings, combat, contracts, diplomacy, economy, entities, field_combat, profiler, baselines, benchmark — hepsi geçiyor
- **INTEGRATION TESTS:** diplomacy_messages (1 başarısız), balance (1 başarısız)
- **CANLI API TESTLERİ:** **HİÇBİRİ YOK.** Hiçbir test gerçek API çağrısı yapmaz. Tüm testler mock/kural tabanlı provider kullanır.
- **PERFORMANS TESTLERİ:** **HİÇBİRİ YOK.**
- **BENCHMARK TESTLERİ:** test_benchmark.py (Elo + mini turnuva) — geçiyor

**Kritik ayrım:** 64 testin geçmesi "API entegrasyonu doğru" veya "LLM karar kalitesi yüksek" anlamına GELMEZ. Testler yalnızca oyun motoru mekaniklerini ve kural tabanlı botları doğrular. **Hiçbir test gerçek LLM API yolunu kullanmaz.** Geçen testler motor/birim testleridir, LLM entegrasyon testleri değildir.

**README "64 passed in 11.60s" iddiası YANLIŞTIR:**
- En az 2 test başarısızdır
- Paket 20+ dakika sürer (11.6s değil), tur başına 1s uyku yüzünden

---

## 13. README İddia Denetimi

| İddia | Kod Kanıtı | Runtime Kanıtı | Durum |
|---|---|---|---|
| `gpt-4o-mini` varsayılan | openai_provider.py:11 | canlı çağrı gpt-4o-mini kullandı | **DOĞRULANDI** |
| `deepseek-chat` varsayılan | deepseek_provider.py:15 | canlı çağrı deepseek-chat kullandı | **DOĞRULANDI** |
| "DeepSeek V4 Flash" | yalnızca yorum, model ID değil | kullanılmadı | **YANLIŞ/GÜNCEL DEĞİL** (pazarlama adı) |
| "64 passed" testler | 64 toplandı | 2+ başarısız | **YANLIŞ** |
| "64 passed in 11.60s" | — | paket 20+ dk sürüyor | **YANLIŞ** |
| FIDE standart Elo | elo_system.py | formül doğrulandı | **DOĞRULANDI** |
| 6D davranışsal profilleme | behavioral_profiler.py | boyutlar hesaplanıyor | **KISMEN DOĞRULANDI** (sezgisel, doğrulanmamış) |
| Fog of War | game_state.py | ordu gizli, bölge sızdırılmış | **KISMEN DOĞRULANDI** |
| Deterministik baselinelar | baseline_agents.py | 3 tekrar özdeş | **DOĞRULANDI** |
| "100+ simülasyon" (spec) | — | ~0.93s/tur → ~3dk/oyun | **DOĞRULANMADI** (pratik değil) |

---

## 14. Hatalar ve Riskler

| Şiddet | Sorun | Konum |
|---|---|---|
| **KRİTİK** | Tur başına 1s yapay uyku benchmark'ı pratik olmaktan çıkarıyor | turn_manager.py:119 |
| **KRİTİK** | Dominant strateji: sürekli-ECONOMY random'a karşı 5/5 kazanıyor (denge hatası) | test_balance.py:135 |
| **YÜKSEK** | RandomProvider BUILD sub_action üretmiyor → boşa harcanan turlar | random_provider.py:44-55 |
| **YÜKSEK** | README "64 passed" iddiası yanlış (2+ test başarısız) | README.md:4,185 |
| **ORTA** | Fog-of-war kesin düşman bölge sayısını sızdırıyor | game_state.py:81 |
| **ORTA** | Config YAML dosyaları hiç yüklenmiyor (ölü config) | config/*.yaml |
| **ORTA** | Test paketinde canlı API testi yok (CI entegrasyonu doğrulanmamış) | tests/ |
| **DÜŞÜK** | Elçi teslimat testi imkansız 3 turluk teslimat bekliyor | test_diplomacy_messages.py:113 |
| **DÜŞÜK** | "DeepSeek V4 Flash/Pro" adları kodda yok | deepseek_provider.py:15 |
| **DÜŞÜK** | Token kullanımı provider'lar tarafından izlenmiyor (yalnızca SDK seviyesinde) | openai/deepseek_provider.py |

---

## 15. Doğrulanan Bulgular

1. **LLM API çağrıları GERÇEKTİR** — canlı OpenAI & DeepSeek çağrıları SDK token metadata'sıyla başarılı oldu.
2. **LLM kararları motoru etkiler** — EXPAND vs DEFEND farklı oyun durumları üretti.
3. **Sıralı yürütme** — kod ve runtime zaman damgalarıyla doğrulandı.
4. **3 katmanlı fallback** — API hatası, parser, doğrulama düzeltmesi hepsi çalışıyor.
5. **FIDE uyumlu Elo** — formül ve K=32 doğrulandı.
6. **Deterministik baselinelar** — Greedy/Defensive/Economic 3 tekrarda özdeş.
7. **Fog-of-war kısmen uygulanmış** — ordu gizli, bölge sızdırılmış.

---

## 16. Doğrulanmamış İddialar

- **"DeepSeek V4 Flash" / "DeepSeek V4 Pro"** — DOĞRULANMADI (kodda model ID olarak yok)
- **"64 test sistemin çalıştığını kanıtlar"** — DOĞRULANMADI (testler LLM yolunu kapsamıyor; 2 başarısız)
- **"100+ simülasyon/dk"** — DOĞRULANMADI (tur başına 1s bunu imkansız kılıyor)
- **"model X saniye düşündü"** — DOĞRULANMADI (gecikme ≠ düşünme süresi)
- **"6D davranışsal benchmark" bilimsel geçerliliği** — DOĞRULANMADI (sezgisel ağırlıklar)
- **"FIDE benchmark"** — KISMEN DOĞRULANDI (Elo formülü doğru, ancak yayınlanmış FIDE standart sonuç yok)

---

## 17. Önerilen Sonraki Adımlar

1. **Tur başına 1s uykuyu** headless/batch modda kaldırın/azaltın (yapılandırılabilir yapın, benchmark için varsayılan 0).
2. **ECONOMY dominant stratejisini** düzeltin (denge hatası) — test bunu doğru yakalamıştır.
3. **RandomProvider'ı** BUILD sub_action üretecek şekilde düzeltin.
4. **Canlı API entegrasyon testleri** ekleyin (anahtar yoksa atlanacak şekilde işaretleyin) böylece LLM yolu gerçekten test edilir.
5. **Elçi teslimat testini** düzeltin (tur sayısını artırın veya teslimatı mock'layın).
6. **Fog-of-war'da kesin düşman bölgesini** gizleyin (ordu gibi tahmin kullanın).
7. **README'yi** gerçek test durumunu ve doğru model adlarını yansıtacak şekilde güncelleyin.

---

## NİHAİ KARAR

## 🟡 SINIRLAMALARLA DOĞRULANDI (VERIFIED WITH LIMITATIONS)

Temel iddialar **büyük ölçüde doğrulanmıştır**: LLM API entegrasyonu gerçektir (canlı çağrılarla doğrulandı), LLM kararları oyun motorunu gerçekten yönlendirmektedir, fallback sistemi çalışmaktadır, Elo FIDE uyumludur ve baselinelar deterministiktir.

Ancak önemli sınırlamalar mevcuttur:
- README'nin "64 passed" iddiası **yanlıştır** (2+ test başarısız, gerçek bir denge hatası dahil).
- **Tur başına 1s uyku** benchmark'ı pratik olmaktan çıkarır ve performans beklentileriyle çelişir.
- Test paketinde **canlı API testi yoktur**, bu yüzden LLM yolu CI tarafından doğrulanmamıştır.
- Fog-of-war kesin düşman bölgesini sızdırır.
- "DeepSeek V4 Flash/Pro" pazarlama adlarıdır, gerçek API model ID'leri değildir.

Sistem **çalışmaktadır ve API entegrasyonu gerçektir**, ancak dokümantasyon test kapsamını ve performansı abartmaktadır ve benchmark sonuçlarının bilimsel olarak anlamlı kabul edilmesinden önce giderilmesi gereken gerçek denge/performans kusurları vardır.

---

*Bu denetim, yalnızca test amaçlı olarak `scratch/` dizininde adli enstrümantasyon betikleri oluşturmuştur (forensic_audit.py, test_insufficient.py, test_prompt.py). Üretim kodu değiştirilmemiştir. Tüm bulgular kod referansları ve runtime çıktılarıyla desteklenmektedir.*
