# Input Session Log — 6. Juli 2026

> Extrahiert aus `hd_state.log` (v0.0.54)
> Room 9 (Cannon Room), Frames 92–215

---

## Timeline

| Frame | Event | Beschreibung |
|-------|-------|-------------|
| 92–102 | — | Normales Gameplay, Inventar zu, `visible~53K` |
| **103** | `KEY 0x1b` | **Escape** — Cutscene überspringen |
| 104–119 | — | Normales Gameplay, `visible~57K` |
| **120** | `MOUSE RCLICK pos=(405,337)` | **Rechtsklick — Inventar öffnet sich!** ✅ |
| 121–149 | — | Inventar OFFEN, `RENDER`, `visible~258K`, `invActive=1` |
| **150** | `MOUSE LCLICK pos=(168,201)` | **Linksklick** — vermutlich Item ausgewählt |
| 151–182 | — | Inventar OFFEN, `RENDER` |
| **183** | — | **Inventar schließt sich** (automatisch?), `CULL`, `visible~57K` |
| 184–206 | — | Normales Gameplay, `visible~61K` |
| **207** | `MOUSE RCLICK pos=(364,243)` | **Rechtsklick** — Inventar öffnet sich NICHT sofort |
| 208–210 | — | Übergang, `visible~59K`, `invActive=0` |
| **211** | `MOUSE RCLICK pos=(364,243)` | **2. Rechtsklick** — Inventar jetzt offen ✅ |
| 212–215 | — | Inventar OFFEN, `RENDER` |

---

## Wichtige Beobachtungen

### 1. Inventar-Gegenstände
- Frame 120: `step2.5 objects: loaded=7 skipped=0 culled=2` — **7 HD Texturen geladen**
- Frame 210: `step2.5 objects: loaded=2 skipped=0 culled=7` — **7 FLOBJs geculled** (Inventar zu)
- Frame 120&150: `step2.6b ui-overlay: pixels=0`
- Frame 210: `step2.6b ui-overlay: pixels=24112`

### 2. Cursor-Detection funktioniert ✅
- Bei Inventar zu: `visible~53K–61K`, `invActive=0` → CULL
- Bei Inventar offen: `visible~258K`, `invActive=1` → RENDER
- Einzige Verzögerung: 1 Frame Delay beim Öffnen (Frame 207→211)

### 3. Offene Fragen
- **Warum `culled=2` bei offenem Inventar?** Welche 2 FLOBJs wurden geculled?
- **Welche 7 wurden geladen?** Enthalten die Inventar-Icons?
- **`step2.6b ui-overlay: 24112`** bei Frame 210 — was ist das?
