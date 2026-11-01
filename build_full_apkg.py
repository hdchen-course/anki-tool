#!/usr/bin/env python3
"""
全量牌組產生器:COCA 10000(10,000 字,10 個 Band 子組,新卡片設計)。

沿用 build_preview_apkg.py 的 MODEL / CSS / 模板(cloze-recall 正面 + 單字背面、
暖米白/暖炭漸層、teal 強調、Anki 原生 [sound:] 發音),把 data/cards.jsonl 全部
10,000 筆依 freq_order 分到 Band 01–10 子組,嵌入全部引用到的 edge-tts 音檔。

執行(用上層 .venv):
  /Volumes/workplace/EnglishTraining/.venv/bin/python build_full_apkg.py
產出:build/COCA_10000.apkg
"""
import collections
import html
import json
import os
import sys

import genanki

from build_preview_apkg import CSS, MODEL, cloze, hil, sound, sid  # reuse design

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "data/cards.jsonl"), encoding="utf-8")]
    by = collections.defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)

    out = os.path.join(ROOT, "build/COCA_10000.apkg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    audio_dir = os.path.join(ROOT, "audio")

    decks, media = [], set()
    n = 0
    for grp in sorted(by):
        lo = min(r["freq_order"] for r in by[grp])
        hi = max(r["freq_order"] for r in by[grp])
        deck = genanki.Deck(sid(f"coca10000_band_{grp}"),
                            f"COCA 10000::Band {grp:02d} ({lo:04d}-{hi:04d})")
        for r in sorted(by[grp], key=lambda x: x["freq_order"]):
            hw = r["headword"]
            c = r["collocations"]
            aw, ae = r.get("audio_word"), r.get("audio_examples", [None, None])
            for fn in [aw] + list(ae):
                p = os.path.join(audio_dir, fn or "")
                if fn and os.path.exists(p) and os.path.getsize(p) > 0:
                    media.add(p)
            deck.add_note(genanki.Note(
                model=MODEL,
                fields=[
                    hw, html.escape(r.get("ipa_us", "")), html.escape(r.get("ipa_uk", "") or ""),
                    html.escape(r["definition"]),
                    cloze(c[0]["example"], hw), cloze(c[1]["example"], hw),
                    hil(c[0]["example"], hw), hil(c[1]["example"], hw),
                    sound(aw), sound(ae[0]), sound(ae[1]),
                    f"Band {grp:02d} · #{r['freq_order']}",
                ],
                guid=genanki.guid_for(f"coca10k:{r['rank']}:{hw}"),
            ))
            n += 1
        decks.append(deck)

    pkg = genanki.Package(decks)
    pkg.media_files = sorted(media)
    pkg.write_to_file(out)
    print(f"deck: {out}  size: {os.path.getsize(out)/1e6:.1f} MB")
    print(f"notes: {n}  media: {len(media)}  bands: {len(decks)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
