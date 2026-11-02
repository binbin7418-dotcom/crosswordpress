import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from crossword_press import run_crosswordpress


def run_job(src, count, seed, outdir):
    s = run_crosswordpress(src, count, outdir, seed=seed)
    lines = [f"Puzzles built: {len(s['puzzles'])}",
             f"Total words placed: {s['total_words_placed']}",
             f"Pages: {s['pages']}"]
    for r in s["puzzles"]:
        lines.append(f"  Puzzle {r['puzzle']}: {r['words_placed']}/{r['words_offered']} words, grid {r['grid']}, verified")
    lines.append(f"PDF: {s['pdf_path']}")
    return lines


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CrosswordPress")
        self.geometry("640x520")
        self.resizable(False, False)
        self.file = tk.StringVar()
        self.count = tk.StringVar(value="20")
        self.seed = tk.StringVar(value="42")
        row = tk.Frame(self); row.pack(fill="x", padx=12, pady=(12, 2))
        tk.Label(row, text="Word list CSV (word,clue):", width=34, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.file, width=38).pack(side="left")
        tk.Button(row, text="Browse", command=lambda: self.pick(self.file,
                  [("CSV files", "*.csv"), ("All files", "*.*")])).pack(side="left", padx=4)
        row = tk.Frame(self); row.pack(fill="x", padx=12, pady=2)
        tk.Label(row, text="Puzzles:", width=34, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=self.count, width=10).pack(side="left")
        tk.Label(row, text="Seed:").pack(side="left", padx=(10, 2))
        tk.Entry(row, textvariable=self.seed, width=10).pack(side="left")
        tk.Button(self, text="Build the book", font=("Segoe UI", 11, "bold"),
                  command=self.start).pack(pady=10)
        self.log = scrolledtext.ScrolledText(self, width=76, height=16,
                                             font=("Consolas", 9))
        self.log.pack(padx=12, pady=4)
        self.write("Your CSV needs two columns: word,clue. A 24-word sample list (sample_words.csv) is included.")

    def write(self, msg):
        self.log.insert(tk.END, str(msg) + "\n")
        self.log.see(tk.END)
        self.update_idletasks()

    def pick(self, var, types):
        p = filedialog.askopenfilename(filetypes=types)
        if p:
            var.set(p)
    def collect(self):
        src = self.file.get().strip()
        if not src or not os.path.isfile(src):
            raise ValueError("Choose a word+clue CSV first.")
        return (src, int(self.count.get()), int(self.seed.get()),
                os.path.join(os.path.dirname(src), "crosswordpress_out"))

    def start(self):
        try:
            args = self.collect()
        except Exception as e:
            messagebox.showerror("CrosswordPress", str(e))
            return
        self.write("Working... (the window stays responsive)")
        threading.Thread(target=self._run, args=args, daemon=True).start()

    def _run(self, *args):
        try:
            lines = run_job(*args)
            for line in lines:
                self.after(0, self.write, line)
        except Exception as e:
            self.after(0, self.write, f"ERROR: {e}")


if __name__ == "__main__":
    App().mainloop()
