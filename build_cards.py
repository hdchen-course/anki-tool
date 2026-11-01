#!/usr/bin/env python3
"""
Pass 2 卡片建置管線(可重跑)。

輸入:authored 記錄(每字已定 sense / definition / 2 collocation 例句)。
動作:
  1. 為 headword + 每句例句產生 edge-tts 音檔(內容定址檔名 = sha1(文字+語音)[:16].mp3)。
  2. 把音檔對映寫進卡片記錄(audio_word / audio_examples)。
  3. 防漂移 verify:每段現值文字的 hash 必有對應檔;列出孤兒檔。

用上層 .venv 執行:
  /Volumes/workplace/EnglishTraining/.venv/bin/python build_cards.py <authored.jsonl> <out_cards.jsonl> <audio_dir>
"""
import asyncio, hashlib, json, os, sys
import edge_tts

VOICE = "en-US-EmmaMultilingualNeural"


def norm(text: str) -> str:
    return " ".join(text.strip().split())


def audio_name(text: str, voice: str = VOICE) -> str:
    h = hashlib.sha1(f"{voice}|{norm(text)}".encode("utf-8")).hexdigest()[:16]
    return f"{h}.mp3"


async def synth(text: str, path: str):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    await edge_tts.Communicate(norm(text), VOICE).save(path)


async def build(authored_path, out_path, audio_dir):
    os.makedirs(audio_dir, exist_ok=True)
    records = [json.loads(l) for l in open(authored_path, encoding="utf-8")]

    # 收集所有要發音的文字(去重),一次產生
    want = {}  # text -> filename
    for r in records:
        for t in [r["headword"]] + [c["example"] for c in r["collocations"]]:
            want[norm(t)] = audio_name(t)
    sem = asyncio.Semaphore(8)
    async def one(text, fn):
        async with sem:
            await synth(text, os.path.join(audio_dir, fn))
    await asyncio.gather(*(one(t, fn) for t, fn in want.items()))

    # 寫卡片記錄(含音檔對映)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in records:
            r["audio_word"] = audio_name(r["headword"])
            r["audio_examples"] = [audio_name(c["example"]) for c in r["collocations"]]
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 防漂移 verify
    referenced = set()
    missing = []
    for r in records:
        for t, fn in [(r["headword"], r["audio_word"])] + \
                     [(c["example"], af) for c, af in zip(r["collocations"], r["audio_examples"])]:
            referenced.add(fn)
            p = os.path.join(audio_dir, fn)
            if not (os.path.exists(p) and os.path.getsize(p) > 0):
                missing.append((r["headword"], t, fn))
    orphans = [fn for fn in os.listdir(audio_dir) if fn.endswith(".mp3") and fn not in referenced]
    print(f"cards: {len(records)}  audio files: {len(referenced)}")
    print(f"  MISSING (text 無對應音檔): {len(missing)}")
    for hw, t, fn in missing[:10]:
        print(f"    [{hw}] {t!r} -> {fn}")
    print(f"  ORPHAN (孤兒音檔): {len(orphans)}")
    return len(missing) == 0 and len(orphans) == 0


if __name__ == "__main__":
    ok = asyncio.run(build(sys.argv[1], sys.argv[2], sys.argv[3]))
    sys.exit(0 if ok else 1)
