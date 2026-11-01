# ANKI_COCA_BUILD_SPEC — 多益 COCA 高頻單字 Anki 牌組(建置規範草稿)

狀態:**DRAFT**(spec-first;未達 content_audit 連續 clean + 紅隊 + 使用者確認前,不得進實作)
最後更新:2026-10-31(台北)
單一事實來源:本檔。要改規範改這裡,不得在實作碼偷放寬。

---

## 0. 目標與使用者

- 使用者自學多益單字,想用 **COCA / BNC-COCA 高頻字**。
- 規模目標:**10,000 個 headword(詞族)**,每字 collocation 例句(目標約 2 句 → ~20,000 句)。
- 主要使用情境:**手機(AnkiMobile / AnkiDroid)為主**,桌面次之;裝置通常有網路。
- 產物:可直接匯入 Anki 的 `.apkg`,並附可重現的完整原始碼 bundle(house 鐵律)。

## 1. 內容鐵律(不可違反)

- R1 **正確性第一**:教錯害人。任何釋義/例句/音檔錯誤皆為 ship-block。
- R2 **全繁體、零簡體、零大陸用語**(台灣用語)。所有中文入庫前必過 `s2twp` + 人工複核 + 簡體掃描 gate。
- R3 **可重現**:每筆事實(字、rank、音標、釋義、例句)須可由腳本從來源重跑產生;禁造假。
- R4 **音檔必為真實檔、可播**(若採預存路線)。
- R5 自用範圍;採用的第三方資料僅限自用、不散佈(見 §3 授權)。

## 2. 資料來源(全部實測可取、已驗證 2026-10-31)

| 用途 | 來源 | 驗證 |
|---|---|---|
| 字 + 頻率帶(1k–25k 詞族) | **Paul Nation BNC/COCA Word Family Lists**(eapfoundation.com xlsx) | 已下載:25,002 詞族 / 25 帶,每帶 1000 |
| 目標字集 | 取 **band 1k–10k = 10,000 headword** | 已存 `data/coca_bnc_wordfamilies.jsonl` |
| us/uk 音標 + 片語(collocation)+ 例句(**候選**) | **changhongzi/BNC_COCA_EN2CN**(per-word JSON,CDN) | 76,125 字;對 10k headword **覆蓋率 100%、0 缺漏**;**只取英文事實(IPA/片語/例句),不取其中文** |
| **英英 definition(必備,學習者友善)** | **MW Learner's**(金鑰、自用)或 Wiktionary(CC BY-SA) | EN2CN 無英英定義,一定要此來源 |
| 既有繁中+例句(top ~5k,可交叉比對) | repo `english-vocab-deploy/vocab_data_coca_L1–L10.js`(4,953 字) | 已盤點 |

- 已存檔:`data/bnccoca_wordfamilies_25k.xlsx`(權威原始)、`data/coca_bnc_wordfamilies.jsonl`(解析)。

## 3. 授權與合規

- EN2CN 的中文譯文源自有道詞典 API(商業、非開放)→ **僅限使用者自用,不散佈**(使用者已確認自用)。
- BNC/COCA 字表與頻率、音標、英文片語/例句屬事實或 Nation 公開教育資源,使用無虞。
- **散佈版**(若未來要分享)必須改走可散佈來源(Wiktionary/WordNet 英英 + 自製繁中),並移除有道來源內容。此為兩種建置模式,spec 預設 = **自用模式**。

## 4. 內容產製管線(per headword)

1. 以 headword 向 EN2CN 取 JSON(本地快取,避免重複抓)。
2. 擷取:`frequency`、`list`(帶)、`usPhone`/`ukPhone`、`translations`、`phrs`(collocation)、`sentences`。
3. 中文全部過 **OpenCC `s2twp`**(簡→繁台灣用語)。
4. **人工複核(team,見 §8)**:繁體/用語、釋義正確性、collocation 自然度與多益職場語域;例句語域不符者篩除或改寫。
5. rank 欄位 = Nation 帶 + EN2CN frequency(可驗)。
6. 產出乾淨 `cards.jsonl`(單一事實來源),再由 builder 生 `.apkg`。

- collocation 不足或語域不符時:以開放語料(.venv 可跑)算 PMI 搭配詞補,仍須人工複核;**禁造假**。

## 5. 卡片設計(已採用使用者設計 2026-10-31,英文四欄、無中文)

卡面四要素:
1. **單字**(headword)
2. **音標**(IPA;us 為主,uk 待定是否並列)
3. **definition**(英英,學習者友善:用簡單字,TOEIC 600–750 可讀)
4. **兩句 collocation 例句**(展示該字最常見搭配)

