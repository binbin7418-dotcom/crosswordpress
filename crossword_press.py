#!/usr/bin/env python3
"""CrosswordPress engine: your word+clue list -> print-ready crossword
puzzle book PDF (KDP interior), with an independent layout verification.

Deterministic placement: words are laid on a grid only where crossings
match letter-for-letter and no illegal letter adjacencies form. The
finished layout is then re-scanned from scratch: every horizontal and
vertical run in the grid must be exactly one of the placed words, the
numbering must be gapless, and every word must appear once in the clue
lists. Books that fail verification are never written.

100% local. Requires: reportlab.

Usage:
    python crossword_press.py words.csv out/ [--puzzles 20] [--seed 42]
"""
import csv
import os
import random
import re
import sys

PAGE_W, PAGE_H = 612, 792  # 8.5 x 11 in

# ------------------------------------------------------------------ words

def load_words(csv_path):
    words = []
    seen = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            w = re.sub(r"[^A-Za-z]", "", (row.get("word") or "")).upper()
            clue = (row.get("clue") or "").strip()
            if len(w) < 3 or len(w) > 15 or not clue or w in seen:
                continue
            seen.add(w)
            words.append({"word": w, "clue": clue})
    return words

# ------------------------------------------------------------------ layout

def _cells(word, r, c, d):
    return [(r + (i if d == "D" else 0), c + (i if d == "A" else 0), ch)
            for i, ch in enumerate(word)]


def _legal(grid, word, r, c, d, size):
    """(ok, crossings). Standard crossword legality."""
    cells = _cells(word, r, c, d)
    crossings = 0
    for rr, cc, ch in cells:
        if not (0 <= rr < size and 0 <= cc < size):
            return False, 0
        cur = grid.get((rr, cc))
        if cur is not None:
            if cur != ch:
                return False, 0
            crossings += 1
    if cells:
        dr, dc = (1, 0) if d == "D" else (0, 1)
        before = (cells[0][0] - dr, cells[0][1] - dc)
        after = (cells[-1][0] + dr, cells[-1][1] + dc)
        if before in grid or after in grid:
            return False, 0
    for rr, cc, ch in cells:
        if (rr, cc) in grid:
            continue  # crossing cell: perpendicular neighbours belong to the crossing word
        perp = [(rr - 1, cc), (rr + 1, cc)] if d == "A" else [(rr, cc - 1), (rr, cc + 1)]
        if any(p in grid for p in perp):
            return False, 0
    return True, crossings


def place_words(subset, size, rng, attempts=60):
    """Best layout found: (placed, grid). placed = list of dicts."""
    best = None
    base = sorted(subset, key=lambda w: -len(w["word"]))
    for attempt in range(attempts):
        order = base[:]
        if attempt:
            rng.shuffle(order)
            order.sort(key=lambda w: -len(w["word"]) + rng.random() * 2)
        grid = {}
        placed = []
        for w in order:
            word = w["word"]
            if not placed:
                r, c = size // 2, max(0, size // 2 - len(word) // 2)
                ok, _ = _legal(grid, word, r, c, "A", size)
                if not ok:
                    continue
                _commit(grid, placed, w, r, c, "A")
                continue
            cand = []
            for (gr, gc), gch in list(grid.items()):
                for i, ch in enumerate(word):
                    if ch != gch:
                        continue
                    for d in ("A", "D"):
                        rr = gr - (i if d == "D" else 0)
                        cc = gc - (i if d == "A" else 0)
                        ok, cross = _legal(grid, word, rr, cc, d, size)
                        if ok and cross >= 1:
                            area = _bbox_area(grid, word, rr, cc, d)
                            cand.append((cross * 100 - area, rr, cc, d))
            if not cand:
                continue
            cand.sort(reverse=True)
            top = cand[0][0]
            ties = [x for x in cand if x[0] == top]
            _, rr, cc, d = ties[rng.randrange(len(ties))]
            _commit(grid, placed, w, rr, cc, d)
        score = (len(placed), -_bbox_area_grid(grid))
        if best is None or score > best[0]:
            best = (score, placed, grid)
        if len(placed) == len(order):
            break
    return best[1], best[2]


def _commit(grid, placed, w, r, c, d):
    for rr, cc, ch in _cells(w["word"], r, c, d):
        grid[(rr, cc)] = ch
    placed.append({"word": w["word"], "clue": w["clue"], "r": r, "c": c, "dir": d})


