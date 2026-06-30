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

#include "scumm/hd_asset_manager.h"
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

HDAssetManager::HDAssetManager(ScummEngine *vm)
	: _vm(vm), _scale(4) {
}

HDAssetManager::~HDAssetManager() {
	_bgFiles.clear();
}

void HDAssetManager::setHDPath(const Common::String &path) {
	_hdPath = path;
	// Trim trailing slash
	if (!_hdPath.empty() && (_hdPath.lastChar() == '/' || _hdPath.lastChar() == '\\'))
		_hdPath.deleteLastChar();

	debug(1, "HDAssetManager: HD path set to %s", _hdPath.c_str());

	// Check if HD directory exists
	Common::FSNode dir(Common::Path(_hdPath, Common::Path::kNativeSeparator));
	if (!dir.exists() || !dir.isDirectory()) {
		debug(1, "HDAssetManager: HD directory not found, HD mode disabled");
		_hdPath.clear();
		return;
	}
	warning("HDAssetManager: HD mode ENABLED at %s", _hdPath.c_str());

	// Scan backgrounds directory for room→filename mapping
	scanBackgrounds();
}

void HDAssetManager::scanBackgrounds() {
	_bgFiles.clear();

	Common::String bgDirPath = _hdPath + "/backgrounds";
	Common::FSNode bgDir(Common::Path(bgDirPath, Common::Path::kNativeSeparator));
	if (!bgDir.exists() || !bgDir.isDirectory()) {
		debug(1, "HDAssetManager: No backgrounds/ subdirectory at %s", bgDirPath.c_str());
		return;
	}

	Common::FSList files;
	if (!bgDir.getChildren(files, Common::FSNode::kListFilesOnly)) {
		debug(1, "HDAssetManager: Failed to list backgrounds directory");
		return;
	}

	int count = 0;
	for (Common::FSList::iterator it = files.begin(); it != files.end(); ++it) {
		Common::String name = it->getName();
		if (!name.hasSuffixIgnoreCase(".png"))
			continue;

		// Extract room number from "ROOMNAME_..." or "bg_ROOM_..." pattern
		int room = 0;
		if (sscanf(name.c_str(), "%d", &room) == 1 || sscanf(name.c_str(), "bg_%d", &room) == 1) {
			Common::String fullPath = bgDirPath + "/" + name;
			_bgFiles[room] = fullPath;
			count++;
		}
	}

	debug(1, "HDAssetManager: Scanned %d backgrounds from %s", count, bgDirPath.c_str());
}

bool HDAssetManager::hasBackground(int room) const {
	if (_hdPath.empty())
		return false;

	return _bgFiles.contains(room);
}

bool HDAssetManager::loadBackground(int room, Graphics::Surface &surf) {
	if (_hdPath.empty())
		return false;

	if (!_bgFiles.contains(room)) {
		HD_TRACE(Common::String::format("bg room %d", room), false);
		return false;
	}

	Common::String bgPath = _bgFiles[room];
	Common::FSNode fileNode(Common::Path(bgPath, Common::Path::kNativeSeparator));
	if (!fileNode.exists()) {
		HD_TRACE(bgPath, false);
		return false;
	}
	HD_TRACE(bgPath, true);

	Common::SeekableReadStream *stream = fileNode.createReadStream();
	if (!stream) {
		warning("HDAssetManager: Failed to open %s", bgPath.c_str());
		return false;
	}

	Image::PNGDecoder png;
	if (!png.loadStream(*stream)) {
		warning("HDAssetManager: Failed to decode PNG: %s", bgPath.c_str());
		delete stream;
		return false;
	}
	delete stream;

	const Graphics::Surface *pngSurf = png.getSurface();
	if (!pngSurf) {
		warning("HDAssetManager: No surface from PNG decoder");
		return false;
	}

		// Convert 24-bit RGB PNGs (3 bytes/pixel) to 32-bit RGBA
		// because ScummVM's fillRect etc. don't support 3 bytes/pixel.
		if (pngSurf->format.bytesPerPixel == 3) {
				warning("HDAssetManager: Converting 24-bit PNG to 32-bit RGBA");
			Graphics::PixelFormat dstFmt(4, 8, 8, 8, 8, 24, 16, 8, 0); // 32-bit RGBA
			surf.create(pngSurf->w, pngSurf->h, dstFmt);
			// Manual pixel conversion: RGB24 → RGBA32 (alpha = 255)
			for (int y = 0; y < pngSurf->h; ++y) {
				const byte *src = (const byte *)pngSurf->getBasePtr(0, y);
				byte *dst = (byte *)surf.getBasePtr(0, y);
				for (int x = 0; x < pngSurf->w; ++x) {
					dst[0] = src[0]; // R
					dst[1] = src[1]; // G
					dst[2] = src[2]; // B
					dst[3] = 255;    // A
					src += 3;
					dst += 4;
				}
			}
		} else {
			surf.copyFrom(*pngSurf);
		}
		png.destroy();
		return true;
	}

} // End of namespace Scumm
