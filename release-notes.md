## Issue #10 — Inventory Items HD beim Drag außerhalb des Inventars ✅

**GELÖST!** Der Fix: Statt den Cursor zu verstecken (was backend-abhängig nie funktioniert hat) wird das Cursor-Bild durch ein 1x1 transparentes Pixel ersetzt. Das SD/OpenGL Cursor-Overlay ist dann unsichtbar, und die HD-Textur im Composite ist das einzig Sichtbare.

### Was geändert wurde
- **Step 2.9** (gfx.cpp): CursorMan.replaceCursor(blank, 1, 1, 0, 0, 0, true) — ersetzt das Cursor-Bild durch transparentes Pixel
- **setCursorFromImg-Hook** (cursor.cpp): Trackt _hdCursorObject und unterdrückt updateScreen() für Inventory-Items
- **OpenGL Backend** (opengl-graphics.cpp): renderCursor() prüft _cursorVisible

### Release Dateien
- comiupscale-fix10-win32.tar.gz — Windows Binary + DLLs + INI + Start-Scripts
- comiupscale-fix10-linux64.tar.gz — Linux Binary + INI + Start-Script

### Installation
1. HD-Assets downloaden (comi_hd_v1.0.2.tar.* oder hd_assets_part*.zip)
2. Tar.gz in ein lokales Verzeichnis entpacken
3. start_comi_hd.bat (Windows) oder start_comi_hd.sh (Linux) ausführen
