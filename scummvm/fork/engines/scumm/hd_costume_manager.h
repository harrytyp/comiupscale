/* ScummVM - Graphic Adventure Engine
 *
 * ScummVM is the legal property of its developers, whose names
 * are too numerous to list here. Please refer to the COPYRIGHT
 * file distributed with this source distribution.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#ifndef SCUMM_HD_COSTUME_MANAGER_H
#define SCUMM_HD_COSTUME_MANAGER_H

#include "common/str.h"
#include "common/hashmap.h"
#include "common/hash-str.h"
#include "graphics/surface.h"

namespace Scumm {

class ScummEngine;

/**
 * Manages HD replacement textures for AKOS costumes (sprites/characters).
 *
 * Costume PNG naming: LFLF_{akos_id:04d}_AKOS_{akos_sub:04d}_aframe_{frame}.png
 *
 * The manager maps AKOS (actor costume) entries to their HD PNG counterparts
 * and provides cached texture access for the renderer.
 *
 * Costumes are drawn with z-ordering by the SCUMM engine; this manager
 * only handles texture replacement — the existing z-order pipeline is preserved.
 */
/**
 * Schliesst kleine Loecher in der Deckkraft einer Textur (durchsichtige Pixel INNEN in
 * einer deckenden Flaeche). Betroffen sind 160 von 500 Kostuemen und 64 Objektbilder,
 * bis zu 41.727 Pixel je Bild; im Spiel erscheinen sie als loechrige Flaechen.
 * Wird auch fuer Raumobjekte benutzt (hd_object_manager.cpp).
 */
void hdFillAlphaHoles(Graphics::Surface &s, int passes = 3);

/**
 * Aufteilung des Cel-Dekodepfads (Mikrosekunden seit Programmstart, Summen).
 * Nur fuer die Perf-Messung (Backlog 11): trennt PNG-Dekode, Lochfuellung,
 * Kopie in den Zwischenspeicher (mit Zeilenbereichen), Kopie zum Aufrufer und
 * Cache-Pruefung. Ohne diese Aufteilung ist "45 ms je Dekode" nur eine Summe.
 */
void hdCostumeLoadDetail(uint64 &pngUs, uint64 &fillUs, uint64 &copyUs,
                         uint64 &destUs, uint64 &pruneUs, uint64 &pixels,
                         uint64 &decodeUs, uint64 &convUs, uint64 &fringeUs);

class HdCostumeManager {
public:
	HdCostumeManager(ScummEngine *vm);
	~HdCostumeManager();

	/** Initialize by scanning the hd/costumes/ directory. */
	bool init(const Common::String &hdPath);

	/** Check if an HD costume frame exists for the given akosId and frame (searches all subs). */
	bool hasCostume(int akosId, int frame) const;

	/**
	 * Gibt es fuer dieses Kostuem ueberhaupt HD-Bilder (irgendein Cel)?
	 * Wird fuer den Rueckfall gebraucht: hat eine Figur HD-Bilder, darf fuer ein
	 * fehlendes Cel nicht die 8-Bit-Fassung gezeichnet werden. In einer Sequenz wechselt
	 * das Cel jedes Bild, dadurch flackerte Guybrush zwischen HD und 8 Bit.
	 */
	bool hasCostumeId(int akosId) const;