**核心鐵律 R6 — 字義對齊(sense alignment)**:每張卡鎖定**單一字義**(取最高頻/最多益相關的義項);definition 與兩句 collocation 例句**必須全部對齊同一字義**。一字多義強的字:只收主義,或拆成多張卡(一義一卡)。reviewer 必檢。
- **不放中文**(英文學英文 R14);因此不使用 EN2CN 的中文/有道內容 → 無簡體/授權風險。
- definition 來源:MW Learner's(控制定義詞彙,自用金鑰)或 Wiktionary 淺義項;須驗可讀性。EN2CN 無英英定義。
- 卡型(暫定):看字→義、看義→字 雙向;例句 cloze 待定。

## 6. 音檔架構(**ADR 待手機實測後定案**)

三案(皆可得自然 neural 音;技術結論已於研究階段用實測釘定):

| 方案 | 牌組大小(10k字+20k例句) | 手機 | 離線 | 基礎設施 |
|---|---|---|---|---|
| A 預存 edge-tts → Opus 24k/16k | ~160–300 MB | ✅ | ✅ | 無 |
| B 卡片即時 + 自架 Cloudflare Worker relay | ~0 | ✅(需網) | ❌ | 要自架 relay |
| C Piper 離線 neural(卡片內 ONNX) | 小(模型數 MB) | ✅ | ✅ | 無 |

- 已實測事實:卡片 webview **無法直連** edge-tts(Bing 檢查 Edge UA + token;瀏覽器禁改 UA → 必經 relay)。
- 預存採防漂移:檔名=`hash(正規化文字+語音)`,冪等重產,附 verify gate(現值文字 hash 無對應音檔 / 孤兒檔 → FAIL)。
- **決策(2026-10-31)**:採 **A 預存**為基準 — 音檔於 **Pass 2 定稿時與內容一起產生**(每字:headword + 2 句例句 = 3 檔),edge-tts 產出。data **必須記錄每段文字對應的音檔名**(見 §7 `audio_word`/`audio_examples`);檔名為內容定址,文字變→重產→更新對映。B/C 日後若要仍可加,但儲存基準走 A。
- 格式:edge-tts 原生 mp3;Opus 瘦身需 ffmpeg(本機未裝,之後補裝再轉)。

## 7. 資料 schema(`cards.jsonl` 每列)

```
{ "rank": int, "band": "1k..10k", "headword": str, "pos": str,
  "ipa_us": str, "ipa_uk": str|null,
  "sense_key": str,                      // 鎖定的字義標識
  "definition": str,                     // 英英、學習者友善、對齊 sense_key
  "collocations": [                      // 恰 2 句,全部對齊 sense_key
    {"collocation": str, "example": str},
    {"collocation": str, "example": str}
  ],
  "audio_word": str|null, "audio_examples": [str|null, str|null],
  "source": {"wordlist":"nation-bnc-coca","ipa":"en2cn","def":"mw-learner|wiktionary","rev":"<reviewer>"} }
```
(無 chinese 欄位 — 英文學英文。)

## 8. 團隊(roles-first,不 solo)

- WRITERS(產資料 + 驗腳本)。
- REVIEW lenses:native English、繁中/用語複核、learning-neuroscience(排序/記憶)、PM(讀者旅程)。
- 獨立對抗式 reviewer。

## 9. DONE-GATE(全部通過才算完成)

1. content_audit 跑到 **連續 clean**(spec 內容先;實作再各檔 clean)。
2. **簡體掃描 gate** 全綠(零簡體/零大陸用語)。
3. 每筆事實可重現(repro:腳本重跑比對)。
4. 音檔(若採 A)存在且可播 gate;防漂移 verify gate 綠。
5. `.apkg` 從乾淨環境可匯入、卡片正常渲染發音。
6. **完整可執行原始碼 bundle**(抓取→轉換→build 腳本 + README + 驗證指令)可下載並從乾淨解包跑通。

## 10. 流程(spec-first,不可跳)

(1) 本 spec → (2) content_audit 連續 clean → (3) 紅隊證明規範不可繞過 → (4) 使用者確認 → (5) 實作(一檔一檔,每檔 clean)→ (6) 全牌組 DONE-GATE。

## 11. 待拍板清單(阻擋定案的使用者決策)

