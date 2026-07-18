import itertools
from collections.abc import Iterable, Iterator
from typing import Any, NamedTuple

from nutcracker.kernel2.chunk import ArrayBuffer, Chunk
from nutcracker.kernel2.element import Element
from nutcracker.kernel2.fileio import ResourceFile
from nutcracker.smush import ahdr
from nutcracker.smush.element import read_data, read_elements
from nutcracker.smush.preset import smush


class SmushAnimation(NamedTuple):
    header: ahdr.AnimationHeader
    frames: Iterator[Element]


def verify_nframes(frames: Iterator[Element], nframes: int) -> Iterator[Element]:
    for idx, frame in enumerate(frames):
        if nframes and idx > nframes - 1:
            raise ValueError('too many frames')
        yield frame


def verify_maxframe(
    frames: Iterator[Element],
    limit: int | None,
) -> Iterator[Element]:
    maxframe = 0
    for elem in frames:
        maxframe = max(elem.attribs['size'], maxframe)
        yield elem
    if limit and maxframe > limit:
        raise ValueError(f'expected maxframe of {limit} but got {maxframe}')


def parse(root: Element) -> SmushAnimation:
    anim = read_elements('ANIM', root)
    header = ahdr.from_bytes(read_data('AHDR', next(anim)))

    frames = verify_nframes(verify_maxframe(anim, header.v2.maxframe), header.nframes)

    return SmushAnimation(header, frames)


def compose(header: ahdr.AnimationHeader, frames: Iterable[Chunk]) -> bytes:
    bheader = smush.mktag('AHDR', memoryview(ahdr.to_bytes(header)))
    return bytes(
        smush.mktag(
            'ANIM', memoryview(smush.write_chunks(itertools.chain([bheader], frames)))
        ),
    )


def from_bytes(resource: ArrayBuffer) -> Element:
    it = itertools.count()

    def set_frame_id(
        parent: Element | None,
        chunk: Chunk,
        offset: int,
    ) -> dict[str, Any]:
        if chunk.tag != 'FRME':
            return {}
        return {'id': next(it)}

    return next(smush(extra=set_frame_id).map_chunks(resource))


def from_path(path: str) -> Element:
    with ResourceFile.load(path) as res:
        return from_bytes(res)
