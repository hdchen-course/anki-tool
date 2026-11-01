# COCA 10000 — TOEIC × COCA 高頻 10,000 單字 Anki 牌組

自學用、**英文卡面(無中文)**、字義對齊(sense-aligned)的 TOEIC 單字 Anki 牌組。
字集取自 **Paul Nation BNC/COCA Word Family Lists** 的 1k–10k 詞族(10,000 個),
音標/搭配/例句候選取自 **BNC_COCA_EN2CN**(只取英文事實),英英定義與例句經人工 +
對抗式審查定稿,每段文字(headword + 2 句例句)以 **edge-tts** 產生真實 mp3 發音。

- **10,000 張卡**,依頻率分 **10 個 Band 子組**(Band 01 = 最高頻 1–1000 … Band 10 = 9001–10000)。
- 牌組名稱 `COCA 10000`,子組 `COCA 10000::Band 01 (0001-1000)` … `Band 10 (9001-10000)`。
- 成品 `.apkg` 與音檔**不進 git**(見下「為何不進 git」),用本倉庫的工具即可重新產生。

---

## 卡片設計(2026-11-01 定案)

單向卡(看定義 → 回想單字),每張鎖定單一字義:

| 面 | 內容 |
|---|---|
| **正面** | 英英定義(粗體置中)+ 兩句**挖空**例句(headword 以 teal 底線空格取代)→ 回想單字 |
| **背面** | 單字(teal 大字)+ US/UK 音標 + 兩句完整例句(答案字 teal 粗體)+ 發音 |

- 配色:暖米白(淺)/ 暖炭(深,`.nightMode` 跟隨 Anki 日夜)+ teal 強調 + 下半漸層。
- 發音:Anki 原生 `[sound:]` 播放鈕(已上 teal 色),實機可播、跨平台穩。
- 超短單字音(a / the / to / of…)edge-tts 單獨唸會吞音/弱讀成「呃」;`build_cards.py`
  對「單一 token 且長度 ≤ 4」的 headword 以雙引號孤立送入 TTS(`SHORT_WORD_MAX`),
  強制完整字典讀音。只改 TTS 輸入字串,檔名仍 = 原字 hash(引用/去重/驗證不變)。
  既有音檔可用 `regen_short_word_audio.py` 原地補修(不必全量重生)。
- (選用)音文稽核:裝 `faster-whisper` 後可把每個 mp3 轉文字與卡片文字比對,
  自動抓出「音檔配錯/唸錯」的卡(ASR round-trip),不需逐張試聽。
- 視覺設計經眼科(對比 AA、抗光暈)、美術、空間版面三位 reviewer 審過。
- 設計預覽(含 base64 音檔,可直接雙擊開):`card_preview.html`。

**核心鐵律 R6**:definition 與兩句例句必須全部對齊**同一字義**(一字多義只收主義)。

---

## 工具與資源

```
Anki/
├── build_full_apkg.py       # ★ 產全量牌組 → build/COCA_10000.apkg(10,000 卡、10 Band 子組)
├── build_preview_apkg.py    # 產預覽牌組 → build/preview_10x2.apkg(10 組×2 字 = 20 卡)
├── build_cards.py           # 為 authored 記錄產 edge-tts 音檔 + 寫音檔對映 + 防漂移 verify
├── verify_deck.py           # DONE-GATE 驗證(schema / 音檔防漂移 / rank 覆蓋 / apkg 讀回)
├── card_preview.html        # 卡片設計預覽(正/背面、淺/深、漸層)
├── data/
│   ├── cards.jsonl                   # ★ 核心資源:全牌組 master(10,000 行)
│   ├── skip_ranks.json               # 永久排除的 rank + 理由
│   ├── coca10k_raw.jsonl             # Pass 1 事實層
│   ├── coca_bnc_wordfamilies.jsonl   # Nation 25k 詞族解析
│   ├── bnccoca_wordfamilies_25k.xlsx # Nation 權威原始表
│   └── batch_* / cards_*             # 各批 writer 輸入/定稿(可重現軌跡)
├── ANKI_COCA_BUILD_SPEC.md  # 建置規範
├── DECISION_LEDGER.md       # 270 字增刪/回填決策紀錄
└── (build/ audio/ downloads/ 不進 git — 見下)
```

`data/cards.jsonl` 每列 schema(摘要):
`rank, level, band, headword, pos, ipa_us, ipa_uk, sense_key, definition,`
`collocations:[{collocation,example}×2], audio_word, audio_examples:[,], freq_order(1-10000), group(1-10)`

---

## 重現步驟(用專案 venv)

venv:`/Volumes/workplace/EnglishTraining/.venv`(已裝 `edge-tts`、`genanki`、`anki`)。

```bash
cd /Volumes/workplace/EnglishTraining/Anki
V=/Volumes/workplace/EnglishTraining/.venv/bin/python

# 1) 由 cards.jsonl 重新產生全部音檔(冪等:已存在且非空則略過)
#    檔名 = sha1(voice|正規化文字)[:16].mp3,內容定址;約 29,921 個 mp3 / ~480MB
$V build_cards.py data/cards.jsonl /tmp/_cards_regen.jsonl audio   # 補齊 audio/,輸出檔可丟棄

# 2) 產全量牌組(嵌入 media)→ build/COCA_10000.apkg(~490MB)
$V build_full_apkg.py

# (可選)產預覽牌組 20 卡 → build/preview_10x2.apkg
$V build_preview_apkg.py

# 3) 驗證
$V verify_deck.py
```

匯入:桌面 `File → Import → build/COCA_10000.apkg`;手機用「檔案 App → 分享到
AnkiMobile/AnkiDroid」(~490MB,手機匯入會跑一下)。每日新卡上限用 Anki 內建(預設 20)。

---

## 為何 apkg / 音檔不進 git

- `build/*.apkg` ~490MB、`audio/` ~480MB 都是**產物/可重生資源**,放 git 不切實際。
- 兩者都能由本倉庫工具 100% 重生:`cards.jsonl`(事實)→ `build_cards.py`(音檔,edge-tts
  內容定址、冪等)→ `build_full_apkg.py`(apkg)。
- 因此 git 只保留**工具 + 資料(cards.jsonl 等)+ 說明**;要成品就跑上面三步。

---

## 授權與合規

- 字表/頻率/音標/英文片語/例句屬事實或 Nation 公開教育資源。
- EN2CN 的中文譯文源自有道 API(商業)→ 本牌組**完全不使用其中文**(英文卡面),無授權風險;**僅限使用者自用、不散佈**。
- 音檔為 edge-tts 本機產生。
