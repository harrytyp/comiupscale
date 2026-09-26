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
class HdCostumeManager {
public:
	HdCostumeManager(ScummEngine *vm);
	~HdCostumeManager();

	/** Initialize by scanning the hd/costumes/ directory. */
	bool init(const Common::String &hdPath);

	/** Check if an HD costume frame exists for the given akosId and frame (searches all subs). */
	bool hasCostume(int akosId, int frame) const;

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
	 */
	bool loadCostume(int akosId, int frame, Graphics::Surface &dest,
	                 const Graphics::Surface **cachedOut = nullptr);
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

	/** Returns true if HD costume mode is active. */
	bool isEnabled() const { return _enabled; }

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
		// ACHTUNG: zurzeit nur vorbereitet, der Zeichenweg nutzt sie noch nicht. Der
		// Versuch, damit die durchsichtigen Raender zu ueberspringen, liess auch die
		// Wiederherstellung des HD-Hintergrunds ausfallen, wodurch 8-Bit-Reste
		// durchgeschienen waeren. Erst nutzen, wenn das mitgezogen ist.
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
