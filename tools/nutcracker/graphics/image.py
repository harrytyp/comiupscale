from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

Origin = tuple[int, int]
Box = tuple[int, int, int, int]
Matrix = Sequence[Sequence[int]]


TImage = Image.Image

@dataclass
class ImagePosition:
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0


def convert_to_pil_image(
    char: Sequence[Sequence[int]],
    size: tuple[int, int] | None = None,
) -> TImage:
    # print('CHAR:', char)
    npp = np.array(list(char), dtype=np.uint8)
    if size:
        width, height = size
        npp.resize(height, width)
    im = Image.fromarray(npp, mode='P')
    return im