- [x] 卡片設計:**英文四欄(單字 / 音標 / 英英 def / 2 collocation 例句),無中文,sense-aligned**(§5)
- [x] 音標:**us + uk 並列**
- [x] 字數/分級:**10,000,按頻率分 10 級**(L1=1k 最高頻 … L10=10k,每級約 1000);Pass 1 事實層已建 `data/coca10k_raw.jsonl`
- [x] definition:抓得到就用、抓不到依例句生成,**但必檢 def↔例句吻合(R6)**
- [ ] definition 來源偏好:MW Learner's(金鑰、自用)優先 vs Wiktionary(可散佈)
- [ ] 一字多義政策:只收主義 vs 一義一卡(多卡)
- [ ] 音檔:A 預存 Opus / B relay 即時 / C Piper(§6,建議先做測試卡手機實測)

## 12. 進度

- **Pass 1(事實層)完成 2026-10-31**:`data/coca10k_raw.jsonl` — 10,000 字、10 頻率級、us+uk 音標、collocation+例句候選(含雜訊待 Pass 2 過濾:全大寫片名 817、CJK 雜訊 ~0%;85% 的字已有 ≥2 乾淨 collocation + ≥2 乾淨例句)。
- **Pass 2(撰寫層,進行中)**:每字選字義 + def + 2 句 sense-aligned collocation 例句 + edge-tts 音檔(word+2 例句)+ 對映。流水線 = writer agent → schema gate → 獨立對抗 reviewer → fixer → build_cards 音檔 → 併 master。
  - **✅ Pass 2 全部完成 2026-11-01**:**全 10,000 ranks 處理完畢 = 9,734 張卡 + 266 skip**(0 uncovered)。`data/cards.jsonl`(9,734 行)+ `audio/`(29,130 mp3,**0 missing / 0 orphan**,466.1 MB)。全牌組複驗:0 badlen、0 CJK、0 sense_key mismatch、0 dup rank、max_rank=10000。每批乾淨率 82–98%,對抗抓到的 R6/literal-figurative 分裂/詞形/IPA/POS/dialect(US/UK 歧義+英式拼字+UK-only 詞)/敏感/事實錯誤缺失全數修掉。
  - 管線(已跑完 pilot + L3_001–008 + 批次 001–101):每波 3 批×100 字並行(writer→schema gate→3 獨立對抗 reviewer→fixer 套用+DROP→schema 複驗→英式拼字掃描→build_cards 音檔→併 master→防漂移 verify)。**去重以 rank 為鍵**。**artifact/低值/敏感/slang/技術/古語/UK-only/explicit/proper-noun rank 記 `data/skip_ranks.json` 永久排除**(最終 266 個)。
  - **✅ DONE-GATE PASS 2026-11-01**:`verify_deck.py` 全綠 — master **9,730 卡**(schema_errs=0 / MISSING=0 / ORPHAN=0),coverage carded(9,730)+skip(270)=10,000、uncovered=0、dup_rank=0、carded∩skip=0,`.apkg` 用官方 anki library 讀回 **9,730 notes / 19,460 cards(雙向)/ 29,118 media** 相符。成品 `build/TOEIC_COCA_10k.apkg`(~475MB)。
    - **DONE-GATE 自查抓到並修正**(gate 未弱化):早期批次(美式規則前)殘留 32 個英式 headword + ~271 卡文字英式拼字 + 2 個重複搭配 + 4 個「英式→美式會與既有卡撞號」→ 28 個 headword 轉美式(連 sense_key/IPA/音檔重產)、4 撞號 drop(skip→270)、dup 搭配補成兩種句位、英式拼字全掃歸零;並修掉背景重建迴圈「平行控制缺陷導致部分 cards_NNN stale」的坑(改序列可靠重建)。
    - ✅ **code-download bundle**:`downloads/anki_coca_10k_src.zip`(8.9MB,317 檔:腳本 + README + SPEC + 全 data/,排除 audio/ 與 build/ 產物,音檔由 `build_cards.py` 經 edge-tts 可重產)。**clean-unpack 冒煙測試通過**:解到 temp → `build_cards`(pilot 10 卡→30 mp3,0 missing/orphan)→ `build_apkg`(產出 .apkg)→ 對 bundle 內 master 跑 schema/英式/CJK/coverage 全 0 錯。
    - **狀態:全 10k 完成並通過 DONE-GATE,等 HD 最終確認。** 成品:`build/TOEIC_COCA_10k.apkg`(9,730 卡雙向、英文四欄、sense-aligned、us+uk IPA、29,118 真實 edge-tts 音檔)+ 可重跑原始碼 bundle。
