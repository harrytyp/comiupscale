from collections.abc import Iterable, Iterator

from nutcracker.kernel2.chunk import Chunk
from nutcracker.kernel2.element import Element
from nutcracker.smush import anim
from nutcracker.smush.fobj import compress
from nutcracker.smush.preset import smush


def compress_frame_data(frame: Element) -> Iterator[Chunk]:
    first_fobj = True
    for comp in frame.children():
        if comp.tag == 'FOBJ' and first_fobj:
            first_fobj = False
            yield smush.mktag('ZFOB', memoryview(compress(comp.data)))
        elif comp.tag == 'PSAD':
            continue
            # print('skipping sound stream')
        else:
            first_fobj = first_fobj and comp.tag != 'ZFOB'
            yield smush.mktag(comp.tag, comp.data)


def compress_frames(frames: Iterable[Element]) -> Iterator[Chunk]:
    yield from (
        smush.mktag('FRME', memoryview(smush.write_chunks(compress_frame_data(frame))))
        for frame in frames
    )


def strip_compress_san(root: Element) -> bytes:
    header, frames = anim.parse(root)
    compressed_frames = compress_frames(frames)
    return anim.compose(header, compressed_frames)
