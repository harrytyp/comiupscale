import csv

pfad = "/opt/data/projects/comi-hd/reports/final_fix/gleicher_frame.csv"
rows = list(csv.DictReader(open(pfad), delimiter=";"))
gemessen = [r for r in rows if (r.get("ueber40_prozent") or "").strip()]
leer = [r["raum"] for r in rows if not (r.get("ueber40_prozent") or "").strip()]
werte = [float(r["ueber40_prozent"]) for r in gemessen]
print("Raeume in Datei: %d, gemessen: %d, ohne Aufnahme: %d" % (len(rows), len(gemessen), len(leer)))
if leer:
    print("ohne Aufnahme:", ",".join(leer))
if werte:
    print("Mittel %.2f%%, schlechtester %.1f%%" % (sum(werte) / len(werte), max(werte)))
    print("\nueber 2 Prozent:")
    for r in sorted(gemessen, key=lambda x: -float(x["ueber40_prozent"])):
        if float(r["ueber40_prozent"]) > 2:
            print("  Raum %-3s %5.1f%%  (Abweichung %s)" % (r["raum"], float(r["ueber40_prozent"]), r["abweichung"]))
