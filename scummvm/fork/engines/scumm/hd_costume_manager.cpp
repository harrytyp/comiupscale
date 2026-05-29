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

#include "scumm/hd_costume_manager.h"
#include "scumm/scumm.h"
#include "common/config-manager.h"
#include "common/debug.h"
#include "common/fs.h"
#include "image/png.h"

namespace Scumm {

// ── Tracing helper ────────────────────────────────────
#define HD_TRACE(path, exists) \
	do { \
		if (ConfMan.getBool("hd_trace", "comi")) \
			debug(0, "hd_trace: %s %s", (exists) ? "OK" : "MISS", (path).c_str()); \
	} while (0)

HdCostumeManager::HdCostumeManager(ScummEngine *vm)
	: _vm(vm), _enabled(false), _lruCounter(0) {
}

HdCostumeManager::~HdCostumeManager() {
	for (Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator it = _textureCache.begin();
		 it != _textureCache.end(); ++it) {
		it->_value.surface.free();
	}
	_textureCache.clear();
	_availableCostumes.clear();
}

Common::String HdCostumeManager::buildCostumePath(int akosId, int akosSub, int frame) const {
	Common::String path = _hdPath;
	path += Common::String::format("/costumes/LFLF_%04d_AKOS_%04d_aframe_%d.png", akosId, akosSub, frame);
	return path;
}

bool HdCostumeManager::loadPNG(const Common::String &path, Graphics::Surface &surf) {
	Common::FSNode fileNode(Common::Path(path, Common::Path::kNativeSeparator));
	if (!fileNode.exists()) {
		HD_TRACE(path, false);
		return false;
	}
	HD_TRACE(path, true);

	Common::SeekableReadStream *stream = fileNode.createReadStream();
	if (!stream) {
		debug(2, "HdCostumeManager: Failed to open %s", path.c_str());
		return false;
	}

	Image::PNGDecoder png;
	if (!png.loadStream(*stream)) {
		debug(2, "HdCostumeManager: Failed to decode PNG: %s", path.c_str());
		delete stream;
		return false;
	}
	delete stream;

	const Graphics::Surface *pngSurf = png.getSurface();
	if (!pngSurf) {
		debug(2, "HdCostumeManager: No surface from PNG decoder");
		return false;
	}

	surf.copyFrom(*pngSurf);
	png.destroy();
	return true;
}

bool HdCostumeManager::init(const Common::String &hdPath) {
	_hdPath = hdPath;
	if (_hdPath.empty())
		return false;

	// Trim trailing separator
	if (_hdPath.lastChar() == '/' || _hdPath.lastChar() == '\\')
		_hdPath.deleteLastChar();

	Common::String costumesDir = _hdPath + "/costumes";
	Common::FSNode dirNode(Common::Path(costumesDir, Common::Path::kNativeSeparator));
	if (!dirNode.exists() || !dirNode.isDirectory()) {
		debug(1, "HdCostumeManager: costumes directory not found at %s, HD costumes disabled", costumesDir.c_str());
		_enabled = false;
		return false;
	}

	// Scan for available costume PNGs
	Common::FSList files;
	if (!dirNode.getChildren(files, Common::FSNode::kListFilesOnly)) {
		_enabled = false;
		return false;
	}

	int count = 0;
	for (Common::FSList::iterator it = files.begin(); it != files.end(); ++it) {
		Common::String name = it->getName();
		// Pattern: LFLF_{akos:04d}_AKOS_{sub:04d}_aframe_{frame}.png
		if (!name.hasPrefixIgnoreCase("LFLF_") || !name.hasSuffixIgnoreCase(".png"))
			continue;

		int akosId = 0, akosSub = 0, frame = 0;
		// Parse: LFLF_XXXX_AKOS_XXXX_aframe_XXXXX.png
		if (sscanf(name.c_str(), "LFLF_%d_AKOS_%d_aframe_%d", &akosId, &akosSub, &frame) >= 3) {
			CostumeKey key;
			key.akosId = akosId;
			key.akosSub = akosSub;
			key.frame = frame;
			_availableCostumes[key] = true;
			count++;

			// Build per-AKOS sub list
			if (!_akosSubs.contains(akosId)) {
				_akosSubs[akosId] = Common::List<int>();
			}
			Common::List<int> &subs = _akosSubs[akosId];
			bool found = false;
			for (Common::List<int>::iterator si = subs.begin(); si != subs.end(); ++si) {
				if (*si == akosSub) { found = true; break; }
			}
			if (!found)
				subs.push_back(akosSub);
		}
	}

	_enabled = (count > 0);
	debug(1, "HdCostumeManager: Registered %d HD costume frames from %s", count, costumesDir.c_str());
	return _enabled;
}

bool HdCostumeManager::hasCostume(int akosId, int frame) const {
	if (!_enabled)
		return false;

	// Only use sub=1 (base animation set).
	// AKOS subs are different animation sets — the actor's _frame value is
	// relative to the CURRENT sub, which we can't determine here.
	// Using other subs would cause wrong animations (e.g. banjo in cannon room).
	CostumeKey key;
	key.akosId = akosId;
	key.akosSub = 1;
	key.frame = frame;
	bool exists = _availableCostumes.contains(key);
	if (exists) {
		Common::String p = buildCostumePath(akosId, 1, frame);
		HD_TRACE(p, true);
	}
	return exists;
}

bool HdCostumeManager::loadCostume(int akosId, int frame, Graphics::Surface &dest) {
	if (!_enabled)
		return false;

	// Only use sub=1 (base animation set)
	CostumeKey key;
	key.akosId = akosId;
	key.akosSub = 1;
	key.frame = frame;

	// Check cache first
	Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator cacheIt = _textureCache.find(key);
	if (cacheIt != _textureCache.end()) {
		dest.copyFrom(cacheIt->_value.surface);
		cacheIt->_value.lastUsed = ++_lruCounter;
		return true;
	}

	// Load from disk
	Common::String path = buildCostumePath(akosId, 1, frame);
	Graphics::Surface surf;
	if (!loadPNG(path, surf))
		return false;

	// Add to cache
	TextureCacheEntry entry;
	entry.surface.copyFrom(surf);
	entry.lastUsed = ++_lruCounter;
	_textureCache[key] = entry;

	dest.copyFrom(surf);
	surf.free();

	pruneCache(512);

	debug(2, "HdCostumeManager: Loaded costume %04d/%04d frame %d (%dx%d) from %s",
		  akosId, 1, frame, dest.w, dest.h, path.c_str());

	return true;
}

void HdCostumeManager::pruneCache(int maxEntries) {
	while ((int)_textureCache.size() > maxEntries) {
		// Find least recently used
		CostumeKey oldestKey = _textureCache.begin()->_key;
		int oldestTime = _lruCounter;
		for (Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator it = _textureCache.begin();
			 it != _textureCache.end(); ++it) {
			if (it->_value.lastUsed < oldestTime) {
				oldestTime = it->_value.lastUsed;
				oldestKey = it->_key;
			}
		}
		_textureCache[oldestKey].surface.free();
		_textureCache.erase(oldestKey);
	}
}

} // End of namespace Scumm
