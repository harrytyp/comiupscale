from typing import cast

import numpy as np

from nutcracker.kernel2 import preset
from nutcracker.kernel2.chunk import ChunkHeader, HeaderDType


class OldSPUTMChunkHeader(ChunkHeader):
    dtype = cast(
        type[HeaderDType],
        np.dtype(
            [
                ('size', '<u4'),  # 4-byte unsigned int for the size
                ('tag', 'S2'),  # 2-byte string for the tag
            ],
        ),
    )


earwax = preset.shell(
    header_dtype=OldSPUTMChunkHeader,
    alignment=1,
    inclheader=True,
    errors='ignore',
)
