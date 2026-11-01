#!/usr/bin/env python3
"""
全牌組 .apkg 生成器(英文四欄、無中文、sense-aligned)。

讀 data/cards.jsonl(Pass 2 定稿,每列一張卡,schema 見 ANKI_COCA_BUILD_SPEC §7)
+ audio/ 內預先以 edge-tts 產生的 mp3(內容定址檔名,build_cards.py 寫入對映),
產出可直接匯入 Anki / AnkiMobile / AnkiDroid 的 .apkg。

卡面(使用者設計,英文四欄):
  正面(看字→義):headword + IPA(us/uk 並列)+ 單字發音
  背面:英英 definition(對齊單一字義)+ 兩句 collocation 例句(各附發音)
雙向另收「看義→字」卡型。

執行(用上層 .venv):
  /Volumes/workplace/EnglishTraining/.venv/bin/python build_apkg.py \
      [data/cards.jsonl] [audio] [build/TOEIC_COCA_10k.apkg]

產出:build/TOEIC_COCA_10k.apkg(含 media)。
"""
import hashlib
import json
import os
import sys

import genanki

ROOT = os.path.dirname(os.path.abspath(__file__))


def stable_id(text: str) -> int:
    """由字串產生穩定的 31-bit id(model/deck id 需穩定,重匯入才不會新建牌組)。"""
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16) % (1 << 31)


MODEL = genanki.Model(
    stable_id("TOEIC_COCA_10k_model_v1"),
    "TOEIC x COCA 10k (EN-only, sense-aligned)",
    fields=[
        {"name": "Headword"},
        {"name": "IPA_US"},
        {"name": "IPA_UK"},
        {"name": "POS"},
        {"name": "Definition"},
        {"name": "Example1"},
        {"name": "Example2"},
        {"name": "AudioWord"},
        {"name": "AudioEx1"},
        {"name": "AudioEx2"},
        {"name": "Rank"},
        {"name": "Level"},
    ],
    templates=[
        {
            "name": "Recognition (word -> meaning)",
            "qfmt": """
<div class="word">{{Headword}}</div>
<div class="ipa">US {{IPA_US}}　·　UK {{IPA_UK}}</div>
<div class="audio">{{AudioWord}}</div>
""",
            "afmt": """
{{FrontSide}}
<hr id="answer">
<div class="pos">{{POS}}</div>
<div class="def">{{Definition}}</div>
<div class="ex">{{Example1}} {{AudioEx1}}</div>
<div class="ex">{{Example2}} {{AudioEx2}}</div>
<div class="meta">#{{Level}} · rank {{Rank}}</div>
""",
        },
        {
            "name": "Recall (meaning -> word)",
            "qfmt": """
<div class="def">{{Definition}}</div>
<div class="ex">{{Example1}}</div>
<div class="ex">{{Example2}}</div>
<div class="pos">{{POS}}</div>
""",
            "afmt": """
{{FrontSide}}
<hr id="answer">
<div class="word">{{Headword}}</div>
<div class="ipa">US {{IPA_US}}　·　UK {{IPA_UK}}</div>
<div class="audio">{{AudioWord}} {{AudioEx1}} {{AudioEx2}}</div>
<div class="meta">#{{Level}} · rank {{Rank}}</div>
""",
        },
    ],
    css="""
.card { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
        font-size: 20px; text-align: center; color: #1a1a1a; background: #fafafa;
        padding: 14px; }
.word { font-size: 40px; font-weight: 700; color: #0b3d91; margin: 8px 0; }
.ipa  { font-size: 20px; color: #555; margin-bottom: 6px; }
.pos  { font-size: 16px; color: #8a6d00; font-style: italic; margin: 4px 0; }
.def  { font-size: 20px; color: #222; margin: 10px 16px; }
.ex   { font-size: 18px; color: #2b6f3a; margin: 10px 16px; line-height: 1.4; }
.meta { font-size: 13px; color: #999; margin-top: 12px; }
hr#answer { border: none; border-top: 1px solid #ccc; margin: 14px 0; }
""",
)


def sound(fn: str) -> str:
    return f"[sound:{fn}]" if fn else ""


def main():
    cards_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data/cards.jsonl")
    audio_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "audio")
    out_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "build/TOEIC_COCA_10k.apkg")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    recs = [json.loads(l) for l in open(cards_path, encoding="utf-8")]
    deck = genanki.Deck(stable_id("TOEIC_COCA_10k_deck_v1"),
                        "TOEIC x COCA 高頻 10,000 單字")

    media = set()
    missing_audio = 0
    for r in recs:
        ex = r["collocations"]
        aw, ae = r.get("audio_word"), r.get("audio_examples", [None, None])
        for fn in [aw] + list(ae):
            if fn:
                p = os.path.join(audio_dir, fn)
                if os.path.exists(p) and os.path.getsize(p) > 0:
                    media.add(p)
                else:
                    missing_audio += 1
        note = genanki.Note(
            model=MODEL,
            fields=[
                r["headword"], r.get("ipa_us", ""), r.get("ipa_uk", "") or "",
                r.get("pos", ""), r["definition"],
                ex[0]["example"], ex[1]["example"],
                sound(aw), sound(ae[0]), sound(ae[1]),
                str(r["rank"]), str(r.get("level", "")),
            ],
            tags=["TOEIC", "COCA", f"L{r.get('level','')}"],
            guid=genanki.guid_for(f"coca10k:{r['rank']}:{r['headword']}"),
        )
        deck.add_note(note)

    pkg = genanki.Package(deck)
    pkg.media_files = sorted(media)
    pkg.write_to_file(out_path)
    size_mb = os.path.getsize(out_path) / 1e6
    print(f"deck: {out_path}")
    print(f"  notes: {len(recs)}  media: {len(media)}  missing_audio: {missing_audio}")
    print(f"  size: {size_mb:.1f} MB")
    return 0 if missing_audio == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
