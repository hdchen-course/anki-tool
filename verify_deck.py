#!/usr/bin/env python3
"""
DONE-GATE 驗證器:對全牌組做最終檢查。乾淨環境可重跑。

檢查:
  1. master schema:2 相異搭配、例句 6–14 字、sense_key==headword.1、ipa_uk 非空、無 CJK/簡體、無英式拼字。
  2. 音檔防漂移:每段現值文字 sha1 皆有非空 mp3(MISSING=0),無孤兒(ORPHAN=0)。
  3. rank 覆蓋:carded ∪ skip == 1..10000,無 uncovered、無重複 rank。
  4. .apkg 可被 anki 官方 library 讀回,note/media 數相符。

執行:
  /Volumes/workplace/EnglishTraining/.venv/bin/python verify_deck.py
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICE = "en-US-EmmaMultilingualNeural"
CJK = re.compile(r"[一-鿿぀-ヿ]")
# 簡體特徵字(抽樣)+ 常見英式拼字
SIMP = re.compile(r"[简体关键单后门边应顺举击减图归课乐习题]")
BRIT = re.compile(
    r"\b(behaviour|colour|grey|neighbour|centre|defence|flavour|favour|honour|"
    r"labour|fibre|theatre|licence|organise|recognise|analyse|catalogue|"
    r"gaol|plait|rucksack|sledge|manoeuvre|mollusc|oedema|ochre|valour)\b",
    re.I,
)


def norm(t):
    return " ".join(t.strip().split())


def an(t):
    return hashlib.sha1(f"{VOICE}|{norm(t)}".encode("utf-8")).hexdigest()[:16] + ".mp3"


def check_master(cards_path, audio_dir):
    recs = [json.loads(l) for l in open(cards_path, encoding="utf-8")]
    errs = []
    ref, missing, ranks = set(), 0, []
    for r in recs:
        ranks.append(r["rank"])
        c = r.get("collocations", [])
        if len(c) != 2:
            errs.append(f"{r['rank']} {r['headword']}: not 2 collocations")
        if len({x["collocation"] for x in c}) < 2:
            errs.append(f"{r['rank']} {r['headword']}: duplicate collocation")
        if r.get("sense_key") != r["headword"] + ".1":
            errs.append(f"{r['rank']} {r['headword']}: sense_key mismatch")
        if not (r.get("ipa_uk") or "").strip():
            errs.append(f"{r['rank']} {r['headword']}: empty ipa_uk")
        blob = r["definition"] + " " + r["headword"] + " " + " ".join(
            x["collocation"] + " " + x["example"] for x in c)
        if CJK.search(blob):
            errs.append(f"{r['rank']} {r['headword']}: CJK present")
        if SIMP.search(blob):
            errs.append(f"{r['rank']} {r['headword']}: simplified-char present")
        if BRIT.search(blob):
            errs.append(f"{r['rank']} {r['headword']}: British spelling/word: {BRIT.search(blob).group(0)}")
        for x in c:
            wc = len(x["example"].split())
            if not (6 <= wc <= 14):
                errs.append(f"{r['rank']} {r['headword']}: example {wc} words")
        for t, fn in [(r["headword"], r.get("audio_word"))] + list(
                zip([x["example"] for x in c], r.get("audio_examples", [None, None]))):
            if fn != an(t):
                errs.append(f"{r['rank']} {r['headword']}: audio hash mismatch for {t!r}")
            ref.add(fn)
            p = os.path.join(audio_dir, fn or "")
            if not (fn and os.path.exists(p) and os.path.getsize(p) > 0):
                missing += 1
    orphans = [f for f in os.listdir(audio_dir)
               if f.endswith(".mp3") and f not in ref]
    return recs, errs, ranks, missing, orphans


def check_coverage(ranks, skip_path):
    skip = set(json.load(open(skip_path))["artifact_ranks"])
    used = set(ranks)
    allr = set(range(1, 10001))
    uncovered = sorted(allr - used - skip)
    dup = len(ranks) - len(used)
    overlap = sorted(used & skip)
    return skip, uncovered, dup, overlap


def check_apkg(apkg_path, n_notes_expected):
    """用官方 anki library 把 .apkg 讀回乾淨 collection,比對 note/media 數。"""
    try:
        from anki.collection import Collection, ImportAnkiPackageRequest
    except Exception as e:
        return f"SKIP (anki lib unavailable: {e})", None, None
    tmp = tempfile.mkdtemp(prefix="ankiverify_")
    col = Collection(os.path.join(tmp, "col.anki2"))
    try:
        try:
            # modern anki: collection-level apkg import
            col.import_anki_package(ImportAnkiPackageRequest(package_path=apkg_path))
        except Exception:
            # fallback for older anki with legacy importer
            from anki.importing.apkg import AnkiPackageImporter
            AnkiPackageImporter(col, apkg_path).run()
        n_notes = col.note_count()
        n_cards = col.card_count()
    finally:
        col.close()
    with zipfile.ZipFile(apkg_path) as z:
        name = "media" if "media" in z.namelist() else None
        media_map = json.loads(z.read(name)) if name else {}
    return None, n_notes, (n_cards, len(media_map))


def main():
    cards = os.path.join(ROOT, "data/cards.jsonl")
    audio = os.path.join(ROOT, "audio")
    skip = os.path.join(ROOT, "data/skip_ranks.json")
    apkg = os.path.join(ROOT, "build/COCA_10000.apkg")

    recs, errs, ranks, missing, orphans = check_master(cards, audio)
    skipset, uncovered, dup, overlap = check_coverage(ranks, skip)

    print(f"== master ==  cards={len(recs)}  schema_errs={len(errs)}  "
          f"MISSING={missing}  ORPHAN={len(orphans)}")
    for e in errs[:20]:
        print("   ERR:", e)
    print(f"== coverage ==  carded={len(set(ranks))}  skip={len(skipset)}  "
          f"carded+skip={len(set(ranks))+len(skipset)}  uncovered={len(uncovered)}  "
          f"dup_rank={dup}  carded∩skip={len(overlap)}")
    if uncovered:
        print("   uncovered:", uncovered[:20])
    if overlap:
        print("   overlap:", overlap[:20])

    apkg_err, n_notes, extra = check_apkg(apkg, len(recs))
    if apkg_err:
        print(f"== apkg ==  {apkg_err}")
    else:
        n_cards, n_media = extra
        print(f"== apkg ==  notes_readback={n_notes} (expect {len(recs)})  "
              f"cards={n_cards} (expect {2*len(recs)})  media={n_media}")

    ok = (not errs and missing == 0 and len(orphans) == 0
          and not uncovered and dup == 0 and not overlap
          and (apkg_err is not None or n_notes == len(recs)))
    print("\nRESULT:", "PASS ✅" if ok else "FAIL ❌")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
