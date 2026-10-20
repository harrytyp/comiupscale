import csv

erwartet = {z.strip() for z in open("/opt/data/projects/comi-hd/work/rooms_expected.txt") if z.strip()}
import sys
pfad = sys.argv[1] if len(sys.argv) > 1 else "/opt/data/projects/comi-hd/reports/gesamt/gleicher_frame.csv"
rows = list(csv.DictReader(open(pfad), delimiter=";"))
gemessen = {r["raum"] for r in rows}
fehlt = sorted(erwartet - gemessen, key=lambda r: int(r) if r.isdigit() else 0)
print("erwartet %d, gemessen %d, fehlen %d" % (len(erwartet), len(gemessen), len(fehlt)))
print("fehlend:", ",".join(fehlt))
if rows:
    werte = [float(r["ueber40_prozent"]) for r in rows if (r.get("ueber40_prozent") or "").strip()]
    print("Mittel %.2f%%, schlechtester %.1f%%" % (sum(werte) / len(werte), max(werte)))