def _bbox_area(grid, word, r, c, d):
    pts = list(grid) + [(rr, cc) for rr, cc, _ in _cells(word, r, c, d)]
    rs = [p[0] for p in pts]
    cs = [p[1] for p in pts]
    return (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)


def _bbox_area_grid(grid):
    if not grid:
        return 0
    rs = [p[0] for p in grid]
    cs = [p[1] for p in grid]
    return (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)


def crop_and_number(placed, grid):
    """Crop to bounding box, assign standard numbering, build clue lists."""
    rs = [p[0] for p in grid]
    cs = [p[1] for p in grid]
    r0, c0 = min(rs), min(cs)
    cells = {(r - r0, c - c0): ch for (r, c), ch in grid.items()}
    nrows = max(rs) - r0 + 1
    ncols = max(cs) - c0 + 1
    for p in placed:
        p["r"] -= r0
        p["c"] -= c0
    numbers = {}
    n = 0
    for r in range(nrows):
        for c in range(ncols):
            if (r, c) not in cells:
                continue
            starts_a = (c == 0 or (r, c - 1) not in cells) and (r, c + 1) in cells
            starts_d = (r == 0 or (r - 1, c) not in cells) and (r + 1, c) in cells
            if starts_a or starts_d:
                n += 1
                numbers[(r, c)] = n
    for p in placed:
        p["num"] = numbers[(p["r"], p["c"])]
    across = sorted([p for p in placed if p["dir"] == "A"], key=lambda p: p["num"])
    down = sorted([p for p in placed if p["dir"] == "D"], key=lambda p: p["num"])
    return {"cells": cells, "nrows": nrows, "ncols": ncols,
            "placed": placed, "across": across, "down": down, "max_num": n}

# ------------------------------------------------------------------ verify

def verify_layout(layout):
    """Independent re-scan of the cropped grid. Returns (ok, problems)."""
    problems = []
    cells, nrows, ncols = layout["cells"], layout["nrows"], layout["ncols"]
    runs = set()
    for r in range(nrows):
        run = ""
        for c in range(ncols + 1):
            ch = cells.get((r, c)) if c < ncols else None
            if ch:
                run += ch
            else:
                if len(run) >= 2:
                    runs.add(run)
                run = ""
    for c in range(ncols):
        run = ""
        for r in range(nrows + 1):
            ch = cells.get((r, c)) if r < nrows else None
            if ch:
                run += ch
            else:
                if len(run) >= 2:
                    runs.add(run)
                run = ""
    words = [p["word"] for p in layout["placed"]]
    if runs != set(words):
        problems.append(f"grid runs != placed words (runs-only {sorted(runs - set(words))}, "
                        f"words-only {sorted(set(words) - runs)})")
    if len(words) != len(set(words)):
        problems.append("duplicate word placed")
    for p in layout["placed"]:
        for rr, cc, ch in _cells(p["word"], p["r"], p["c"], p["dir"]):
            if cells.get((rr, cc)) != ch:
                problems.append(f"{p['word']} disagrees with grid at {(rr, cc)}")
                break
    nums = [p["num"] for p in layout["placed"]]
    if set(nums) != set(range(1, layout["max_num"] + 1)):
        problems.append("numbering inconsistent")
    if len(layout["across"]) + len(layout["down"]) != len(words):
        problems.append("clue lists do not cover every word exactly once")
    return (not problems), problems

# ------------------------------------------------------------------ PDF

def _wrap(text, font, size, width):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    out, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if stringWidth(trial, font, size) <= width or not cur:
            cur = trial
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def _draw_grid(c, layout, cx, top, cell, solution=False):
    cells, nrows, ncols = layout["cells"], layout["nrows"], layout["ncols"]
    nums = {(p["r"], p["c"]): p["num"] for p in layout["placed"]}
    x0 = cx - ncols * cell / 2
    y_top = top
    c.setLineWidth(0.7)
    for r in range(nrows):
        for col in range(ncols):
            x = x0 + col * cell
            y = y_top - (r + 1) * cell
            if (r, col) in cells:
                c.setFillColorRGB(1, 1, 1)
                c.rect(x, y, cell, cell, stroke=1, fill=1)
                if (r, col) in nums:
                    c.setFillColorRGB(0, 0, 0)
                    c.setFont("Helvetica", max(6, cell * 0.28))
                    c.drawString(x + 1.5, y + cell - max(8, cell * 0.34), str(nums[(r, col)]))
                if solution:
                    c.setFillColorRGB(0, 0, 0)
                    c.setFont("Helvetica-Bold", cell * 0.52)
                    c.drawCentredString(x + cell / 2, y + cell * 0.30, cells[(r, col)])
            else:
                c.setFillColorRGB(0, 0, 0)
                c.rect(x, y, cell, cell, stroke=1, fill=1)


