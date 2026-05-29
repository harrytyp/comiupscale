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
	} else {
		warning("HDAssetManager: HD mode ENABLED at %s", _hdPath.c_str());
	}
}

bool HDAssetManager::hasBackground(int room) const {
	if (_hdPath.empty())
		return false;

	// Build expected path
	Common::String bgPath = _hdPath;
	bgPath += Common::String::format("/bg_%04d.png", room);

	Common::FSNode file(Common::Path(bgPath, Common::Path::kNativeSeparator));
	bool exists = file.exists();
	HD_TRACE(bgPath, exists);
	return exists;
}

bool HDAssetManager::loadBackground(int room, Graphics::Surface &surf) {
	if (_hdPath.empty())
		return false;

	// Build path: <hdPath>/bg_XXXX.png
	Common::String bgPath = _hdPath;
	bgPath += Common::String::format("/bg_%04d.png", room);

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

	surf.copyFrom(*pngSurf);

	// Convert 24-bit RGB to 32-bit RGBA if needed
	if (surf.format.bytesPerPixel == 3) {
		Graphics::Surface *conv = new Graphics::Surface();
		conv->create(surf.w, surf.h, Graphics::PixelFormat(4, 8, 8, 8, 8, 0, 8, 16, 24));
		const byte *src = (const byte *)surf.getPixels();
		byte *dst = (byte *)conv->getPixels();
		// PNG 24-bit RGB: bytes in memory are [R, G, B] (LE, createFormatRGB24).
		// SDL RGBA8888 expects bytes [R, G, B, A] in memory.
		for (int i = 0; i < surf.w * surf.h; i++) {
			dst[i * 4 + 0] = src[i * 3 + 0];  // R
			dst[i * 4 + 1] = src[i * 3 + 1];  // G
			dst[i * 4 + 2] = src[i * 3 + 2];  // B
			dst[i * 4 + 3] = 0xFF;            // A
		}
		surf.free();
		surf.copyFrom(*conv);
		conv->free();
		delete conv;
	}

	png.destroy();

	debug(1, "HDAssetManager: Loaded HD background for room %d: %dx%d (%s)",
		room, surf.w, surf.h, bgPath.c_str());
	return true;
}

} // End of namespace Scumm
