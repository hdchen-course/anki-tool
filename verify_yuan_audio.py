#!/usr/bin/env python3
"""
全量 ASR 稽核:把修好的 apkg 裡每個(重產的)本機音檔用 whisper 轉文字,
與它應唸的文字正規化比對,列出所有「對不上」的檔供人工覆核。

比對規則:
  - 句子/定義(多字):用詞序列相似度 (difflib),>=0.72 視為通過。
  - 單字:正規化後完全相同、或互為前綴(ASR 對短音常有頭尾雜訊)視為通過;
          heteronym 改拼字(live→liv 等)以「原字」為準比對。
輸出:/tmp/yuan_audit.tsv(status, file, expected, heard),並印出統計 + 前幾筆 FAIL。

執行:/Volumes/workplace/EnglishTraining/.venv/bin/python verify_yuan_audio.py <fixed.apkg>
"""
import os
import re
import sys
import difflib

import anki_tool
from faster_whisper import WhisperModel
from fix_yuan_audio import collect, RESPELL


def norm_txt(s):
    return re.sub(r"[^a-z0-9 ]", "", (s or "").lower()).strip()


def norm_word(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def is_match(expected, heard):
    e, h = norm_txt(expected), norm_txt(heard)
    if not e:
        return True
    if " " in e:  # 句子/定義
        return difflib.SequenceMatcher(None, e, h).ratio() >= 0.72
    # 單字:還原 heteronym 改拼回原字比對
    ew = norm_word(expected)
    for real, spell in RESPELL.items():
        if norm_word(spell) == ew:
            ew = norm_word(real)
    hw = norm_word(heard)
    return hw == ew or hw.startswith(ew) or ew.startswith(hw) or ew in hw


def main():
    fixed = sys.argv[1]
    t = anki_tool.AnkiTool()
    t.load(fixed)
    want = collect(t)            # filename -> expected text(與重產同一套對應)
    md = t.col.media.dir()
    m = WhisperModel("base.en", device="cpu", compute_type="int8")
    rows, fails = [], 0
    for i, (fn, exp) in enumerate(sorted(want.items()), 1):
        p = os.path.join(md, fn)
        if not os.path.exists(p):
            rows.append(("MISSING", fn, exp, "")); fails += 1; continue
        segs, _ = m.transcribe(p, language="en")
        heard = " ".join(s.text.strip() for s in segs)
        ok = is_match(exp, heard)
        rows.append(("PASS" if ok else "FAIL", fn, exp, heard))
        if not ok:
            fails += 1
        if i % 300 == 0:
            print(f"  audited {i}/{len(want)}  (fails so far {fails})")
    t.close()
    with open("/tmp/yuan_audit.tsv", "w", encoding="utf-8") as f:
        for st, fn, exp, heard in rows:
            f.write(f"{st}\t{fn}\t{exp}\t{heard}\n")
    passed = sum(1 for r in rows if r[0] == "PASS")
    print(f"\n== 稽核完成 ==  total={len(rows)}  PASS={passed}  FAIL={fails}")
    print("FAIL 前 40 筆:")
    for st, fn, exp, heard in [r for r in rows if r[0] != "PASS"][:40]:
        print(f"  [{st}] {fn}\n        expect={exp!r}\n        heard ={heard!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
