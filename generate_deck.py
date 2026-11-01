#!/usr/bin/env python3
"""
TOEIC x COCA 高頻單字 Anki 牌組產生器(樣本版)。

- 以 genanki 建立自訂 note type(看字想義 + 看義想字 兩種卡)。
- 每個單字用 edge-tts 產生真實發音 mp3,嵌入卡片。
- 輸出 .apkg,可直接匯入 Anki。

執行(用上層 .venv):
    /Volumes/workplace/EnglishTraining/.venv/bin/python generate_deck.py

產出:
    build/TOEIC_COCA_sample.apkg
    build/media/<word>.mp3
"""

import asyncio
import hashlib
import os
from pathlib import Path

import edge_tts
import genanki

# ---------------------------------------------------------------------------
# 樣本字表:COCA 高頻 ∩ 多益職場常見。
# 欄位:word, ipa, pos, zh(繁體), en_def, example, topic
# 註:正式版會由 COCA csv(含 rank)載入並擴大;此處為確認格式的樣本。
# ---------------------------------------------------------------------------
WORDS = [
    ("available", "/əˈveɪləbəl/", "adj.", "可取得的;有空的",
     "able to be used or obtained; not busy",
     "The manager is not available until after the meeting.", "Office"),
    ("schedule", "/ˈskedʒuːl/", "n./v.", "時程表;排定",
     "a plan of when things will happen; to arrange a time",
     "We need to schedule the delivery for next Monday.", "Logistics"),
    ("budget", "/ˈbʌdʒɪt/", "n./v.", "預算;編列預算",
     "the amount of money available for a purpose",
     "The marketing budget was cut by ten percent this quarter.", "Finance"),
    ("invoice", "/ˈɪnvɔɪs/", "n./v.", "發票;請款單",
     "a document listing goods sold and the price owed",
     "Please send the invoice to the accounting department.", "Finance"),
    ("deadline", "/ˈdedlaɪn/", "n.", "截止期限",
     "the latest time by which something must be finished",
     "The team worked overtime to meet the deadline.", "Project"),
    ("negotiate", "/nɪˈɡoʊʃieɪt/", "v.", "協商;談判",
     "to reach an agreement through discussion",
     "They negotiated a better price with the supplier.", "Business"),
    ("colleague", "/ˈkɑːliːɡ/", "n.", "同事",
     "a person you work with",
     "I asked a colleague to cover my shift.", "Office"),
    ("efficient", "/ɪˈfɪʃənt/", "adj.", "有效率的",
     "working well without wasting time or resources",
     "The new software made the process more efficient.", "Business"),
    ("purchase", "/ˈpɜːrtʃəs/", "n./v.", "購買",
     "to buy something; the act of buying",
     "The company purchased new equipment for the lab.", "Finance"),
    ("warehouse", "/ˈwerhaʊs/", "n.", "倉庫",
     "a large building for storing goods",
     "The goods are stored in the warehouse near the port.", "Logistics"),
    ("apply", "/əˈplaɪ/", "v.", "申請;應用",
     "to make a formal request; to put into use",
     "You can apply for the position online.", "HR"),
    ("confirm", "/kənˈfɜːrm/", "v.", "確認",
     "to state that something is true or definite",
     "Please confirm your attendance by Friday.", "Office"),
    ("revenue", "/ˈrevənuː/", "n.", "營收;收益",
     "the money a company receives from its business",
     "Annual revenue grew by fifteen percent.", "Finance"),
    ("recruit", "/rɪˈkruːt/", "v./n.", "招募;新進人員",
     "to find new people to work for a company",
     "The firm is recruiting engineers for the new project.", "HR"),
    ("shipment", "/ˈʃɪpmənt/", "n.", "貨運;一批貨",
     "a quantity of goods that are sent together",
     "The shipment will arrive at the dock on Tuesday.", "Logistics"),
    ("approve", "/əˈpruːv/", "v.", "核准;贊成",
     "to officially agree to or accept something",
     "The board approved the new expansion plan.", "Business"),
    ("client", "/ˈklaɪənt/", "n.", "客戶",
     "a person or company that buys services",
     "Our biggest client renewed the contract.", "Business"),
    ("expense", "/ɪkˈspens/", "n.", "費用;支出",
     "the money spent on something",
     "Travel expenses must be reported each month.", "Finance"),
    ("attend", "/əˈtend/", "v.", "出席;參加",
     "to be present at an event",
     "All staff must attend the safety training.", "Office"),
    ("deliver", "/dɪˈlɪvər/", "v.", "遞送;交付",
     "to take goods to a place; to produce a result",
     "The courier will deliver the package by noon.", "Logistics"),
    ("contract", "/ˈkɑːntrækt/", "n.", "合約",
     "a formal written agreement",
     "Both parties signed the contract yesterday.", "Business"),
    ("refund", "/ˈriːfʌnd/", "n./v.", "退款;退還",
     "money paid back; to pay money back",
     "The store offered a full refund for the faulty item.", "Finance"),
    ("estimate", "/ˈestɪmeɪt/", "n./v.", "估計;估價",
     "a rough calculation of value or cost",
     "Can you give me an estimate for the repair?", "Business"),
    ("supplier", "/səˈplaɪər/", "n.", "供應商",
     "a company that provides goods or services",
     "We switched to a cheaper supplier last year.", "Logistics"),
]

