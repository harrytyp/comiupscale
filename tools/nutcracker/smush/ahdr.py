import io
import struct
from dataclasses import dataclass, replace

from nutcracker.kernel.structured import StructuredTuple

PALETTE_SIZE = 0x300


@dataclass(frozen=True)
class AnimationHeaderV2:
    framerate: int | None = None
    maxframe: int | None = None
    samplerate: int | None = None
    dummy2: int | None = None
    dummy3: int | None = None

NO_AHDR_V2 = AnimationHeaderV2()

@dataclass(frozen=True)
class AnimationHeader:
    version: int
    nframes: int
    dummy: int
    palette: bytes
    v2: AnimationHeaderV2 = NO_AHDR_V2


AHDR_V1 = StructuredTuple(
    ('version', 'nframes', 'dummy', 'palette'),
    struct.Struct(f'<3H{PALETTE_SIZE}s'),
    AnimationHeader,
)

AHDR_V2 = StructuredTuple(
    ('framerate', 'maxframe', 'samplerate', 'dummy2', 'dummy3'),
    struct.Struct('<5I'),
    AnimationHeaderV2,
)


def from_bytes(data: bytes) -> AnimationHeader:
    with io.BytesIO(data) as stream:
        header = AHDR_V1.unpack(stream)
        if header.version == 2:
            header = replace(header, v2=AHDR_V2.unpack(stream))
        if stream.read():
            raise ValueError('got extra trailing data')
        if header.v2.dummy2 or header.v2.dummy3:
            raise ValueError('non-zero value in header dummies')
        return header


def to_bytes(header: AnimationHeader) -> bytes:
    optional_part = AHDR_V2.pack(header.v2) if header.version == 2 else b''
    return AHDR_V1.pack(header) + optional_part
