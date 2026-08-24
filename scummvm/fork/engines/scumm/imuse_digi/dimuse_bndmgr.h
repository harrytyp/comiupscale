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

#ifndef SCUMM_IMUSE_DIGI_BUNDLE_MGR_H
#define SCUMM_IMUSE_DIGI_BUNDLE_MGR_H

#include "common/scummsys.h"
#include "common/file.h"
#include "scumm/imuse_digi/dimuse_defs.h"

namespace Scumm {

class BaseScummFile;

class BundleDirCache {
public:
	struct AudioTable {
		char filename[24];
		int32 offset;
		int32 size;
	};

	struct IndexNode {
		char filename[24];
		int32 index;
	};

private:

	struct FileDirCache {
		char fileName[20];
		AudioTable *bundleTable;
		int32 numFiles;
		bool isCompressed;
		IndexNode *indexTable;
	} _bundleDirCache[4];

	const ScummEngine *_vm;
public:
	BundleDirCache(const ScummEngine *vm);
	~BundleDirCache();

	int matchFile(const char *filename);
	AudioTable *getTable(int slot);
	IndexNode *getIndexTable(int slot);
	int32 getNumFiles(int slot);
	bool isSndDataExtComp(int slot);
};

class BundleMgr {

private:
	struct CompTable {
		int32 offset;
		int32 size;
		int32 codec;
	};

	BundleDirCache *_cache;
	BundleDirCache::AudioTable *_bundleTable;
	BundleDirCache::IndexNode *_indexTable = nullptr;
	CompTable *_compTable;

	int _numFiles = 0;
	int _numCompItems = 0;
	int _lastBlockDecompressedSize = 0;
	int _curSampleId = 0;
	int _curDecompressedFilePos = 0;
	BaseScummFile *_file;
	bool _compTableLoaded = 0;
	bool _isUncompressed = 0;
	int _fileBundleId = 0;
	byte _compOutputBuff[0x2000] = {};
	byte *_compInputBuff = nullptr;
	int _outputSize = 0;
	int _lastBlock = 0;
	bool loadCompTable(int32 index);

	// Issue #19: CD-quality external music tracks (WAV drop-in).
	// When a sound is not found in the bundle, try "<name>.wav" next to the
	// game data. The WAV (44.1k/22.05k 16-bit stereo/mono PCM) is streamed
	// through the same readFile() path with a synthetic iMUS/MAP/FRMT header
	// so the iMUSE dispatch parser is unchanged.
	Common::SeekableReadStream *_extStream = nullptr;
	Common::String _extTrackName;        // which track the external stream is for
	int32 _extStreamDataOffset = 0;  // byte offset of PCM data inside the WAV
	int32 _extStreamDataLen = 0;     // PCM data length in bytes
	byte _extHeader[64];             // synthetic iMUS/MAP/FRMT header (52 bytes used)
	bool _extHeaderSent = false;
	bool _extHashLogged = false;      // hash of first bytes logged once
	int32 _extReadTotal = 0;         // bytes of header+PCM handed out so far
	void openExternal(const char *name);
	void closeExternal();

public:

	BundleMgr(const ScummEngine *vm, BundleDirCache *_cache);
	~BundleMgr();

	bool open(const char *filename, bool &isCompressed, bool errorFlag = false);
	void close();
	Common::SeekableReadStream *getFile(const char *filename, int32 &offset, int32 &size);
	int32 seekFile(int32 offset, int size);
	int32 readFile(const char *name, int32 size, byte **compFinal, bool headerOutside);
	int32 readFileExternal(const char *name, int32 size, byte **compFinal);
	bool isExtCompBun(byte gameId);
};

} // End of namespace Scumm

#endif
