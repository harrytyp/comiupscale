from nutcracker.kernel2 import preset
from nutcracker.kernel2.chunk import IFFChunkHeader

from .schema import SCHEMA

smush = preset.shell(
    alignment=2,
    header_dtype=IFFChunkHeader,
    inclheader=False,
    schema=SCHEMA,
    errors='ignore',
)
