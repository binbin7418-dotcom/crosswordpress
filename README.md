# CrosswordPress

Build print-ready **crossword puzzle books for Amazon KDP** from *your own* word+clue list — with every finished grid re-scanned and proven before it enters the book.

## Why

Puzzle-book buyers leave 1-star reviews for broken crosswords: a crossing that disagrees, a word in the grid with no clue, numbering with gaps. CrosswordPress treats those as build failures, not typos. After layout, an independent verifier re-scans the cropped grid from scratch — every across and down run must be exactly one of the placed words, every placed word's letters must match the grid, numbering must be gapless, and the clue lists must cover every word exactly once. A grid that fails is never written into a book.

## Use

**App (Windows):** launch `CrosswordPress.exe`, pick your word list CSV (two columns: `word,clue`), choose the number of puzzles and a seed, click **Build the book**. Output: `crossword_book.pdf` in a `crosswordpress_out` folder — title page, one puzzle page per crossword (grid + Across/Down clues), then a solutions section with filled grids. 8.5×11in (612×792pt), ready for KDP interior upload.

**Command line:** `python crossword_press.py words.csv out/ --puzzles=50 --seed=42`

A 24-word sample list is included (`sample_words.csv`, fruit theme) and a 6-puzzle sample book (`sample_book.pdf`).

## How placement works

Words are placed only where crossings match letter-for-letter and no illegal adjacencies form (standard crossword legality, including end caps and parallel-touch rules). Placement runs multiple seeded attempts and keeps the layout with the most words placed and the tightest grid. Generation is deterministic: the same seed rebuilds the same book, so a series keeps a consistent workflow.

## Verified

Acceptance test (8/8 PASS, `test/acceptance_results.txt`): from the 24-word sample list, a 6-puzzle book placed 13–14 of 14 offered words per puzzle (81 total), every grid passed the independent re-scan, PDF measured exactly 14 pages at 612×792pt, and placement was byte-identical across repeated runs with the same seed.

## Scope

Words must be 3–15 letters (A–Z) with a clue each. The tool places as many as legally fit and reports placed vs offered per puzzle — it never forces a word in by breaking a crossing. You bring the niche word list; CrosswordPress does layout, numbering, verification and the print-ready PDF. 100% local.

## Build from source

`pip install pyinstaller reportlab`, then `pyinstaller crosswordpress.spec`. Or push to GitHub and let the included Actions workflow build the Windows package.
