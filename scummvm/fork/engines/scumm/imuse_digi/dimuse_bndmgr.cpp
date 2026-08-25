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


#include "common/scummsys.h"
#include "scumm/scumm.h"
#include "scumm/util.h"
#include "scumm/file.h"
#include "scumm/imuse_digi/dimuse_bndmgr.h"
#include "scumm/imuse_digi/dimuse_codecs.h"
#include "scumm/imuse_digi/dimuse_extmusic_table.h"
#include "scumm/hd_asset_manager.h"
#include "common/debug.h"

namespace Scumm {

BundleDirCache::BundleDirCache(const ScummEngine *vm) : _vm(vm) {
	for (int fileId = 0; fileId < ARRAYSIZE(_bundleDirCache); fileId++) {
		_bundleDirCache[fileId].bundleTable = nullptr;
		_bundleDirCache[fileId].fileName[0] = 0;
		_bundleDirCache[fileId].numFiles = 0;
		_bundleDirCache[fileId].isCompressed = false;
		_bundleDirCache[fileId].indexTable = nullptr;
	}
}

BundleDirCache::~BundleDirCache() {
	for (int fileId = 0; fileId < ARRAYSIZE(_bundleDirCache); fileId++) {
		free(_bundleDirCache[fileId].bundleTable);
		free(_bundleDirCache[fileId].indexTable);
	}
}

BundleDirCache::AudioTable *BundleDirCache::getTable(int slot) {
	return _bundleDirCache[slot].bundleTable;
}

int32 BundleDirCache::getNumFiles(int slot) {
	return _bundleDirCache[slot].numFiles;
}

BundleDirCache::IndexNode *BundleDirCache::getIndexTable(int slot) {
	return _bundleDirCache[slot].indexTable;
}

bool BundleDirCache::isSndDataExtComp(int slot) {
	return _bundleDirCache[slot].isCompressed;
}

int BundleDirCache::matchFile(const char *filename) {
	int32 tag, offset;
	bool found = false;
	int freeSlot = -1;
	int fileId;

	for (fileId = 0; fileId < ARRAYSIZE(_bundleDirCache); fileId++) {
		if ((_bundleDirCache[fileId].bundleTable == nullptr) && (freeSlot == -1)) {
			freeSlot = fileId;
		}
		if (scumm_stricmp(filename, _bundleDirCache[fileId].fileName) == 0) {
			found = true;
			break;
		}
	}

	if (!found) {
		ScummFile file(_vm);

		if (g_scumm->openFile(file, filename) == false) {
			error("BundleDirCache::matchFile() Can't open bundle file: %s", filename);
			return false;
		}

		if (freeSlot == -1)
			error("BundleDirCache::matchFileFile() Can't find free slot for file bundle dir cache");

		tag = file.readUint32BE();
		if (tag == MKTAG('L','B','2','3'))
			_bundleDirCache[freeSlot].isCompressed = true;
		offset = file.readUint32BE();

		Common::strlcpy(_bundleDirCache[freeSlot].fileName, filename, sizeof(_bundleDirCache[freeSlot].fileName));
		_bundleDirCache[freeSlot].numFiles = file.readUint32BE();
		_bundleDirCache[freeSlot].bundleTable = (AudioTable *)malloc(_bundleDirCache[freeSlot].numFiles * sizeof(AudioTable));
		assert(_bundleDirCache[freeSlot].bundleTable);

		file.seek(offset, SEEK_SET);

		_bundleDirCache[freeSlot].indexTable =
				(IndexNode *)calloc(_bundleDirCache[freeSlot].numFiles, sizeof(IndexNode));
		assert(_bundleDirCache[freeSlot].indexTable);

		for (int32 i = 0; i < _bundleDirCache[freeSlot].numFiles; i++) {
			char name[24], c;
			int32 z = 0;
			int32 z2;

			if (tag == MKTAG('L','B','2','3')) {
				file.read(_bundleDirCache[freeSlot].bundleTable[i].filename, 24);
			} else {
				for (z2 = 0; z2 < 8; z2++)
					if ((c = file.readByte()) != 0)
						name[z++] = c;
				name[z++] = '.';
				for (z2 = 0; z2 < 4; z2++)
					if ((c = file.readByte()) != 0)
						name[z++] = c;

				name[z] = '\0';
				Common::strlcpy(_bundleDirCache[freeSlot].bundleTable[i].filename, name, sizeof(_bundleDirCache[freeSlot].bundleTable[i].filename));
			}
			_bundleDirCache[freeSlot].bundleTable[i].offset = file.readUint32BE();
			_bundleDirCache[freeSlot].bundleTable[i].size = file.readUint32BE();
			Common::strlcpy(_bundleDirCache[freeSlot].indexTable[i].filename, _bundleDirCache[freeSlot].bundleTable[i].filename, sizeof(_bundleDirCache[freeSlot].indexTable[i].filename));
			_bundleDirCache[freeSlot].indexTable[i].index = i;
		}
		qsort(_bundleDirCache[freeSlot].indexTable, _bundleDirCache[freeSlot].numFiles,
				sizeof(IndexNode), (int (*)(const void *, const void *))scumm_stricmp);
		return freeSlot;
	} else {
		return fileId;
	}
}

BundleMgr::BundleMgr(const ScummEngine *vm, BundleDirCache *cache) {
	_cache = cache;
	_vm = vm;
	_bundleTable = nullptr;
	_compTable = nullptr;
	_numFiles = 0;
	_numCompItems = 0;
	_lastBlockDecompressedSize = 0;
	_curSampleId = -1;
	_fileBundleId = -1;
	_file = new ScummFile(vm);
	_compInputBuff = nullptr;
}

BundleMgr::~BundleMgr() {
	close();
	delete _file;
}

// Issue #19: try to open the CD-quality music for a game cue.
// The cue name (e.g. "1099-M~1.IMX") is looked up in kExtMusicTable to
// find the OST file base name (e.g. "ost_01_The_Adventure_Continues"),
// then "<hd>/audio/<ost>.wav" is opened. Files keep their original
// archive.org names — the mapping table does the translation.
void BundleMgr::openExternal(const char *name) {
	closeExternal();
	_extTrackName = name;

	// Look up the cue in the music table
	const char *ostBase = nullptr;
	for (int i = 0; i < kExtMusicTableSize; i++) {
		if (scumm_stricmp(kExtMusicTable[i].cue, name) == 0) {
			ostBase = kExtMusicTable[i].ost;
			break;
		}
	}
	if (!ostBase) {
		debug(3, "HQ-MUSIC: no OST mapping for cue %s", name);
		return;
	}

	// Build <hd>/audio/<ost>.wav — same FSNode pattern as HDAssetManager
	// (which provably works on Windows for the hd/ assets).
	Common::String hdPath = _vm->_hdAssetManager ? _vm->_hdAssetManager->getHDPath() : "";
	if (hdPath.empty()) {
		warning("HQ-MUSIC: no HD path, skipping %s", name);
		return;
	}
	Common::Path wavPath(Common::String(hdPath) + "/audio/" + ostBase + ".wav", Common::Path::kNativeSeparator);
	Common::FSNode wavNode(wavPath);
	if (!wavNode.exists() || wavNode.isDirectory()) {
		warning("HQ-MUSIC: no audio file %s (for cue %s)", wavPath.toString().c_str(), name);
		return;
	}

	// Open via FSNode (same as HDAssetManager; resolves CWD-relative hd)
	Common::SeekableReadStream *fileStream = wavNode.createReadStream();
	if (!fileStream) {
		warning("HQ-MUSIC: cannot open %s (cue %s)", wavPath.toString().c_str(), name);
		return;
	}

	// Parse RIFF/WAVE header
	uint32 riffTag = fileStream->readUint32BE();
	fileStream->readUint32LE(); // file size
	uint32 waveTag = fileStream->readUint32BE();
	if (riffTag != MKTAG('R','I','F','F') || waveTag != MKTAG('W','A','V','E')) {
		debug(3, "HQ-MUSIC: %s is not RIFF/WAVE (cue %s)", wavPath.toString().c_str(), name);
		delete fileStream;
		return;
	}

	// Walk chunks to find fmt + data
	uint32 dataOffset = 0, dataLen = 0;
	uint16 channels = 1, bits = 16;
	uint32 sampleRate = 22050;
	// pos is now 12 (after RIFF header)
	while (fileStream->pos() + 8 <= fileStream->size()) {
		uint32 cid = fileStream->readUint32BE();
		uint32 clen = fileStream->readUint32LE();
		uint32 chunkStart = fileStream->pos() - 8;   // where this chunk began
		uint32 next = chunkStart + 8 + clen + (clen & 1);  // next chunk
		debug(3, "HQ-MUSIC: chunk '%c%c%c%c' clen=%u at %u", (cid>>24)&0xff, (cid>>16)&0xff, (cid>>8)&0xff, cid&0xff, clen, chunkStart);
		if (cid == MKTAG('f','m','t',' ')) {
			fileStream->readUint16LE();  // format tag (must be 1 = PCM, assumed)
			channels = fileStream->readUint16LE();
			sampleRate = fileStream->readUint32LE();
			fileStream->skip(6);         // byteRate(4) + blockAlign(2)
			bits = fileStream->readUint16LE();
		} else if (cid == MKTAG('d','a','t','a')) {
			dataOffset = chunkStart + 8;
			dataLen = clen;
			break;
		}
		if (next > fileStream->size())
			break;
		fileStream->seek(next);
	}
	if (!dataOffset || !dataLen) {
		warning("HQ-MUSIC: %s has no data chunk", name);
		delete fileStream;
		return;
	}

	// Only 16-bit PCM is supported (the FRMT header describes 16-bit words).
	if (bits != 16) {
		warning("HQ-MUSIC: %s is not 16-bit PCM (%d bit)", name, bits);
		delete fileStream;
		return;
	}

	// Keep the stream for playback (seeked to data start on each read)
	_extStream = fileStream;
	_extStreamDataOffset = dataOffset;
	_extStreamDataLen = dataLen;

	// Build the FULL synthetic stream header (mapSize + MAP + FRMT):
	// The engine reads offset 0..0x10 for the iMUS/MAP check, then reads
	// size = mapSize + 24 bytes as the map. map[4] (= stream offset 24)
	// MUST equal size (52) — it marks where the audio data begins.
	// Layout (big-endian):
	//   0: 'iMUS'   4: mapSize(28)   8: 'MAP '  12: mapSize(28)
	//  16: 'FRMT'  20: blkSize-8(20) 24: offset(52 = data start)
	//  28: empty(0) 32: wordSize(16) 36: rate    40: channels  44..51: 0
	const int hdrSize = 52;
	memset(_extHeader, 0, sizeof(_extHeader));
	memcpy(_extHeader + 0, "iMUS", 4);
	WRITE_BE_UINT32(_extHeader + 4, 28);
	memcpy(_extHeader + 8, "MAP ", 4);
	WRITE_BE_UINT32(_extHeader + 12, 28);
	memcpy(_extHeader + 16, "FRMT", 4);
	WRITE_BE_UINT32(_extHeader + 20, 20);   // block size - 8
	WRITE_BE_UINT32(_extHeader + 24, hdrSize);  // data start offset (=52)
	WRITE_BE_UINT32(_extHeader + 28, 0);    // empty
	WRITE_BE_UINT32(_extHeader + 32, 16);   // wordSize
	WRITE_BE_UINT32(_extHeader + 36, sampleRate);
	WRITE_BE_UINT32(_extHeader + 40, channels);
	// 44..51 padding zero

	_extHeaderSent = false;
	_extReadTotal = 0;
	_extStreamDataOffset = dataOffset;
	_extStreamDataLen = dataLen;
	debug(3, "HQ-MUSIC: external track %s.wav (%d Hz, %d ch, %d bytes PCM)", name, sampleRate, channels, dataLen);
}

void BundleMgr::closeExternal() {
	if (_extStream) {
		delete _extStream;
		_extStream = nullptr;
	}
	_extTrackName = "";
	_extStreamDataOffset = 0;
	_extStreamDataLen = 0;
	_extHeaderSent = false;
	_extReadTotal = 0;
}

Common::SeekableReadStream *BundleMgr::getFile(const char *filename, int32 &offset, int32 &size) {
	BundleDirCache::IndexNode target;
	Common::strlcpy(target.filename, filename, sizeof(target.filename));
	BundleDirCache::IndexNode *found = (BundleDirCache::IndexNode *)bsearch(&target, _indexTable, _numFiles,
			sizeof(BundleDirCache::IndexNode), (int (*)(const void *, const void *))scumm_stricmp);
	if (found) {
		_file->seek(_bundleTable[found->index].offset, SEEK_SET);
		offset = _bundleTable[found->index].offset;
		size = _bundleTable[found->index].size;
		return _file;
	}

	return nullptr;
}

bool BundleMgr::open(const char *filename, bool &isCompressed, bool errorFlag) {
	if (_file->isOpen())
		return true;

	if (g_scumm->openFile(*_file, filename) == false) {
		if (errorFlag) {
			error("BundleMgr::open() Can't open bundle file: %s", filename);
		} else {
			warning("BundleMgr::open() Can't open bundle file: %s", filename);
		}
		return false;
	}

	int slot = _cache->matchFile(filename);
	assert(slot != -1);
	isCompressed = _cache->isSndDataExtComp(slot);
	_numFiles = _cache->getNumFiles(slot);
	assert(_numFiles);
	_bundleTable = _cache->getTable(slot);
	_indexTable = _cache->getIndexTable(slot);
	assert(_bundleTable);
	_compTableLoaded = false;
	_isUncompressed = false;
	_outputSize = 0;
	_lastBlockDecompressedSize = 0;
	_curDecompressedFilePos = 0;
	_lastBlock = -1;

	return true;
}

void BundleMgr::close() {
	if (_file->isOpen()) {
		_file->close();
		_bundleTable = nullptr;
		_numFiles = 0;
		_numCompItems = 0;
		_lastBlockDecompressedSize = 0;
		_curDecompressedFilePos = 0;
		_compTableLoaded = false;
		_isUncompressed = false;
		_lastBlock = -1;
		_outputSize = 0;
		_curSampleId = -1;
		free(_compTable);
		_compTable = nullptr;
		free(_compInputBuff);
		_compInputBuff = nullptr;
	}
	closeExternal();
}

bool BundleMgr::loadCompTable(int32 index) {
	_file->seek(_bundleTable[index].offset, SEEK_SET);
	uint32 tag = _file->readUint32BE();

	if (tag == MKTAG('i','M','U','S')) {
		_isUncompressed = true;
		return true;
	}

	_numCompItems = _file->readUint32BE();
	assert(_numCompItems > 0);
	_file->seek(4, SEEK_CUR);
	_lastBlockDecompressedSize = _file->readUint32BE();
	if (tag != MKTAG('C','O','M','P')) {
		debug("BundleMgr::loadCompTable() Compressed sound %d (%s:%d) invalid (%s)", index, _file->getDebugName().c_str(), _bundleTable[index].offset, tag2str(tag));
		return false;
	}

	_compTable = (CompTable *)malloc(sizeof(CompTable) * _numCompItems);
	assert(_compTable);
	int32 maxSize = 0;
	for (int i = 0; i < _numCompItems; i++) {
		_compTable[i].offset = _file->readUint32BE();
		_compTable[i].size = _file->readUint32BE();
		_compTable[i].codec = _file->readUint32BE();
		_file->seek(4, SEEK_CUR);
		if (_compTable[i].size > maxSize)
			maxSize = _compTable[i].size;
	}
	// CMI hack: one more byte at the end of input buffer
	_compInputBuff = (byte *)malloc(maxSize + 1);
	assert(_compInputBuff);

	return true;
}

int32 BundleMgr::seekFile(int32 offset, int mode) {
	// We don't actually seek the file, but instead try to find that the specified offset exists
	// within the decompressed blocks, and save that offset in _curDecompressedFilePos
	int result = 0;

	// Issue #19: external WAV track — position is the PCM data offset.
	if (_extStream) {
		switch (mode) {
		case SEEK_END:
			result = offset + _extStreamDataLen;
			break;
		case SEEK_SET:
		default:
			result = offset;
			break;
		}
		if (result < 0)
			result = 0;
		if (result > _extStreamDataLen)
			result = _extStreamDataLen;
		_curDecompressedFilePos = result;
		return result;
	}

	switch (mode) {
	case SEEK_END:
		if (_isUncompressed) {
			result = offset + _bundleTable[_curSampleId].size;
		} else {
			result = offset + ((_numCompItems - 1) * DIMUSE_BUN_CHUNK_SIZE) + _lastBlockDecompressedSize;
		}
		_curDecompressedFilePos = result;
		break;
	case SEEK_SET:
	default:
		if (_isUncompressed) {
			result = offset;
			_curDecompressedFilePos = result;
		} else {
			int destBlock = offset / DIMUSE_BUN_CHUNK_SIZE + (offset % DIMUSE_BUN_CHUNK_SIZE != 0);
			if (destBlock <= _numCompItems) {
				result = offset;
				_curDecompressedFilePos = result;
			}
		}
		break;
	}
	return result;
}

int32 BundleMgr::readFile(const char *name, int32 size, byte **comp_final, bool header_outside) {

	if (!_file->isOpen()) {
		error("BundleMgr::readFile() File is not open");
		return 0;
	}

	// Issue #19: CD-quality replacement — ONLY when hq_music=1 is set in the
	// config. If the cue has an OST mapping and the file exists in
	// <hd>/audio/, stream that instead of the bundle's IMX-ADPCM audio.
	// Checked ONCE per track; any failure falls through to the bundle.
	if (_vm && _vm->_hqMusic) {
		bool mapped = false;
		for (int i = 0; i < kExtMusicTableSize && !mapped; i++)
			if (scumm_stricmp(kExtMusicTable[i].cue, name) == 0)
				mapped = true;
		if (mapped) {
			// Only attempt the external file once per track.
			if (!_extChecked || _extTrackName != name) {
				_extChecked = true;
				_extTrackName = name;
				openExternal(name);
			}
			if (_extStream && _extTrackName == name) {
				int32 ext = readFileExternal(name, size, comp_final);
				if (ext > 0)
					return ext;
				// External stream failed/empty — fall back to the bundle
				// so music never goes silent.
				closeExternal();
				warning("HQ-MUSIC: external stream for %s failed, using bundle", name);
			}
		}
	}

	// Find the sound in the bundle
	BundleDirCache::IndexNode target;
	strncpy(target.filename, name, sizeof(target.filename));
	target.filename[sizeof(target.filename) - 1] = '\0';
	BundleDirCache::IndexNode *found = (BundleDirCache::IndexNode *)bsearch(&target, _indexTable, _numFiles,
		sizeof(BundleDirCache::IndexNode), (int(*)(const void *, const void *))scumm_stricmp);

	if (found) {
		int32 i, finalSize, outputSize;
		int skip, firstBlock, lastBlock;
		int headerSize = 0;

		assert(0 <= found->index && found->index < _numFiles);

		if (_file->isOpen() == false) {
			error("BundleMgr::readFile() File is not open");
			return 0;
		}

		if (_curSampleId == -1)
			_curSampleId = found->index;

		assert(_curSampleId == found->index);

		if (!_compTableLoaded) {
			_compTableLoaded = loadCompTable(found->index);
			if (!_compTableLoaded)
				return 0;
		}

		if (_isUncompressed) {
			_file->seek(_bundleTable[found->index].offset + _curDecompressedFilePos + headerSize, SEEK_SET);
			*comp_final = (byte *)malloc(size);
			assert(*comp_final);
			_file->read(*comp_final, size);
			_curDecompressedFilePos += size;
			return size;
		}

		firstBlock = (_curDecompressedFilePos + headerSize) / DIMUSE_BUN_CHUNK_SIZE;
		lastBlock = (_curDecompressedFilePos + headerSize + size - 1) / DIMUSE_BUN_CHUNK_SIZE;

		// Clip last_block by the total number of blocks (= "comp items")
		if ((lastBlock >= _numCompItems) && (_numCompItems > 0))
			lastBlock = _numCompItems - 1;

		int32 blocksFinalSize = DIMUSE_BUN_CHUNK_SIZE * (1 + lastBlock - firstBlock);
		*comp_final = (byte *)malloc(blocksFinalSize);
		assert(*comp_final);
		finalSize = 0;

		skip = (_curDecompressedFilePos + headerSize) % DIMUSE_BUN_CHUNK_SIZE; // Excess length after the last block

		for (i = firstBlock; i <= lastBlock; i++) {
			if (_lastBlock != i) {
				// CMI hack: one more zero byte at the end of input buffer
				_compInputBuff[_compTable[i].size] = 0;
				_file->seek(_bundleTable[found->index].offset + _compTable[i].offset, SEEK_SET);
				_file->read(_compInputBuff, _compTable[i].size);
				_outputSize = BundleCodecs::decompressCodec(_compTable[i].codec, _compInputBuff, _compOutputBuff, _compTable[i].size);

				if (_outputSize > DIMUSE_BUN_CHUNK_SIZE) {
					error("_outputSize: %d", _outputSize);
				}
				_lastBlock = i;
			}

			outputSize = _outputSize;

			if (header_outside) {
				outputSize -= skip;
			} else {
				if ((headerSize != 0) && (skip >= headerSize))
					outputSize -= skip;
			}

			if ((outputSize + skip) > DIMUSE_BUN_CHUNK_SIZE) // workaround
				outputSize -= (outputSize + skip) - DIMUSE_BUN_CHUNK_SIZE;

			if (outputSize > size)
				outputSize = size;

			assert(finalSize + outputSize <= blocksFinalSize);

			memcpy(*comp_final + finalSize, _compOutputBuff + skip, outputSize);
			finalSize += outputSize;

			size -= outputSize;
			assert(size >= 0);
			if (size == 0)
				break;

			skip = 0;
		}
		_curDecompressedFilePos += finalSize;

		return finalSize;
	}

	debug(2, "BundleMgr::readFile() Failed finding sound %s", name);
	return readFileExternal(name, size, comp_final);
}

// Issue #19 fallback: sound not in bundle -> try external WAV.
// The streamer calls seek() then read(); we serve the WAV PCM at the
// position set by seekFile (position = byte offset into the PCM data).
// The first openSound() readFile(0x2000) serves the synthetic iMUS/MAP/FRMT
// header (52 bytes); after that, all reads are raw PCM from the WAV.
int32 BundleMgr::readFileExternal(const char *name, int32 size, byte **comp_final) {
	if (!_extStream) {
		// First call for this sound: try to open the WAV
		openExternal(name);
		if (!_extStream) {
			debug(2, "HQ-MUSIC: no external track for %s", name);
			return 0;
		}
	}

	const int hdrSize = 52;  // synthetic iMUS/MAP/FRMT header length

	// Serve the synthetic header first (only once).
	if (!_extHeaderSent) {
		int avail = hdrSize - _extReadTotal;
		int take = MIN(avail, size);
		*comp_final = (byte *)malloc(take ? take : 1);
		memcpy(*comp_final, _extHeader + _extReadTotal, take);
		_extReadTotal += take;
		_extHeaderSent = (_extReadTotal >= hdrSize);
		_curDecompressedFilePos = 0;   // audio data starts at 0 after header
		debug(3, "HQ-MUSIC: served header %d bytes for %s (total %d)", take, name, _extReadTotal);
		// Append audio if the caller asked for more than the header.
		if (take < size && _extHeaderSent) {
			int32 take2 = MIN(_extStreamDataLen, size - take);
			if (take2 > 0) {
				byte *extended = (byte *)realloc(*comp_final, take + take2);
				if (extended) {
					*comp_final = extended;
					_extStream->seek(_extStreamDataOffset);
					uint32 got = _extStream->read(*comp_final + take, take2);
					_extReadTotal += got;
					_curDecompressedFilePos = got;
					debug(3, "HQ-MUSIC: %s header+audio served %d+%d bytes", name, take, got);
					return take + got;
				}
			}
		}
		return take;
	}

	// Audio data: read from the position set by seekFile().
	int32 wantPos = _curDecompressedFilePos;
	if (wantPos >= _extStreamDataLen) {
		// Loop: restart from 0 (iMUSE loops the stream)
		wantPos = 0;
		_curDecompressedFilePos = 0;
	}
	_extStream->seek(_extStreamDataOffset + wantPos);

	int32 remaining = _extStreamDataLen - wantPos;
	int32 take = MIN(remaining, size);
	if (take <= 0)
		return 0;

	*comp_final = (byte *)malloc(take);
	uint32 got = _extStream->read(*comp_final, take);
	_curDecompressedFilePos += got;
	// Verify: hash the first 256 bytes served at pos 0 against the WAV.
	if (wantPos == 0 && !_extHashLogged) {
		uint32 h = 0;
		for (int i = 0; i < 256 && i < (int)got; i++)
			h = (h << 5) + h + (*comp_final)[i];
		debug(3, "HQ-MUSIC: %s first-bytes-hash=%08x (pos0, %d bytes)", name, h, MIN(256, (int)got));
		_extHashLogged = true;
	}
	debug(3, "HQ-MUSIC: %s served %d bytes at pos %d/%d", name, got, wantPos, _extStreamDataLen);
	return got;
}

bool BundleMgr::isExtCompBun(byte gameId) {
	bool isExtComp = false;
	if (gameId == GID_CMI) {
		bool isExtComp1 = false, isExtComp2 = false, isExtComp3 = false, isExtComp4 = false;
		this->open("voxdisk1.bun", isExtComp1); this->close();
		this->open("voxdisk2.bun", isExtComp2); this->close();
		this->open("musdisk1.bun", isExtComp3); this->close();
		this->open("musdisk2.bun", isExtComp4); this->close();

		isExtComp = isExtComp1 | isExtComp2 | isExtComp3 | isExtComp4;
	} else {
		bool isExtComp1 = false, isExtComp2 = false;
		this->open("digvoice.bun", isExtComp1); this->close();
		this->open("digmusic.bun", isExtComp2); this->close();
		isExtComp = isExtComp1 | isExtComp2;
	}

	return isExtComp;
}

} // End of namespace Scumm
