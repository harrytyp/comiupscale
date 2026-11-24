#!/usr/bin/env python3
"""Grafische Oberflaeche fuer Installation, Extraktion, Upscaling und Pack-Verwaltung.

Ersetzt die reine Kommandozeile, ohne die bestehenden Skripte zu ersetzen: jeder Knopf ruft
genau das auf, was auch von Hand aufgerufen wird, und schreibt die Ausgabe ins Fenster.

    python3 setup_wizard/gui.py            # Fenster oeffnen
    python3 setup_wizard/gui.py --selftest # nur die geplanten Befehle pruefen (ohne Fenster)

Braucht nur die Standardbibliothek (tkinter), keine zusaetzlichen Pakete.
"""
import argparse
import os
import queue
import shutil
import subprocess
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def plan(action, game_dir="", hd_dir="", pack_root="", videos=""):
    """Befehl fuer eine Aktion bauen. Reine Funktion, damit sie ohne Fenster testbar ist."""
    py = lambda *a: [PY] + list(a)
    table = {
        "detect": py(os.path.join(ROOT, "scripts", "pack_manifest.py"), "--help"),
        "check_pack": py(os.path.join(ROOT, "scripts", "pack_manifest.py"), "--pack", hd_dir, "--check"),
        "write_pack": py(os.path.join(ROOT, "scripts", "pack_manifest.py"), "--pack", hd_dir, "--name", "local-pack"),
        "list_packs": py(os.path.join(ROOT, "scripts", "pack_manifest.py"), "--list", "--pack", pack_root),
        "extract": py(os.path.join(ROOT, "scripts", "extract_all_raw.py"), game_dir,
                      "--outdir", os.path.join(hd_dir, "..", "raw")),
        "upscale_bg": py(os.path.join(ROOT, "scripts", "upscale_esrgan.py"),
                         "--input", os.path.join(hd_dir, "..", "raw", "backgrounds"),
                         "--output", os.path.join(hd_dir, "backgrounds")),
        "upscale_obj": py(os.path.join(ROOT, "scripts", "upscale_esrgan.py"),
                          "--input", os.path.join(hd_dir, "..", "raw", "objects"),
                          "--output", os.path.join(hd_dir, "objects")),
        "install": ["bash", os.path.join(ROOT, "setup.sh")],
    }
    cmd = table.get(action)
    if cmd is None:
        raise SystemExit("unbekannte Aktion: %s" % action)
    return [c for c in cmd if c not in (None, "")]


def self_test():
    """Alle Aktionen einmal bauen und pruefen, dass die Skripte existieren."""
    cases = {
        "check_pack": ("hd",), "extract": ("game", "hd"), "upscale_bg": ("hd",),
        "upscale_obj": ("hd",), "list_packs": ("packs",),
    }
    ok = True
    for action, args in cases.items():
        cmd = plan(action, game_dir="/g", hd_dir="/h", pack_root="/p")
        script = cmd[1]
        exists = os.path.exists(script)
        ok = ok and exists
        print("%-12s %s  %s" % (action, "OK  " if exists else "FEHLT", " ".join(cmd[1:3])))
    print("Selbsttest:", "bestanden" if ok else "fehlgeschlagen")
    return 0 if ok else 1


class App:
    """Fenster: Pfade waehlen, Aktionen starten, Ausgabe mitlesen."""

    def __init__(self):
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        self.tk = tk
        self.fd = filedialog
        self.mb = messagebox
        self.root = tk.Tk()
        self.root.title("COMI HD Setup")
        self.root.geometry("880x640")
        self.queue = queue.Queue()
        self.proc = None

        self.game_dir = tk.StringVar()
        self.hd_dir = tk.StringVar()
        self.pack_root = tk.StringVar(value=os.path.join(ROOT, "packs"))

        frm = ttk.Frame(self.root, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="COMI HD: Installation, Upscaling, Packs", font=("TkDefaultFont", 14, "bold")).pack(anchor="w")

        self._path_row(frm, "Spielordner (COMI.LA0)", self.game_dir)
        self._path_row(frm, "HD-Pack-Ordner", self.hd_dir)
        self._path_row(frm, "Packs-Verzeichnis", self.pack_root)

        btns = ttk.LabelFrame(frm, text="Aktionen", padding=8)
        btns.pack(fill="x", pady=8)
        for label, action in (
            ("Pack pruefen", "check_pack"),
            ("Pack-Beschreibung schreiben", "write_pack"),
            ("Packs auflisten", "list_packs"),
            ("Rohdaten extrahieren", "extract"),
            ("Hintergruende upscalen", "upscale_bg"),
            ("Objekte upscalen", "upscale_obj"),
            ("Installer starten", "install"),
        ):
            ttk.Button(btns, text=label, command=lambda a=action: self.run(a)).pack(side="left", padx=2)

        self.log = tk.Text(frm, height=20, wrap="none")
        self.log.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="bereit")
        ttk.Label(frm, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x")

        self.root.after(100, self._drain)
        self.root.mainloop()

    def _path_row(self, parent, label, var):
        from tkinter import ttk
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=28).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="...", width=3, command=lambda: var.set(self.fd.askdirectory() or var.get())).pack(side="left")

    def _say(self, text):
        self.log.insert("end", text.rstrip("\n") + "\n")
        self.log.see("end")

    def run(self, action):
        if self.proc and self.proc.poll() is None:
            self.mb.showwarning("laeuft", "Es laeuft noch eine Aktion.")
            return
        try:
            cmd = plan(action, self.game_dir.get(), self.hd_dir.get(), self.pack_root.get())
        except SystemExit as exc:
            self._say(str(exc))
            return
        self._say("$ " + " ".join(cmd))
        self.status.set("laeuft: " + action)
        env = dict(os.environ, PYTHONUNBUFFERED="1")

        def worker():
            try:
                p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1)
                self.proc = p
                for line in p.stdout:
                    self.queue.put(line)
                p.wait()
                self.queue.put("\n[%s] fertig, Rueckgabewert %d\n" % (action, p.returncode))
            except Exception as exc:  # noqa: BLE001 - im Fenster anzeigen, nicht abstuerzen
                self.queue.put("\n[%s] Fehler: %s\n" % (action, exc))
        threading.Thread(target=worker, daemon=True).start()

    def _drain(self):
        try:
            while True:
                line = self.queue.get_nowait()
                self._say(line)
                if "fertig, Rueckgabewert" in line:
                    self.status.set("bereit")
        except queue.Empty:
            pass
        self.root.after(120, self._drain)


def main():
    ap = argparse.ArgumentParser(description="COMI HD grafische Oberflaeche")
    ap.add_argument("--selftest", action="store_true", help="nur Befehle pruefen, kein Fenster")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(self_test())
    if not shutil.which("bash") and os.name != "nt":
        print("Hinweis: bash fehlt, der Installer-Knopf funktioniert nicht.")
    App()


if __name__ == "__main__":
    main()
