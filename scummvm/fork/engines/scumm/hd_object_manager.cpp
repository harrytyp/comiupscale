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

#include "scumm/hd_object_manager.h"
#include "scumm/scumm.h"
#include "common/config-manager.h"
#include "common/debug.h"
#include "common/formats/json.h"
#include "common/fs.h"
#include "common/memstream.h"
#include "image/png.h"

namespace Scumm {

// ── Tracing helper ────────────────────────────────────
#define HD_TRACE(path, exists) \
	do { \
		if (ConfMan.getBool("hd_trace", "comi")) \
			debug(0, "hd_trace: %s %s", (exists) ? "OK" : "MISS", (path).c_str()); \
	} while (0)

HdObjectManager::HdObjectManager(ScummEngine *vm)
	: _vm(vm), _enabled(false), _lruCounter(0) {
}

HdObjectManager::~HdObjectManager() {
	// Free all cached surfaces
	for (Common::HashMap<Common::String, TextureCacheEntry>::iterator it = _textureCache.begin();
		 it != _textureCache.end(); ++it) {
		it->_value.surface.free();
	}
	_textureCache.clear();
}

Common::String HdObjectManager::buildObjectPath(int room, const Common::String &name, int state) const {
	Common::String path = _hdPath;
	path += Common::String::format("/objects/%04d_%s_%04d.png", room, name.c_str(), state);
	return path;
}

Common::String HdObjectManager::buildLayerPath(int room, const Common::String &name, int state) const {
	Common::String path = _hdPath;
	path += Common::String::format("/objects_layers/%04d_%s_%04d.png", room, name.c_str(), state);
	return path;
}

bool HdObjectManager::loadPNG(const Common::String &path, Graphics::Surface &surf) {
	Common::FSNode fileNode(Common::Path(path, Common::Path::kNativeSeparator));
	if (!fileNode.exists()) {
		HD_TRACE(path, false);
		return false;
	}
	HD_TRACE(path, true);

	Common::SeekableReadStream *stream = fileNode.createReadStream();
	if (!stream) {
		debug(2, "HdObjectManager: Failed to open %s", path.c_str());
		return false;
	}

	Image::PNGDecoder png;
	if (!png.loadStream(*stream)) {
		debug(2, "HdObjectManager: Failed to decode PNG: %s", path.c_str());
		delete stream;
		return false;
	}
	delete stream;

	const Graphics::Surface *pngSurf = png.getSurface();
	if (!pngSurf) {
		debug(2, "HdObjectManager: No surface from PNG decoder");
		return false;
	}

	surf.copyFrom(*pngSurf);

	// Convert 24-bit RGB to 32-bit RGBA if needed
	if (surf.format.bytesPerPixel == 3) {
		Graphics::Surface *conv = new Graphics::Surface();
		conv->create(surf.w, surf.h, Graphics::PixelFormat(4, 8, 8, 8, 8, 0, 8, 16, 24));
		const byte *src = (const byte *)surf.getPixels();
		byte *dst = (byte *)conv->getPixels();
		for (int i = 0; i < surf.w * surf.h; i++) {
			dst[i * 4 + 0] = src[i * 3 + 0];
			dst[i * 4 + 1] = src[i * 3 + 1];
			dst[i * 4 + 2] = src[i * 3 + 2];
			dst[i * 4 + 3] = 0xFF;
		}
		surf.free();
		surf.copyFrom(*conv);
		conv->free();
		delete conv;
	}

	png.destroy();
	return true;
}

bool HdObjectManager::init(const Common::String &hdPath) {
	_hdPath = hdPath;
	if (!_hdPath.empty() && (_hdPath.lastChar() == '/' || _hdPath.lastChar() == '\\'))
		_hdPath.deleteLastChar();

	// Build path to mapping file
	Common::String mapPath = _hdPath + "/object_map.json";
	Common::FSNode mapNode(Common::Path(mapPath, Common::Path::kNativeSeparator));
	if (!mapNode.exists()) {
		HD_TRACE(mapPath, false);
		warning("HdObjectManager: object_map.json not found at %s — HD objects disabled", mapPath.c_str());
		_enabled = false;
		return false;
	}
	HD_TRACE(mapPath, true);

	// Read the mapping file
	Common::SeekableReadStream *stream = mapNode.createReadStream();
	if (!stream) {
		warning("HdObjectManager: Failed to open %s", mapPath.c_str());
		_enabled = false;
		return false;
	}

	// Read entire file into a memory stream
	Common::MemoryWriteStreamDynamic memStream(DisposeAfterUse::NO);
	byte buf[4096];
	while (!stream->eos()) {
		int32 n = stream->read(buf, sizeof(buf));
		if (n > 0)
			memStream.write(buf, n);
	}
	delete stream;

	// Zero-terminate for JSON parser
	char *jsonStr = Common::JSON::zeroTerminateContents(memStream);
	Common::String jsonData(jsonStr);
	delete[] jsonStr;

	// Parse JSON
	Common::JSONValue *root = Common::JSON::parse(jsonData);
	if (!root || !root->isObject()) {
		warning("HdObjectManager: Failed to parse object_map.json");
		delete root;
		_enabled = false;
		return false;
	}

	// Iterate over all object entries
	const Common::JSONObject &objMap = root->asObject();
	for (Common::JSONObject::const_iterator it = objMap.begin(); it != objMap.end(); ++it) {
		int objId = atol(it->_key.c_str());
		Common::JSONValue *entryVal = it->_value;
		if (!entryVal->isObject()) continue;

		const Common::JSONObject &entry = entryVal->asObject();

		Common::JSONValue *nameVal = entryVal->child("name");
		if (!nameVal || !nameVal->isString()) continue;
		Common::String name = nameVal->asString();

		ObjectInfo info;
		info.name = name;

		Common::JSONValue *roomsVal = entryVal->child("rooms");
		if (roomsVal && roomsVal->isObject()) {
			const Common::JSONObject &rooms = roomsVal->asObject();
			for (Common::JSONObject::const_iterator rit = rooms.begin(); rit != rooms.end(); ++rit) {
				int roomId = atol(rit->_key.c_str());
				Common::JSONValue *roomVal = rit->_value;
				if (!roomVal->isObject()) continue;

				Common::JSONValue *statesVal = roomVal->child("states");
				if (statesVal && statesVal->isArray()) {
					const Common::JSONArray &states = statesVal->asArray();
					for (uint i = 0; i < states.size(); i++) {
						info.roomStates[roomId].push_back(states[i]->asIntegerNumber());
					}
				}
			}
		}

		_objectMap[objId] = info;
		_nameToId[name] = objId;
	}

	delete root;
	_enabled = true;
	debug(1, "HdObjectManager: Loaded %d object mappings from %s", _objectMap.size(), mapPath.c_str());
	return true;
}

bool HdObjectManager::hasObject(int obj_nr, int room, int state) const {
	if (!_enabled)
		return false;

	// Check if obj_nr exists in map
	const Common::HashMap<int, ObjectInfo>::const_iterator it = _objectMap.find(obj_nr);
	if (it == _objectMap.end())
		return false;

	const ObjectInfo &info = it->_value;

	// Check if this room has the object
	const Common::HashMap<int, Common::List<int>>::const_iterator rit = info.roomStates.find(room);
	if (rit != info.roomStates.end()) {
		// Check if the state exists
		for (Common::List<int>::const_iterator sit = rit->_value.begin(); sit != rit->_value.end(); ++sit) {
			if (*sit == state)
				return true;
		}
	}

	// Fallback: try any other room in the mapping (inventory items, etc.)
	for (Common::HashMap<int, Common::List<int>>::const_iterator oit = info.roomStates.begin();
		 oit != info.roomStates.end(); ++oit) {
		if (oit->_key == room)
			continue;
		for (Common::List<int>::const_iterator sit = oit->_value.begin();
			 sit != oit->_value.end(); ++sit) {
			if (*sit == state)
				return true;
		}
	}

	return false;
}

bool HdObjectManager::loadObject(int obj_nr, int room, int state, Graphics::Surface &dest) {
	if (!_enabled)
		return false;

	Common::HashMap<int, ObjectInfo>::iterator it = _objectMap.find(obj_nr);
	if (it == _objectMap.end())
		return false;

	const ObjectInfo &info = it->_value;

	// Try to load standalone object file first, then fall back to layer files.
	// Layer files are pre-composited on the full background (2560x1920) and
	// NOT suitable for runtime compositing — they would overwrite the whole screen.
	Common::String objPath = buildObjectPath(room, info.name, state);
	Common::String cacheKey;

	// Check cache
	Common::HashMap<Common::String, TextureCacheEntry>::iterator cacheIt = _textureCache.find(objPath);
	if (cacheIt != _textureCache.end()) {
		cacheIt->_value.lastUsed = ++_lruCounter;
		dest.copyFrom(cacheIt->_value.surface);
		return true;
	}

	// Not in cache — load from disk
	Graphics::Surface surf;
	if (loadPNG(objPath, surf)) {
		cacheKey = objPath;
	} else {
		// Fallback: try alternate rooms (e.g. inventory items stored in room 3
		// but referenced from the player's current room).
		for (Common::HashMap<int, Common::List<int>>::const_iterator rit = info.roomStates.begin();
			 rit != info.roomStates.end(); ++rit) {
			int altRoom = rit->_key;
			if (altRoom == room)
				continue;
			// Check if this room supports the requested state
			bool hasState = false;
			for (Common::List<int>::const_iterator sit = rit->_value.begin();
				 sit != rit->_value.end(); ++sit) {
				if (*sit == state) {
					hasState = true;
					break;
				}
			}
			if (!hasState)
				continue;
			Common::String altPath = buildObjectPath(altRoom, info.name, state);
			cacheIt = _textureCache.find(altPath);
			if (cacheIt != _textureCache.end()) {
				cacheIt->_value.lastUsed = ++_lruCounter;
				dest.copyFrom(cacheIt->_value.surface);
				return true;
			}
			if (loadPNG(altPath, surf)) {
				objPath = altPath;
				cacheKey = altPath;
				break;
			}
		}
		if (cacheKey.empty())
			return false;
	}

	// Add to cache
	pruneCache();
	TextureCacheEntry entry;
	entry.surface.copyFrom(surf);
	entry.lastUsed = ++_lruCounter;
	_textureCache[cacheKey] = entry;

	dest.copyFrom(surf);
	surf.free();
	return true;
}

Common::String HdObjectManager::getObjectName(int obj_nr) const {
	const Common::HashMap<int, ObjectInfo>::const_iterator it = _objectMap.find(obj_nr);
	if (it != _objectMap.end())
		return it->_value.name;
	return Common::String();
}

int HdObjectManager::findObjectRoom(int obj_nr) const {
	const Common::HashMap<int, ObjectInfo>::const_iterator it = _objectMap.find(obj_nr);
	if (it == _objectMap.end())
		return -1;
	const Common::HashMap<int, Common::List<int>> &rooms = it->_value.roomStates;
	if (rooms.empty())
		return -1;
	return rooms.begin()->_key;
}

void HdObjectManager::pruneCache(int maxEntries) {
	// Simple LRU: when cache exceeds maxEntries, remove oldest entries
	while ((int)_textureCache.size() > maxEntries) {
		Common::HashMap<Common::String, TextureCacheEntry>::iterator oldest = _textureCache.begin();
		for (Common::HashMap<Common::String, TextureCacheEntry>::iterator it = _textureCache.begin();
			 it != _textureCache.end(); ++it) {
			if (it->_value.lastUsed < oldest->_value.lastUsed)
				oldest = it;
		}
		oldest->_value.surface.free();
		_textureCache.erase(oldest);
	}
}

} // End of namespace Scumm
