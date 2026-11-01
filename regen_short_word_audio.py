#!/usr/bin/env python3
"""
修超短單字音:把會被 edge-tts 吞音/唸成 schwa 的超短 headword(單字音檔 < THRESH bytes)
改用「雙引號孤立」法重產(TTS 輸入 = '"word"'),覆蓋同一個內容定址檔名(= hash(headword))。
卡片欄位/guid/例句音完全不動。產完用 whisper 抽驗。

執行:/Volumes/workplace/EnglishTraining/.venv/bin/python regen_short_word_audio.py [THRESH]
"""
import asyncio
import hashlib
import json
import os
import sys

import edge_tts

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICE = "en-US-EmmaMultilingualNeural"
AUDIO = os.path.join(ROOT, "audio")
THRESH = int(sys.argv[1]) if len(sys.argv) > 1 else 4500


def norm(t):
    return " ".join(t.strip().split())


def an(t):
    return hashlib.sha1(f"{VOICE}|{norm(t)}".encode()).hexdigest()[:16] + ".mp3"


async def gen(text, path):
    # 雙引號孤立,強制 TTS 以完整短句處理,避免吞音
    c = edge_tts.Communicate(f'"{text}"', VOICE)
    await c.save(path)


async def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "data/cards.jsonl"), encoding="utf-8")]
    # 依單字音檔大小挑超短;以 audio_word 檔名去重(同 headword 共用一檔)
    targets = {}
    for r in rows:
        fn = r.get("audio_word")
        if not fn:
            continue
        p = os.path.join(AUDIO, fn)
        if os.path.exists(p) and os.path.getsize(p) < THRESH:
            targets.setdefault(fn, r["headword"])
    # 一致性檢查:檔名必須 == hash(headword)
    bad = [(fn, hw) for fn, hw in targets.items() if fn != an(hw)]
    if bad:
        print("WARN: filename≠hash(headword) for", bad[:5], "...", len(bad))
    print(f"THRESH={THRESH}  要重產的超短單字音: {len(targets)} 個")
    done = 0
    for fn, hw in sorted(targets.items(), key=lambda x: x[1]):
        p = os.path.join(AUDIO, fn)
        old = os.path.getsize(p)
        await gen(hw, p)
        new = os.path.getsize(p)
        done += 1
        if done <= 30 or done % 50 == 0:
            print(f"  [{done}/{len(targets)}] {hw:12} {old}->{new}B")
    print(f"完成:重產 {done} 個超短單字音(雙引號法)")


if __name__ == "__main__":
    asyncio.run(main())
