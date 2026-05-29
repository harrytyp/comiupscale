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
			warning("hd_trace: %s %s", (exists) ? "OK" : "MISS", (path).c_str()); \
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
	// Parameters: akosId=AKOS number, akosSub=LFLF owner
	// Filename format: LFLF_XXXX_AKOS_XXXX_aframe_X.png → LFLF_{lflf}_AKOS_{akos}_{frame}.png
	path += Common::String::format("/costumes/LFLF_%04d_AKOS_%04d_aframe_%d.png", akosSub, akosId, frame);
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

	Graphics::PixelFormat rgbaFmt(4, 8, 8, 8, 8, 0, 8, 16, 24);
	surf.create(pngSurf->w, pngSurf->h, rgbaFmt);

	// Convert pixels: copy RGB and set alpha to opaque
	for (int y = 0; y < pngSurf->h; y++) {
		const byte *src = (const byte *)pngSurf->getBasePtr(0, y);
		uint32 *dst = (uint32 *)surf.getBasePtr(0, y);
		int srcBpp = pngSurf->format.bytesPerPixel;
		for (int x = 0; x < pngSurf->w; x++) {
			byte r = src[x * srcBpp + 0];
			byte g = src[x * srcBpp + 1];
			byte b = src[x * srcBpp + 2];
			dst[x] = r | (g << 8) | (b << 16) | (0xFF << 24);
		}
	}
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

		int lflfOwner = 0, akosNumber = 0, frame = 0;
		// Filename: LFLF_XXXX_AKOS_XXXX_aframe_XXXXX.png
		//   LFLF_0087_AKOS_0439_aframe_0.png → lflfOwner=87, akosNumber=439, frame=0
		if (sscanf(name.c_str(), "LFLF_%d_AKOS_%d_aframe_%d", &lflfOwner, &akosNumber, &frame) >= 3) {
			CostumeKey key;
			key.akosId = akosNumber;  // AKOS resource ID (0439) is the primary key
			key.akosSub = lflfOwner;  // LFLF owner (0087) is the sub-group
			key.frame = frame;
			_availableCostumes[key] = true;
			count++;

			// Build per-AKOS sub list (akosId is the AKOS resource number)
			if (!_akosSubs.contains(akosNumber)) {
				_akosSubs[akosNumber] = Common::List<int>();
			}
			Common::List<int> &subs = _akosSubs[akosNumber];
			bool found = false;
			for (Common::List<int>::iterator si = subs.begin(); si != subs.end(); ++si) {
				if (*si == lflfOwner) { found = true; break; }
			}
			if (!found)
				subs.push_back(lflfOwner);
		}
	}

	_enabled = (count > 0);
	debug(1, "HdCostumeManager: Registered %d HD costume frames from %s", count, costumesDir.c_str());
	if (_enabled)
		warning("hd_trace: HdCostumeManager: %d HD costume frames available", count);
	return _enabled;
}

bool HdCostumeManager::hasCostume(int akosId, int frame) const {
	if (!_enabled)
		return false;

	// Check if any AKOS sub has this frame.
	// AKOS subs are different animation sets — we search all available
	// subs for the given AKOS ID to support non-base animation sets.
	typename Common::HashMap<int, Common::List<int> >::const_iterator subsIt = _akosSubs.find(akosId);
	if (subsIt == _akosSubs.end())
		return false;

	for (Common::List<int>::const_iterator si = subsIt->_value.begin(); si != subsIt->_value.end(); ++si) {
		int sub = *si;
		CostumeKey key;
		key.akosId = akosId;
		key.akosSub = sub;
		key.frame = frame;
		if (_availableCostumes.contains(key)) {
			Common::String p = buildCostumePath(akosId, sub, frame);
			HD_TRACE(p, true);
			return true;
		}
		// Exact frame not found — check if ANY frame exists for this (akos,sub).
		// If so, report available so the renderer tries to load the closest frame.
		CostumeKey anyKey;
		anyKey.akosId = akosId;
		anyKey.akosSub = sub;
		anyKey.frame = -1; // sentinel: not used in lookup
		// Search for any frame with this akosId+sub
		for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
		     it != _availableCostumes.end(); ++it) {
			if (it->_key.akosId == akosId && it->_key.akosSub == sub) {
				warning("hd_trace: costume %04d frame %d not available, but frame %d is — accepting",
					akosId, frame, it->_key.frame);
				return true;
			}
		}
	}
	// Log MISS for debugging
	warning("hd_trace: MISS costume akos=%d frame=%d (checked %d subs)", akosId, frame, (int)subsIt->_value.size());
	return false;
}

bool HdCostumeManager::loadCostume(int akosId, int frame, Graphics::Surface &dest) {
	if (!_enabled)
		return false;

	// Search all available subs for this AKOS ID
	if (!_akosSubs.contains(akosId))
		return false;

	for (Common::List<int>::const_iterator si = _akosSubs[akosId].begin(); si != _akosSubs[akosId].end(); ++si) {
		int sub = *si;
		CostumeKey key;
		key.akosId = akosId;
		key.akosSub = sub;
		key.frame = frame;

		// Check cache first
		Common::HashMap<CostumeKey, TextureCacheEntry, CostumeKeyHash>::iterator cacheIt = _textureCache.find(key);
		if (cacheIt != _textureCache.end()) {
			dest.copyFrom(cacheIt->_value.surface);
			cacheIt->_value.lastUsed = ++_lruCounter;
			return true;
		}

		// Try exact frame first, then fall back to any available frame
		Common::String path;
		int loadFrame = frame;
		CostumeKey exactKey = key;
		if (_availableCostumes.contains(exactKey)) {
			path = buildCostumePath(akosId, sub, frame);
		} else {
			// Find the closest available frame
			for (Common::HashMap<CostumeKey, bool, CostumeKeyHash>::const_iterator it = _availableCostumes.begin();
			     it != _availableCostumes.end(); ++it) {
				if (it->_key.akosId == akosId && it->_key.akosSub == sub) {
					loadFrame = it->_key.frame;
					key.frame = loadFrame;
					path = buildCostumePath(akosId, sub, loadFrame);
					warning("hd_trace: loading %s as fallback for frame %d", path.c_str(), frame);
					break;
				}
			}
		}
		if (path.empty())
			continue;

		Graphics::Surface surf;
		if (!loadPNG(path, surf))
			continue;

		// Add to cache
		TextureCacheEntry entry;
		entry.surface.copyFrom(surf);
		entry.lastUsed = ++_lruCounter;
		_textureCache[key] = entry;
		dest.copyFrom(surf);
		pruneCache(512);
		return true;
		}
	return false;
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
