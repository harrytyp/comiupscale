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

#ifndef SCUMM_HD_VIDEO_PLAYER_H
#define SCUMM_HD_VIDEO_PLAYER_H

#include "common/scummsys.h"
#include "graphics/surface.h"

namespace Scumm {

/**
 * HD video player using ffmpeg via pipe to decode MP4 files.
 *
 * When a SMUSH cutscene plays, this class checks if an MP4 replacement
 * exists in the hd/videos/ directory. If so, it spawns ffmpeg.exe
 * as a subprocess and pipes raw BGRA frames for direct HD rendering.
 */
class HdVideoPlayer {
public:
	HdVideoPlayer();
	~HdVideoPlayer();

	/** Check if an MP4 replacement exists for the given SAN filename. */
	static bool hasVideo(const Common::String &sanFilename);

	/**
	 * Open an MP4 video file for playback.
	 * @param mp4Path  Full path to the MP4 file
	 * @param width    Expected frame width (e.g., 2880)
	 * @param height   Expected frame height (e.g., 2160)
	 * @return true if ffmpeg was spawned successfully
	 */
	bool open(const Common::String &mp4Path, int width, int height);

	/**
	 * Read the next frame into the provided buffer.
	 * Buffer must be at least getFrameSize() bytes.
	 * @return true if a frame was read, false on end/error
	 */
	bool readFrame(byte *buffer);

	/** Close the video and terminate ffmpeg. */
	void close();

	/** Check if a video is currently playing. */
	bool isPlaying() const { return _hdPipe != nullptr; }

	int getWidth() const { return _width; }
	int getHeight() const { return _height; }
	int getFrameSize() const { return _width * _height * 4; }

private:
#ifdef _WIN32
	void *_hdProcess;  // HANDLE (opaque)
	void *_hdPipe;     // HANDLE (opaque)
#else
	// TODO: POSIX pipe
	void *_hdPipe;
#endif
	int _width;
	int _height;
};

} // End of namespace Scumm

#endif
