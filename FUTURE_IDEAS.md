# 🏛️ Gelecek Fikirler & Oyun Modları Mimarisi — AI Strategy Arena

Bu doküman, gelecekte sisteme eklenecek özel oyun modlarının ve gelişmiş mimari özelliklerin teknik tasarım notlarını içerir.

---

## 🎮 1. Planlanan Özel Oyun Modları

### 🔹 Mod 1: Klasik Mod (Standard Competitive Benchmark)
- **Kural:** Tüm AI modelleri birebir aynı başlangıç kaynaklarına (Gold: 500, Food: 400, Wood: 150, Stone: 100, Iron: 50), eşit orduya ve simetrik harita başlangıçlarına sahiptir.
- **Amaç:** Saf model zekasını ve stratejik adaptasyon yeteneğini ölçen standart benchmark ortamı.

### 🔹 Mod 2: Krallık / Uygarlık Seçmeli Mod (Asymmetric Factions)
- **Kural:** Her krallığın kendine has pasif güçleri ve başlangıç avantajları vardır:
  * ⚔️ *Demir Lejyonu:* +%20 Ordu gücü, başlangıçta +50 Iron, ucuz kışla üretimi.
  * 🌾 *Bereket Hanedanı:* +%30 Tarım verimi, hızlı nüfus artışı, gıda kıtlığı direnci.
  * 💰 *Altın Kervanı:* Ticaret anlaşmalarından 2 kat altın, liman ve pazar bonusu.
  * 🏰 *Dağ Muhafızları:* +%40 Savunma bonusu, ucuz kale inşası, dağ geçitlerinde görünmezlik.

### 🔹 Mod 3: Haritadan Başlangıç Bölgesi Seçmeli Mod (Regional Spawning)
- **Kural:** Oyuncular simülasyon başlamadan önce haritadaki farklı biyo-zonları seçer:
  * *Kıyı & Nehir Havzası:* Hızlı ticaret ve gıda avantajı, savunması açık.
  * *Dağlık Maden Havzası:* Yüksek demir ve taş üretimi, zorlu arazi savunması.
  * *Yoğun Ormanlar:* Kereste zenginliği ve gizlenme avantajı.

### 🔹 Mod 4: Çok Oyunculu & Takım Senaryoları (Multi-AI Dynamics)
- **Kural:** 4 ila 8 AI arasında dinamik maç tipleri:
  * *Free-For-All (4 AI):* Herkes tek başına, dinamik saldırmazlık ve ihanetler serbest.
  * *2v2 İttifak Savaşı:* İki model takımı ortak vizyon ve kaynak paylaşımıyla savaşır.
  * *3v1 Koalisyon / Boss Savaşı:* Üç küçük krallık devasa bir imparatorluğa karşı birleşir.

### 🔹 Mod 5: Agresif / Kışkırtıcı (Terörist/Anarşist) AI Modu
- **Kural:** Özel bir AI karakteri (Örn: "Kaos Lordu") barış ve paktları sürekli sabote eder, sahte mektuplarla diğer AI'ları birbirine kırdırmaya çalışır ve durmaksızın saldırır.
- **Amaç:** Diğer AI modellerinin **"Ortak Tehdide Karşı Acil Koalisyon Kurma"** ve pragmatik diplomasi yeteneklerini benchmark etmek.

---

## 📊 2. 6 Boyutlu Benchmark ve Model Profilleme
- `Aggressiveness (AGG)`: Saldırganlık ve askeri büyüme oranı.
- `Economic Focus (ECO)`: Üretim, bina inşası ve ticaret odaklılık.
- `Trustworthiness (TRU)`: Paktlara sadakat ve verilen sözü tutma oranı.
- `Adaptability (ADP)`: Tehdit anında strateji değiştirme ve karar çeşitliliği.
- `Deception Index (DEC)`: Aldatma, blöf yapma ve arkadan vurma eğilimi.
- `Long-Term Planning (LTP)`: Teknoloji araştırması ve kalıcı altyapı yatırımları.
