#!/usr/bin/env python3
"""
Preview 牌組產生器:10 組 × 每組 2 字 = 20 張卡,供 HD 在 Anki 實機看新卡片設計。

設計(使用者 2026-11-01 定案):
  正面 = 英英定義 + 兩句挖空例句(headword 以 teal 底線空格取代)→ 回想單字
  背面 = 單字(teal 大字)+ US/UK 音標 + 兩句完整例句(答案字 teal 粗體)+ 發音
  配色 = 暖米白 / 暖炭(.nightMode)+ teal 強調 + 下半漸層
  發音 = Anki 原生 [sound:] 播放鈕(實機可播);預覽 HTML 用的自訂圓鈕為展示用
10 個子牌組(第01組…第10組)對應頻率 group 1–10,每組取前 2 個實詞(略過功能詞)。

執行:
  /Volumes/workplace/EnglishTraining/.venv/bin/python build_preview_apkg.py
產出:build/preview_10x2.apkg
"""
import collections
import hashlib
import html
import json
import os
import re
import sys

import genanki

ROOT = os.path.dirname(os.path.abspath(__file__))
FUNCTION_POS = {"article", "pronoun", "preposition", "conjunction",
                "determiner", "auxiliary", "particle"}


def sid(text):
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % (1 << 31)


def cloze(ex, w):
    return re.sub(r"\b" + re.escape(w) + r"(s|d|es|ed|ing)?\b",
                  '<span class="blank">______</span>', ex, flags=re.I)


def hil(ex, w):
    return re.sub(r"\b(" + re.escape(w) + r"(?:s|d|es|ed|ing)?)\b",
                  r'<span class="ans">\1</span>', html.escape(ex), flags=re.I)


def sound(fn):
    return f"[sound:{fn}]" if fn else ""


CSS = """
.card{--bg:#f6f1e7;--ink:#241f17;--body:#352f24;--soft:#5c5443;--accent:#1f6a5c;
 --chip:#dcebdf;--chip-ink:#17584c;--line:#e3dccb;--ans:#17584c;--blank:#1f6a5c;
 --grad:linear-gradient(170deg,#f8f3ea 0%,#e9f1ea 32%,#c6e4d6 72%,#aedcc8 100%);
 font-family:-apple-system,"Helvetica Neue",Arial,"PingFang TC",sans-serif;
 color:var(--body);background:var(--grad);min-height:100vh;
 -webkit-font-smoothing:antialiased;text-align:left;margin:0;padding:34px 22px 28px}
.card.nightMode{--bg:#201e18;--ink:#f2ede3;--body:#ddd7ca;--soft:#c2bcaa;--accent:#79d8c5;
 --chip:#294a42;--chip-ink:#a6ead9;--line:#36322a;--ans:#a6ead9;--blank:#79d8c5;
 --grad:linear-gradient(170deg,#201e18 0%,#19211e 32%,#0f2620 72%,#0a2a20 100%)}
.inner{width:100%;max-width:560px;margin:0 auto}
.def-front{font-size:25px;font-weight:700;color:var(--ink);text-align:center;line-height:1.45;margin:0 4px 20px}
.rule{border:none;border-top:1px solid var(--line);margin:18px 0 6px}
.ex{font-size:21px;color:var(--body);text-align:left;margin:16px 2px;line-height:1.6}
.blank{display:inline-block;min-width:92px;border-bottom:2.5px solid var(--blank);
 color:transparent;vertical-align:baseline;margin:0 3px}
.wordrow{display:flex;align-items:center;justify-content:center;gap:14px;margin:4px 0 10px;flex-wrap:wrap}
.word{font-size:46px;font-weight:800;color:var(--accent);letter-spacing:.005em}
.ipa{font-size:20px;color:var(--ink);text-align:center;margin-bottom:6px}
.ipa .t{color:var(--soft);font-size:15px}
.ans{color:var(--ans);font-weight:700}
.exrow{display:flex;align-items:center;gap:12px;margin:0 2px;padding:10px 0}
.exrow+.exrow{border-top:1px solid var(--line)}
.exrow .ex{flex:1;margin:0}
.grp{text-align:center;font-size:12px;letter-spacing:.1em;color:var(--soft);margin-top:18px}
/* Anki 原生播放鈕上色成 teal 家族 */
.replay-button svg{width:30px;height:30px}
.replay-button svg circle{fill:var(--chip)}
.replay-button svg path{fill:var(--chip-ink)}
"""