	/**
	 * Laedt ein Einzelbild einer Figur.
	 * Die Flaeche ist RGBA8888 wenn Alpha vorhanden ist, sonst RGB888.
	 *
	 * Bei einem Treffer im Zwischenspeicher wird die zwischengespeicherte Flaeche
	 * normalerweise nach dest kopiert. Wer nur zeichnen will, kann stattdessen
	 * cachedOut uebergeben: dann zeigt der Zeiger auf die Flaeche im Cache und die
	 * Kopie entfaellt. Der Zeiger gilt nur innerhalb des laufenden Bildes, solange
	 * kein weiteres loadCostume dazwischenkommt. Der Cache hat ein Budget von 1,5 GB
	 * und verdraengt in der Praxis nichts.
	 *
	 * rowFirstOut/rowLastOut/spanRowsOut liefern die Zeilenbereiche (erste und letzte
	 * gedeckte Spalte je Quellzeile) genau zu der Flaeche, die zurueckgegeben wurde.
	 * Nicht ueber getRowSpans nachfragen: bei Kostuemen mit mehreren Unterbildern
	 * (Koerperteile) kann die Nachfrage ein anderes Unterbild treffen als das geladene.
	 */
	bool loadCostume(int akosId, int frame, Graphics::Surface &dest,
	                 const Graphics::Surface **cachedOut = nullptr,
	                 const uint16 **rowFirstOut = nullptr, const uint16 **rowLastOut = nullptr,
	                 int *spanRowsOut = nullptr);
	bool isFrameCached(int akosId, int frame) const;
	/**
	 * Liefert je Quellzeile die erste und letzte Spalte mit Deckung.
	 * Die Zeiger zeigen in den Cache und gelten nur, solange der Eintrag dort liegt.
	 * Leere Zeilen haben first > last.
	 */
	bool getRowSpans(int akosId, int frame, const uint16 **first, const uint16 **last, int *rows) const;
	int preloadNext(int akosId);

	/** Load all uncached frames of a costume in [from..to] (wraps via
	 *  loadCostume's modulo). Called on room enter for the animation
	 *  range the actors are currently playing. Returns frames loaded. */
	int preloadCostumeRange(int akosId, int from, int to);

	/** Beim Raumeintritt den ganzen Satz eines Kostuems vorbereiten (bis zu maxFrames
	 *  noch nicht zwischengespeicherte Cels) und dabei die teuren Schritte auf
	 *  `threads` Worker verteilen. Rueckgabe: wirklich geladene Cels.
	 *  Anlass: der Erstzugriff im Zeichenweg kostet 25 ms je Cel, Raum 84 braucht 103
	 *  davon; der 12-ms-Vorlauf neben dem Bild kann das nicht aufholen. */
	int preloadCostumeSet(int akosId, int maxFrames, int threads = 4);

	/** Gemeinsamer Kern: Cels im Bildbereich [from..to] aufbereiten und eintragen. */
	int hdPreloadCels(int akosId, int from, int to, int maxFrames, int threads);

	/**
	 * Asynchroner Vorlauf (Aufgabe 11, Weg (b)): bereitet bis zu maxFrames noch fehlende
	 * Cels im Hintergrund vor, beginnend beim Rahmen fromFrame (mit Umlauf). Der Aufruf
	 * kehrt sofort zurueck; der Worker dekodiert unabhaengig vom Bildtakt. Ein Satz
	 * gleichzeitig, laufende oder fertige Cels werden nicht doppelt angefordert.
	 * Anlass: im kalten Raum ist die Restzeit des Bildes null, deshalb dekodierte der
	 * Zeichenweg jedes Cel selbst (Raum 84: 103 x 25 ms). Rueckgabe: Anzahl der Auftraege.
	 */
	int requestAsync(int akosId, int fromFrame, int maxFrames);

	/** Fertige Cels in den Zwischenspeicher eintragen (Hauptthread, ohne Dekode). */
	int pumpAsync();

	/** Auftraege, die noch laufen oder auf das Eintragen warten (nur fuer die Messung). */
	int asyncPending();

	/** Worker-Rumpf (von hdAsyncThunk gerufen): Auftrag aufbereiten, Ergebnisliste fuellen. */
	void hdAsyncRun();

	/** Returns true if HD costume mode is active. */
	bool isEnabled() const { return _enabled; }

	/**
	 * Zaehler fuer die Perf-Messung: Bilder aus dem Zwischenspeicher gegen wirklich
	 * dekodierte. Trennt "Dekode je Bild" von "Zeichnen ist teuer" (Backlog 11).
	 */
	static void hdCostumeStats(int &treffer, int &dekode);

private:
	struct CostumeKey {
		int akosId;
		int akosSub;
		int frame;

