from dataclasses import dataclass, replace
from typing import Any, Self

from nutcracker.kernel2 import tree
from nutcracker.kernel2.chunk import (
    IFFChunkHeader,
    assert_tag,
    mktag,
    read_chunks,
    untag,
    write_chunks,
)
from nutcracker.kernel2.element import (
    IndexerSettings,
    generate_schema,
    map_chunks,
)


@dataclass(frozen=True)
class _DefaultOverride:
    def __call__(self, **kwargs: Any) -> Self:
        return replace(self, **kwargs)


@dataclass(frozen=True)
class Preset(IndexerSettings, _DefaultOverride):
    read_chunks = read_chunks
    write_chunks = write_chunks
    map_chunks = map_chunks
    generate_schema = generate_schema
    mktag = mktag
    untag = untag

    # static pass through
    find = staticmethod(tree.find)
    findall = staticmethod(tree.findall)
    findpath = staticmethod(tree.findpath)
    render = staticmethod(tree.render)
    renders = staticmethod(tree.renders)
    assert_tag = staticmethod(assert_tag)


shell = Preset(
    header_dtype=IFFChunkHeader,
    alignment=2,
    inclheader=True,
    skip_byte=None,
)
