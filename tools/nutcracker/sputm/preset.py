from nutcracker.kernel2 import preset
from nutcracker.kernel2.chunk import IFFChunkHeader

from .schema import SCHEMA

sputm = preset.shell(
    header_dtype=IFFChunkHeader,
    alignment=1,
    inclheader=True,
    skip_byte=0x80,
    schema=SCHEMA,
    errors='ignore',
)
