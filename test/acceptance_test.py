#!/usr/bin/env python3
"""CrosswordPress acceptance test: generate a real 6-puzzle book from the
bundled 24-word fruit list and assert placement quality, independent
verification, PDF structure and determinism."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from crossword_press import load_words, place_words, crop_and_number, verify_layout, build_book

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
WORDS = os.path.join(HERE, "..", "sample_words.csv")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


def main():
    words = load_words(WORDS)
    check("word list loads 24 words", len(words) == 24, f"got {len(words)}")

    # determinism: same seed, same layout
    import random
    p1, g1 = place_words(words[:14], 15, random.Random(7))
    p2, g2 = place_words(words[:14], 15, random.Random(7))
    sig1 = sorted((p["word"], p["r"], p["c"], p["dir"]) for p in p1)
    sig2 = sorted((p["word"], p["r"], p["c"], p["dir"]) for p in p2)
    check("placement is deterministic for a fixed seed", sig1 == sig2)

    s = build_book(words, 6, OUT, seed=7, per_puzzle=14)
    check("book PDF written", os.path.getsize(s["pdf_path"]) > 5000,
          f"{os.path.getsize(s['pdf_path'])} bytes")
    per = [r["words_placed"] for r in s["puzzles"]]
    check("every puzzle places >= 10 of 14 words", all(n >= 10 for n in per), f"per-puzzle {per}")
    check("every puzzle passed independent verification",
          all(r["verified"] for r in s["puzzles"]))
    check("page count = 1 title + 6 puzzles + 1 solutions title + 6 solutions",
          s["pages"] == 14, f"got {s['pages']}")

    from pypdf import PdfReader
    r = PdfReader(s["pdf_path"])
    check("PDF reopens with 14 pages", len(r.pages) == 14, f"got {len(r.pages)}")
    mb = r.pages[0].mediabox
    check("page size is 612x792 (8.5x11in)", float(mb.width) == 612 and float(mb.height) == 792,
          f"got {mb.width}x{mb.height}")

    failed = [x for x in results if not x[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