		bool operator==(const CostumeKey &other) const {
			return akosId == other.akosId && akosSub == other.akosSub && frame == other.frame;
		}
	};

	struct CostumeKeyHash {
		uint operator()(const CostumeKey &k) const {
			return (uint)(k.akosId * 1000003 + k.akosSub * 10007 + k.frame);
		}
	};

	struct TextureCacheEntry {
		Graphics::Surface surface;
		int lastUsed;
		// Erste und letzte Spalte mit Deckung je Quellzeile, einmal beim Laden bestimmt.
		// Eine leere Zeile wird als first=1, last=0 abgelegt, also first > last.
		// Der Zeichenweg begrenzt damit jede Zeile auf den Figurenumriss (Schritt 2.6 in
		// gfx.cpp); die Bereiche kommen aus loadCostume, damit sie zu genau der Flaeche
		// gehoeren, die gezeichnet wird.
		Common::Array<uint16> rowFirst;
		Common::Array<uint16> rowLast;
	};

	ScummEngine *_vm;
	bool _enabled;

	// Set of available costume frames (using HashMap as a set)
	Common::HashMap<CostumeKey, bool, CostumeKeyHash> _availableCostumes;

	// Per-AKOS: list of available sub-IDs (built during init)
	Common::HashMap<int, Common::List<int>> _akosSubs;

	// Texture cache (LRU)
	Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash> _textureCache;
	int _lruCounter;

	// Time-sliced prefetch state: per-costume frame list + cursor
	Common::HashMap<int, Common::Array<int>> _framesByCostume;
	Common::HashMap<int, int> _preloadCursor;
	// Hoechster vorhandener Einzelbildrahmen je (akosId, sub). Wird einmal ermittelt und
	// gemerkt: vorher lief fuer jeden angeforderten Rahmen eine Suche ueber die komplette
	// Liste der vorhandenen Kostueme, pro Koerperteil und Bild.
	Common::HashMap<uint64, int> _maxFrameCache;

	// Cache eviction budget (bytes) — current + previous room's costumes
	// stay cached; eviction only when the budget is exceeded.
	static const uint32 _cacheBudgetBytes = 1500 * 1024 * 1024;

	// ── Asynchroner Vorlauf (Weg (b)) ────────────────────────────────────────
	// Ein Worker dekodiert die angeforderten Cels, der Hauptthread traegt sie in
	// pumpAsync() ein. Geteilt sind nur diese drei Felder, alle Zugriffe unter
	// _asyncMutex; der Zwischenspeicher selbst wird ausschliesslich vom Hauptthread
	// angefasst (kein Zeiger aus dem Cache wird ungueltig).
	struct AsyncResult {
		CostumeKey key;
		Graphics::Surface surface;
		Common::Array<uint16> rowFirst;
		Common::Array<uint16> rowLast;
	};
	// Elaborierte Typnamen statt SDL.h im Header (forbidden.h in gfx.cpp vertraegt es nicht).
	struct SDL_mutex *_asyncMutex;
	struct SDL_Thread *_asyncThread;
	bool _asyncBusy;
	Common::Array<CostumeKey> _asyncKeys;    // laufender Auftrag
	Common::Array<AsyncResult> _asyncDone;   // fertig aufbereitet, wartet auf Eintrag


	// Base HD path
	Common::String _hdPath;

	/** Build path: hdPath/costumes/LFLF_{akosId}_AKOS_{akosSub}_aframe_{frame}.png */
	Common::String buildCostumePath(int akosId, int akosSub, int frame) const;

	/** Load a PNG file into a surface (reused from HdObjectManager pattern). */
	bool loadPNG(const Common::String &path, Graphics::Surface &surf);

	/** Evict old cache entries when over limit. */
	void pruneCache();
};

} // End of namespace Scumm

#endif
