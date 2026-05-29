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

#ifndef SCUMM_HD_ASSET_MANAGER_H
#define SCUMM_HD_ASSET_MANAGER_H

#include "common/str.h"
#include "common/stream.h"
#include "graphics/surface.h"

namespace Scumm {

class ScummEngine;

/**
 * Manager for HD replacement assets for the ScummVM fork.
 * Loads upscaled textures from an external hd/ directory
 * next to the game data files.
 */
class HDAssetManager {
public:
	HDAssetManager(ScummEngine *vm);
	~HDAssetManager();

	/** Load the HD background for a given room. Returns true if successful. */
	bool loadBackground(int room, Graphics::Surface &surf);

	/** Check if an HD background exists for a room. */
	bool hasBackground(int room) const;

	/** Set the base path for HD assets (usually game path + "/hd"). */
	void setHDPath(const Common::String &path);

	/** Set the global scale factor. */
	void setScale(int s) { _scale = s; }

	/** Get the global scale factor (HD texture width / game width when loaded). */
	int getScale() const { return _scale; }

	/** Returns true if HD mode is active (directory was found). */
	bool isEnabled() const { return !_hdPath.empty(); }

private:
	ScummEngine *_vm;
	Common::String _hdPath;
	int _scale;
};

} // End of namespace Scumm

#endif