VOICE = "en-US-AriaNeural"

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
MEDIA = BUILD / "media"


def stable_id(text: str) -> int:
    """由字串產生穩定的 31-bit id(genanki 的 model/deck id 需穩定才不會每次匯入都新建)。"""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (1 << 31)


MODEL = genanki.Model(
    stable_id("TOEIC_COCA_model_v1"),
    "TOEIC x COCA 單字",
    fields=[
        {"name": "Word"},
        {"name": "IPA"},
        {"name": "POS"},
        {"name": "Chinese"},
        {"name": "EnglishDef"},
        {"name": "Example"},
        {"name": "Topic"},
        {"name": "Audio"},
    ],
    templates=[
        {
            "name": "看字想義 (Recognition)",
            "qfmt": """
<div class="word">{{Word}}</div>
<div class="ipa">{{IPA}}</div>
<div class="audio">{{Audio}}</div>
""",
            "afmt": """
{{FrontSide}}
<hr id="answer">
<div class="pos">{{POS}}</div>
<div class="zh">{{Chinese}}</div>
<div class="endef">{{EnglishDef}}</div>
<div class="example">{{Example}}</div>
<div class="topic">#{{Topic}}</div>
""",
        },
        {
            "name": "看義想字 (Recall)",
            "qfmt": """
<div class="zh">{{Chinese}}</div>
<div class="endef">{{EnglishDef}}</div>
<div class="pos">{{POS}}</div>
<div class="topic">#{{Topic}}</div>
""",
            "afmt": """
{{FrontSide}}
<hr id="answer">
<div class="word">{{Word}}</div>
<div class="ipa">{{IPA}}</div>
<div class="audio">{{Audio}}</div>
<div class="example">{{Example}}</div>
""",
        },
    ],
    css="""
.card { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
        font-size: 20px; text-align: center; color: #1a1a1a; background: #fafafa; }
.word { font-size: 40px; font-weight: 700; color: #0b3d91; margin: 8px 0; }
.ipa  { font-size: 22px; color: #555; margin-bottom: 6px; }
.pos  { font-size: 16px; color: #8a6d00; font-style: italic; }
.zh   { font-size: 30px; font-weight: 600; margin: 10px 0; }
.endef { font-size: 18px; color: #333; margin: 6px 16px; }
.example { font-size: 18px; color: #2b6f3a; margin: 12px 16px; }
.topic { font-size: 14px; color: #888; margin-top: 10px; }
hr#answer { border: none; border-top: 1px solid #ccc; margin: 14px 0; }
""",
)


async def synth(word: str, path: Path):
    """用 edge-tts 產生單字發音 mp3。"""
    if path.exists():
        return
    tts = edge_tts.Communicate(word, VOICE)
    await tts.save(str(path))


async def build_audio():
    MEDIA.mkdir(parents=True, exist_ok=True)
    tasks = []
    for word, *_ in WORDS:
        tasks.append(synth(word, MEDIA / f"{word}.mp3"))
    await asyncio.gather(*tasks)


def build_deck():
    deck = genanki.Deck(stable_id("TOEIC_COCA_deck_v1"),
                        "TOEIC x COCA 高頻單字(樣本)")
    media_files = []
    for word, ipa, pos, zh, en_def, example, topic in WORDS:
        mp3 = MEDIA / f"{word}.mp3"
        audio_field = f"[sound:{word}.mp3]" if mp3.exists() else ""
        if mp3.exists():
            media_files.append(str(mp3))
        note = genanki.Note(
            model=MODEL,
            fields=[word, ipa, pos, zh, en_def, example, topic, audio_field],
            tags=["TOEIC", "COCA", topic],
        )
        deck.add_note(note)

    pkg = genanki.Package(deck)
    pkg.media_files = media_files
    out = BUILD / "TOEIC_COCA_sample.apkg"
    pkg.write_to_file(str(out))
    return out, len(WORDS), len(media_files)


def main():
    BUILD.mkdir(exist_ok=True)
    print(f"Synthesizing audio for {len(WORDS)} words...")
    asyncio.run(build_audio())
    missing = [w for w, *_ in WORDS if not (MEDIA / f"{w}.mp3").exists()]
    if missing:
        print(f"⚠️  audio missing for: {missing}")
    out, n_words, n_media = build_deck()
    print(f"✅ Deck: {out}")
    print(f"   words={n_words}  audio={n_media}")


if __name__ == "__main__":
    main()
