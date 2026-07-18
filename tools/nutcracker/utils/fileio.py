__all__ = ('read_file', 'write_file')

from pathlib import Path

from nutcracker.chiper import xor
from nutcracker.kernel2.fileio import read_file


def write_file(path: str, data: bytes, key: int = 0x00) -> int:
    with Path(path).open('wb') as res:
        return xor.write(res, data, key=key)