def _draw_clues(c, layout, top):
    margin = 54
    col_w = (PAGE_W - 2 * margin - 24) / 2
    y = top
    c.setFillColorRGB(0, 0, 0)
    for x, title, items in ((margin, "ACROSS", layout["across"]),
                            (margin + col_w + 24, "DOWN", layout["down"])):
        yy = y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, yy, title)
        yy -= 14
        c.setFont("Helvetica", 9)
        for p in items:
            for line in _wrap(f"{p['num']}. {p['clue']}", "Helvetica", 9, col_w):
                c.drawString(x, yy, line)
                yy -= 11.5
            yy -= 1.5
    return y


def build_book(word_list, count, outdir, seed=42, per_puzzle=14, size=15,
               title="Crossword Puzzle Book"):
    from reportlab.pdfgen import canvas as rl_canvas
    rng = random.Random(seed)
    os.makedirs(outdir, exist_ok=True)
    pdf_path = os.path.join(outdir, "crossword_book.pdf")
    layouts, reports = [], []
    pool = word_list[:]
    for k in range(count):
        rng.shuffle(pool)
        subset = pool[:per_puzzle]
        placed, grid = place_words(subset, size, rng)
        layout = crop_and_number(placed, grid)
        ok, problems = verify_layout(layout)
        if not ok:
            raise RuntimeError(f"puzzle {k + 1} failed verification: {problems}")
        layouts.append(layout)
        reports.append({"puzzle": k + 1, "words_placed": len(placed),
                        "words_offered": len(subset),
                        "grid": f"{layout['nrows']}x{layout['ncols']}",
                        "verified": True})
    c = rl_canvas.Canvas(pdf_path, pagesize=(PAGE_W, PAGE_H))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 + 60, title)
    c.setFont("Helvetica", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 + 28,
                        f"{count} crosswords with full solutions")
    c.setFont("Helvetica", 10)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 6,
                        "Every grid in this book passed an independent re-scan:")
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2 - 20,
                        "all crossings agree letter-for-letter and numbering is gapless.")
    c.showPage()
    for i, layout in enumerate(layouts):
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(PAGE_W / 2, PAGE_H - 54, f"Puzzle {i + 1}")
        cell = min(30, 470 / max(layout["nrows"], layout["ncols"]))
        grid_top = PAGE_H - 76
        _draw_grid(c, layout, PAGE_W / 2, grid_top, cell)
        _draw_clues(c, layout, grid_top - layout["nrows"] * cell - 26)
        c.showPage()
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(PAGE_W / 2, PAGE_H / 2, "Solutions")
    c.showPage()
    for i, layout in enumerate(layouts):
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(PAGE_W / 2, PAGE_H - 54, f"Solution {i + 1}")
        cell = min(30, 470 / max(layout["nrows"], layout["ncols"]))
        _draw_grid(c, layout, PAGE_W / 2, PAGE_H - 76, cell, solution=True)
        c.showPage()
    c.save()
    return {"pdf_path": pdf_path, "puzzles": reports,
            "pages": 1 + count + 1 + count,
            "total_words_placed": sum(r["words_placed"] for r in reports)}


def run_crosswordpress(csv_path, count, outdir, seed=42, **kw):
    words = load_words(csv_path)
    if len(words) < 8:
        raise ValueError("word list needs at least 8 usable word+clue rows")
    return build_book(words, count, outdir, seed=seed, **kw)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=") for a in sys.argv[1:] if a.startswith("--"))
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    s = run_crosswordpress(args[0], int(opts.get("puzzles", 20)), args[1],
                           seed=int(opts.get("seed", 42)))
    print(f"{len(s['puzzles'])} puzzles, {s['total_words_placed']} words placed, "
          f"{s['pages']} pages\nPDF: {s['pdf_path']}")
