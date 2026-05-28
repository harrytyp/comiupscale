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
	 * Load an HD costume frame for the given akosId and frame (searches all subs).
	 * The surface will be in RGBA8888 format if alpha exists,
	 * or RGB888 if no alpha channel.
	 * Returns true on success.
	 */
	bool loadCostume(int akosId, int frame, Graphics::Surface &dest);

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

	// Base HD path
	Common::String _hdPath;

	/** Build path: hdPath/costumes/LFLF_{akosId}_AKOS_{akosSub}_aframe_{frame}.png */
	Common::String buildCostumePath(int akosId, int akosSub, int frame) const;

	/** Load a PNG file into a surface (reused from HdObjectManager pattern). */
	bool loadPNG(const Common::String &path, Graphics::Surface &surf);

	/** Evict old cache entries when over limit. */
	void pruneCache(int maxEntries = 128);
};

} // End of namespace Scumm

#endif
