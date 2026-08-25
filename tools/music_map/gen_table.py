#!/usr/bin/env python3
"""Generate dimuse_extmusic_table.h from hq_music_map.json.

The table maps each game music cue (e.g. "1099-M~1.IMX") to the OST file
base name (e.g. "ost_01_The_Adventure_Continues"). The engine looks for
that file (as .flac/.mp3/.wav) in <hd>/audio/.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = json.load(open(os.path.join(HERE, "hq_music_map.json")))

lines = []
lines.append("// Auto-generated from hq_music_map.json — do not edit by hand.")
lines.append("// Maps game music cues to OST file base names (looked up in <hd>/audio/).")
lines.append("struct ExtMusicEntry { const char *cue; const char *ost; };")
lines.append("static const ExtMusicEntry kExtMusicTable[] = {")
for cue, info in sorted(MAP.items()):
    ost = info["ost"].replace(".wav", "")  # "ost_01_The_Adventure_Continues"
    # normalize the cue name: bundle short names lack the dot before IMX
    game_cue = cue
    if "~1IMX" in game_cue and ".IMX" not in game_cue:
        game_cue = game_cue.replace("~1IMX", "~1.IMX")
    lines.append(f'\t{{"{game_cue}", "{ost}"}},')
lines.append("};")
lines.append(f"static const int kExtMusicTableSize = {len(MAP)};")

out = os.path.join(HERE, "dimuse_extmusic_table.h")
with open(out, "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote {out} ({len(MAP)} entries)")
