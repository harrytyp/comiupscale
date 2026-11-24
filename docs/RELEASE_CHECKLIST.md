# Release-Checkliste

Stand 2026-11-23. Was geprueft ist und was nicht, damit niemand ein Release auf Vermutungen baut.

## Vor jedem Release

| Punkt | Befehl / Nachweis | Stand |
|---|---|---|
| Exec-Bits im Fork | `git ls-files -s scummvm/fork/configure` zeigt `100755` | erledigt, Issue #33 |
| Upstream-Zips im Repo | `ls scummvm/fork/gui/themes/*.zip` findet vier Dateien | erledigt, 12 Dateien committet |
| Upscaler-URL erreichbar | `curl -I` auf `…/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip` liefert 200 | erledigt |
| Pack-Manifest | `python3 scripts/pack_manifest.py --pack <hd> --check` endet mit 0 | erledigt fuer den 1.0.5-Pack |
| Unit-Tests Manifest | `python3 tests/test_pack_manifest.py` | erledigt, 5 Faelle gruen |
| GUI startet | `python3 setup_wizard/gui.py` | **offen**, braucht einen Rechner mit Bildschirm |
| Fork baut | `make -j4` im Fork | **offen**, scheitert hier an fehlenden ALSA-/X11-Dev-Paketen |
| Frischer Clone baut | `git clone && bash build/build-all.sh linux` | **offen**, braucht denselben Baukasten |
| Konformitaetslauf | `harness/konform_sweep.py`, Summe notieren | erledigt, 93 Raeume, 53 pixelgenau, Summe 5,80 % |
| Menue-Zustand (#32) | Aufnahme mit Tastendruck ins Menue | **offen** |

## Was ein Release enthalten muss

- Linux-Binary, gestrippt (`strip`)
- Windows-Binary plus `SDL2.dll` mit Audio und Startdateien
- HD-Pack mit `hd.json` (Version, Raumabdeckung, Objektzahl)
- Release-Notes auf Englisch, mit Links auf Store, HD-Assets und die 4K-Videos
- `setup.sh` und `setup_wizard` mit denselben Tags wie das Release

## Was nicht ohne Rueckfrage passiert

- Veroeffentlichen von Tag oder Assets
- Aendern der ausgelieferten Assets in `comi-hd-final/`
- Loeschen von Releases, Tags oder Branches, die nicht vollstaendig in `main` enthalten sind

## Offene Fehler, die ein Release nicht als "fertig" ausweisen sollte

- Objektkomposition in mehreren Raeumen (Raum 22: Holzgestell ueber dem Fass), Ursache eingegrenzt, Fix offen
- Menue-Ueberlagerung (#32) nicht reproduziert
- Raeume 41 bis 43, 70: Panning, Bewertung instabil
- Raum 81: Lauf endet im Zeitlimit
