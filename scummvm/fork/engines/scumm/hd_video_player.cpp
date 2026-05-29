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

#if defined(_WIN32)
// Windows headers must come before ScummVM headers to avoid
// conflicts with common/forbidden.h
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#endif

#include "scumm/hd_video_player.h"
#include "common/config-manager.h"
#include "common/debug.h"
#include "common/fs.h"
#include "common/textconsole.h"

namespace Scumm {

// ── Tracing helper ────────────────────────────────────
#define HD_TRACE(path, exists) \
	do { \
		if (ConfMan.getBool("hd_trace", "comi")) \
			debug(0, "hd_trace: %s %s", (exists) ? "OK" : "MISS", (path).c_str()); \
	} while (0)

HdVideoPlayer::HdVideoPlayer()
	: _hdProcess(nullptr), _hdPipe(nullptr), _width(0), _height(0) {
}

HdVideoPlayer::~HdVideoPlayer() {
	close();
}

bool HdVideoPlayer::hasVideo(const Common::String &sanFilename) {
	Common::String baseName = sanFilename;
	int dotPos = baseName.findLastOf('.');
	if (dotPos > 0)
		baseName.erase(dotPos);

	// Filename mapping table: SAN base name → MP4 base name
	// Some archive.org videos have different filenames than the SAN files
	struct Mapping { const char *san; const char *mp4; };
	static const Mapping s_mappings[] = {
		{ "SINKSHP", "SINKSHIP" },  // SAN is "SINKSHP", MP4 is "SINKSHIP"
		{ nullptr, nullptr }         // sentinel
	};
	for (int i = 0; s_mappings[i].san; i++) {
		if (baseName.equalsIgnoreCase(s_mappings[i].san)) {
			baseName = s_mappings[i].mp4;
			break;
		}
	}

	// Build path from hd_path config, with fallback to game/hd/
	Common::FSNode hdDir;
	if (ConfMan.hasKey("hd_path", "comi")) {
		hdDir = Common::FSNode(Common::Path(ConfMan.get("hd_path", "comi"), Common::Path::kNativeSeparator));
	} else {
		Common::FSNode gameDataDir(ConfMan.getPath("path"));
		hdDir = gameDataDir.getChild("hd");
	}

	Common::FSNode videoDir = hdDir.getChild("videos");
	if (!videoDir.exists()) {
		// Videos directory not present — no HD video
		return false;
	}

	// Try exact case first, then lowercase, then uppercase
	Common::FSNode mp4File = videoDir.getChild(baseName + ".mp4");
	if (mp4File.exists()) { HD_TRACE(mp4File.getPath().toString(), true); return true; }

	Common::String lower = baseName;
	lower.toLowercase();
	mp4File = videoDir.getChild(lower + ".mp4");
	if (mp4File.exists()) { HD_TRACE(mp4File.getPath().toString(), true); return true; }

	Common::String upper = baseName;
	upper.toUppercase();
	mp4File = videoDir.getChild(upper + ".mp4");
	if (mp4File.exists()) { HD_TRACE(mp4File.getPath().toString(), true); return true; }

	// None found — log the last tried path
	Common::String lastTry = videoDir.getPath().toString() + "/" + baseName + ".mp4";
	HD_TRACE(lastTry, false);
	return false;
}

bool HdVideoPlayer::open(const Common::String &mp4Path, int width, int height) {
	close();

	_width = width;
	_height = height;

	Common::FSNode mp4Node(Common::Path(mp4Path, Common::Path::kNativeSeparator));
	HD_TRACE(mp4Path, mp4Node.exists());

#ifdef _WIN32
	// Build ffmpeg command
	Common::String ffmpegPath = "ffmpeg";
	if (ConfMan.hasKey("ffmpeg_path", "comi"))
		ffmpegPath = ConfMan.get("ffmpeg_path", "comi");

	Common::String cmd = Common::String::format(
		"%s -i \"%s\" -vf crop=2560:1920:160:120 -f rawvideo -pix_fmt rgba -an -loglevel error -",
		ffmpegPath.c_str(), mp4Path.c_str());

	// Set up pipe for reading ffmpeg stdout
	SECURITY_ATTRIBUTES sa;
	sa.nLength = sizeof(sa);
	sa.bInheritHandle = TRUE;
	sa.lpSecurityDescriptor = nullptr;

	HANDLE readPipe, writePipe;
	if (!CreatePipe(&readPipe, &writePipe, &sa, 0))
		return false;
	if (!SetHandleInformation(readPipe, HANDLE_FLAG_INHERIT, 0))
		return false;

	// Set up process info
	PROCESS_INFORMATION pi;
	ZeroMemory(&pi, sizeof(pi));

	STARTUPINFOA si;
	ZeroMemory(&si, sizeof(si));
	si.cb = sizeof(si);
	si.hStdError = writePipe;
	si.hStdOutput = writePipe;
	si.dwFlags |= STARTF_USESTDHANDLES;

	// Create ffmpeg process
	// Build a writeable copy of the command
	byte *cmdStr = new byte[cmd.size() + 1];
	memcpy(cmdStr, cmd.c_str(), cmd.size() + 1);
	BOOL result = CreateProcessA(nullptr, (LPSTR)cmdStr, nullptr, nullptr, TRUE,
		CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi);
	delete[] cmdStr;

	if (!result) {
		CloseHandle(readPipe);
		CloseHandle(writePipe);
		return false;
	}

	CloseHandle(writePipe);
	_hdProcess = pi.hProcess;
	_hdPipe = readPipe;

	_width = 2560;
	_height = 1920;
	return true;
#else
	// TODO: POSIX implementation with popen
	warning("HdVideoPlayer: not yet implemented on non-Windows");
	return false;
#endif
}

bool HdVideoPlayer::readFrame(byte *buffer) {
	if (!_hdPipe)
		return false;

	int frameSize = getFrameSize();
	int total = 0;

	while (total < frameSize) {
		DWORD bytesRead;
		if (!ReadFile(_hdPipe, buffer + total, frameSize - total, &bytesRead, nullptr))
			return false;
		if (bytesRead == 0)
			return false;
		total += bytesRead;
	}

	return true;
}

void HdVideoPlayer::close() {
#ifdef _WIN32
	if (_hdProcess) {
		// Wait for ffmpeg to finish (with timeout)
		WaitForSingleObject(_hdProcess, 5000);
		CloseHandle(_hdProcess);
		_hdProcess = nullptr;
	}
	if (_hdPipe) {
		CloseHandle(_hdPipe);
		_hdPipe = nullptr;
	}
#endif
}

} // End of namespace Scumm