FRONT = """
<div class="inner">
 <div class="def-front">{{Definition}}</div>
 <hr class="rule">
 <div class="ex">{{Ex1Cloze}}</div>
 <div class="ex">{{Ex2Cloze}}</div>
</div>
"""

BACK = """
<div class="inner">
 <div class="wordrow"><span class="word">{{Headword}}</span> {{AudioWord}}</div>
 <div class="ipa"><span class="t">US</span> {{IPA_US}}　·　<span class="t">UK</span> {{IPA_UK}}</div>
 <hr class="rule">
 <div class="exrow"><div class="ex">{{Ex1Full}}</div> {{AudioEx1}}</div>
 <div class="exrow"><div class="ex">{{Ex2Full}}</div> {{AudioEx2}}</div>
 <div class="grp">{{Group}}</div>
</div>
"""

MODEL = genanki.Model(
    sid("TOEIC_COCA_preview_model_v1"),
    "TOEIC x COCA preview (cloze-recall, gradient)",
    fields=[{"name": n} for n in (
        "Headword", "IPA_US", "IPA_UK", "Definition",
        "Ex1Cloze", "Ex2Cloze", "Ex1Full", "Ex2Full",
        "AudioWord", "AudioEx1", "AudioEx2", "Group")],
    templates=[{"name": "Recall (definition -> word)", "qfmt": FRONT, "afmt": BACK}],
    css=CSS,
)


def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "data/cards.jsonl"), encoding="utf-8")]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)

    out = os.path.join(ROOT, "build/preview_10x2.apkg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    audio_dir = os.path.join(ROOT, "audio")

    decks, media = [], set()
    picked = []
    for grp in sorted(by):
        cand = sorted(by[grp], key=lambda r: r["freq_order"])
        sel = [r for r in cand
               if (r.get("pos", "").lower() not in FUNCTION_POS and len(r["headword"]) >= 4)][:2]
        lo = min(r["freq_order"] for r in by[grp])
        hi = max(r["freq_order"] for r in by[grp])
        deck = genanki.Deck(sid(f"preview_group_{grp}"),
                            f"COCA 10000::Band {grp:02d} ({lo:04d}-{hi:04d})")
        for r in sel:
            hw = r["headword"]
            c = r["collocations"]
            aw, ae = r.get("audio_word"), r.get("audio_examples", [None, None])
            for fn in [aw] + list(ae):
                p = os.path.join(audio_dir, fn or "")
                if fn and os.path.exists(p) and os.path.getsize(p) > 0:
                    media.add(p)
            note = genanki.Note(
                model=MODEL,
                fields=[
                    hw, html.escape(r.get("ipa_us", "")), html.escape(r.get("ipa_uk", "") or ""),
                    html.escape(r["definition"]),
                    cloze(c[0]["example"], hw), cloze(c[1]["example"], hw),
                    hil(c[0]["example"], hw), hil(c[1]["example"], hw),
                    sound(aw), sound(ae[0]), sound(ae[1]),
                    f"Band {grp:02d} · #{r['freq_order']}",
                ],
                guid=genanki.guid_for(f"preview:{r['rank']}:{hw}"),
            )
            deck.add_note(note)
            picked.append((grp, r["rank"], hw))
        decks.append(deck)

    pkg = genanki.Package(decks)
    pkg.media_files = sorted(media)
    pkg.write_to_file(out)
    print(f"deck: {out}  size: {os.path.getsize(out)/1e6:.1f} MB")
    print(f"notes: {len(picked)}  media: {len(media)}")
    for grp, rank, hw in picked:
        print(f"  第{grp:02d}組  rank {rank:<5} {hw}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
