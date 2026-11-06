#!/usr/bin/env python3
"""
修 Yuan's English.apkg 的 CEFR + DK 片語動詞本機音檔:
  - 以「正確欄位文字」用 edge-tts 重產(修 Google TTS 音質 + 音文配錯)。
  - 超短單字用引號孤立(避免吞音,沿用 build_cards 規則)。
  - 多音字(heteronym)用改拼 override map 取得正確讀音(edge-tts 不支援 SSML 音標)。
  - 只覆蓋媒體位元組(檔名不變)→ note 欄位/guid/排程、遠端 DK URL 全不動。
欄位→文字對應(由 ASR 實測確認):
  CEFR  : SentAudio←Question(去 cloze)  Audio←Definition  OptionsAudio[i]←Options[i]
  PhraseVerb: DefAudio←Definition  (Audio 為遠端 URL,不碰)

執行:/Volumes/workplace/EnglishTraining/.venv/bin/python fix_yuan_audio.py <in.apkg> <out.apkg>
"""
import asyncio
import html as htmllib
import os
import re
import sys

import edge_tts
import anki_tool
from build_cards import tts_source  # 超短字引號規則


def clean_text(s):
    """去 HTML 標籤 / 實體 / 多餘空白,供 TTS 使用。"""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = htmllib.unescape(s)
    s = s.replace(" ", " ")
    return " ".join(s.split()).strip()

VOICE = "en-US-EmmaMultilingualNeural"

# 多音字改拼:送 TTS 前替換,取得句子需要的讀音。檔名仍用原字。
RESPELL = {
    "live": "liv",   # /lɪv/ 居住(I live with my family)
}


def sounds(s):
    return re.findall(r"\[sound:([^\]]+)\]", s or "")


def strip_cloze(q):
    return re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", q or "").strip()


def tts_for_word(w):
    w2 = RESPELL.get(w.strip().lower(), w.strip())
    return tts_source(w2, headword=True)  # 短字加引號


def collect(tool):
    """回傳 {filename: tts_text}(本機音檔去重;遠端 URL 跳過)。"""
    want = {}
    for n in tool.get_notes():
        m, f = n["model_name"], n["fields"]
        if m == "Basic-Child-CEFR-Cloze-Radios":
            for fn in sounds(f.get("SentAudio")):
                want[fn] = clean_text(strip_cloze(f.get("Question")))
            for fn in sounds(f.get("Audio")):
                want[fn] = clean_text(f.get("Definition"))
            opts = [w.strip() for w in re.split(r"<br>|\n", f.get("Options", "")) if w.strip()]
            ofiles = sounds(f.get("OptionsAudio"))
            for w, fn in zip(opts, ofiles):
                want[fn] = tts_for_word(clean_text(w))
        elif m == "Basic-Child-PhraseVerb":
            for fn in sounds(f.get("DefAudio")):
                want[fn] = clean_text(f.get("Definition"))
    return {fn: t for fn, t in want.items() if t and re.search(r"[A-Za-z0-9]", t)}


async def synth_all(want, media_dir):
    sem = asyncio.Semaphore(8)
    done = [0]
    failed = []
    async def one(fn, text):
        async with sem:
            for attempt in range(3):
                try:
                    await edge_tts.Communicate(text, VOICE).save(os.path.join(media_dir, fn))
                    break
                except Exception as e:
                    if attempt == 2:
                        failed.append((fn, text, repr(e)))
                    else:
                        await asyncio.sleep(1.5)
            done[0] += 1
            if done[0] % 250 == 0:
                print(f"  {done[0]}/{len(want)}  (failed {len(failed)})")
    await asyncio.gather(*(one(fn, t) for fn, t in want.items()))
    return failed


def main():
    src, out = sys.argv[1], sys.argv[2]
    t = anki_tool.AnkiTool()
    t.load(src)
    want = collect(t)
    media_dir = t.col.media.dir()
    print(f"要重產的本機音檔: {len(want)}  媒體夾: {media_dir}")
    failed = asyncio.run(synth_all(want, media_dir))
    print(f"重產完成(失敗 {len(failed)});失敗清單:")
    for fn, txt, err in failed[:30]:
        print(f"   {fn}  text={txt!r}  {err}")
    print("匯出 apkg...")
    t.save(out)
    t.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
