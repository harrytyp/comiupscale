#!/usr/bin/env python3

import io
import operator
import pprint
from collections.abc import Callable, Iterable, Iterator
from functools import partial
from itertools import takewhile
from typing import IO

from nutcracker.chiper import xor
from nutcracker.kernel2.chunk import ArrayBuffer
from nutcracker.kernel2.element import Element

from .preset import sputm


def read_directory_leg(data: ArrayBuffer) -> Iterator[tuple[int, tuple[int, int]]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(2), byteorder='little', signed=False)
        rnums = [
            int.from_bytes(s.read(1), byteorder='little', signed=False)
            for i in range(num)
        ]
        offs = [
            int.from_bytes(s.read(4), byteorder='little', signed=False)
            for i in range(num)
        ]
        return enumerate(zip(rnums, offs, strict=True))


def read_directory_leg_v8(data: ArrayBuffer) -> Iterator[tuple[int, tuple[int, int]]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(4), byteorder='little', signed=False)
        rnums = [
            int.from_bytes(s.read(1), byteorder='little', signed=False)
            for i in range(num)
        ]
        offs = [
            int.from_bytes(s.read(4), byteorder='little', signed=False)
            for i in range(num)
        ]
        return enumerate(zip(rnums, offs, strict=True))


def read_rnam(data: ArrayBuffer, key: int = 0xFF) -> Iterator[tuple[int, str]]:
    with io.BytesIO(data) as s:
        while True:
            rnum = int.from_bytes(s.read(1), byteorder='little', signed=False)
            if not rnum:
                break
            name = xor.read(s, 9, key=key).split(b'\0')[0].decode()
            yield rnum, name


def readcstr(
    stream: IO[bytes],
    read_fn: Callable[[IO[bytes], int], bytes],
) -> str | None:
    bound_read = iter(partial(read_fn, stream, 1), b'')
    res = b''.join(takewhile(partial(operator.ne, b'\00'), bound_read))
    return res.decode() if res else None


def read_rnam_he(
    data: ArrayBuffer,
    key: int = 0xFF,
) -> Iterator[tuple[int, str]]:
    with io.BytesIO(data) as s:
        while True:
            rnum = int.from_bytes(s.read(2), byteorder='little', signed=False)
            if not rnum:
                break
            name = readcstr(s, partial(xor.read, key=key))
            assert name is not None
            yield rnum, name


def read_anam(data: ArrayBuffer) -> Iterator[tuple[int, str]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(2), byteorder='little', signed=False)
        names = [s.read(9).split(b'\0')[0].decode() for i in range(num)]
        return enumerate(names)


def read_dobj(data: ArrayBuffer) -> Iterator[tuple[int, tuple[int, int]]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(2), byteorder='little', signed=False)
        values = list(s.read(num))
        # [(state, owner)]
        return enumerate((val >> 4, val & 0xFF) for val in values)


def read_dobj_v8(data: ArrayBuffer) -> Iterator[tuple[str, tuple[int, int, int, int]]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(4), byteorder='little', signed=False)
        for i in range(num):
            name = s.read(40).split(b'\0')[0].decode()
            obj_id = i
            state = ord(s.read(1))
            room = ord(s.read(1))
            obj_class = int.from_bytes(s.read(4), byteorder='little', signed=False)
            yield name, (obj_id, state, room, obj_class)


def read_dobj_v7(data: ArrayBuffer) -> Iterator[tuple[int, tuple[int, int, int]]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(2), byteorder='little', signed=False)
        states = list(s.read(num))
        rooms = list(s.read(num))
        classes = [
            int.from_bytes(s.read(4), byteorder='little', signed=False)
            for _ in range(num)
        ]
        return enumerate(zip(states, rooms, classes, strict=True))


def read_dobj_he(data: ArrayBuffer) -> Iterator[tuple[int, tuple[int, int, int, int]]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(2), byteorder='little', signed=False)
        states = list(s.read(num))
        owners = list(s.read(num))
        rooms = list(s.read(num))
        classes = [
            int.from_bytes(s.read(4), byteorder='little', signed=False)
            for _ in range(num)
        ]
        return enumerate(zip(states, owners, rooms, classes, strict=True))


def read_dlfl(data: ArrayBuffer) -> Iterator[tuple[int, int]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(2), byteorder='little', signed=False)
        offs = [
            int.from_bytes(s.read(4), byteorder='little', signed=False)
            for i in range(num)
        ]
        return enumerate(offs)


def read_directory(data: ArrayBuffer) -> list[tuple[int, int]]:
    with io.BytesIO(data) as s:
        num = int.from_bytes(s.read(1), byteorder='little', signed=False)
        merged = [
            (
                int.from_bytes(s.read(1), byteorder='little', signed=False),
                int.from_bytes(s.read(4), byteorder='little', signed=False),
            )
            for i in range(num)
        ]
        return merged


IdGen = Callable[[int, ArrayBuffer, int], int | None]


def read_inner_uint16le_v7(pid: int, data: ArrayBuffer, off: int) -> int:
    res = int.from_bytes(data[12:14], byteorder='little', signed=False)
    return res


def read_inner_uint16le(pid: int, data: ArrayBuffer, off: int) -> int:
    res = int.from_bytes(data[8:10], byteorder='little', signed=False)
    return res


def read_uint8le(pid: int, data: ArrayBuffer, off: int) -> int:
    res = int.from_bytes(data[:1], byteorder='little', signed=False)
    return res


def read_uint16le(pid: int, data: ArrayBuffer, off: int) -> int:
    res = int.from_bytes(data[:2], byteorder='little', signed=False)
    return res


def read_uint32le(pid: int, data: ArrayBuffer, off: int) -> int:
    res = int.from_bytes(data[:4], byteorder='little', signed=False)
    return res


def compare_pid_off(directory: dict[int, tuple[int, int]], base: int = 0) -> IdGen:
    def inner(pid: int, data: ArrayBuffer, off: int) -> int | None:
        return next((k for k, v in directory.items() if v == (pid, off + base)), None)

    return inner


def compare_off_he(directory: dict[int, int]) -> IdGen:
    def inner(pid: int, data: ArrayBuffer, off: int) -> int | None:
        return next((k for k, v in directory.items() if v == off + 16), None)

    return inner


def read_index_v5tov7(
    root: Iterable[Element],
) -> tuple[dict[int, str], dict[str, IdGen]]:
    for t in root:
        sputm.render(t)
        if t.tag == 'RNAM':
            rnam = dict(read_rnam(t.data, key=0xFF))
            pprint.pprint(rnam)
        elif t.tag == 'MAXS':
            print('MAXS not yet supported')
        elif t.tag == 'DROO':
            droo = dict(read_directory_leg(t.data))
            pprint.pprint(droo)
        elif t.tag == 'DRSC':
            drsc = dict(read_directory_leg(t.data))
            pprint.pprint(drsc)
        elif t.tag == 'DSCR':
            dscr = dict(read_directory_leg(t.data))
            pprint.pprint(dscr)
        elif t.tag == 'DSOU':
            dsou = dict(read_directory_leg(t.data))
            pprint.pprint(dsou)
        elif t.tag == 'DCOS':
            dcos = dict(read_directory_leg(t.data))
            pprint.pprint(dcos)
        elif t.tag == 'DCHR':
            dchr = dict(read_directory_leg(t.data))
            pprint.pprint(dchr)
        elif t.tag == 'DOBJ':
            print('DOBJ not yet supported')
        elif t.tag == 'ANAM':
            anam = dict(read_anam(t.data))
            pprint.pprint(anam)
    return rnam, {
        'LFLF': droo,
        'OBIM': read_inner_uint16le,  # check gid for DIG and FT
        'OBCD': read_inner_uint16le,
        'LSCR': read_uint8le,
        'SCRP': compare_pid_off(dscr),
        'CHAR': compare_pid_off(dchr),
        'SOUN': compare_pid_off(dsou),
        'COST': compare_pid_off(dcos),
        'AKOS': compare_pid_off(dcos),
    }


def read_index_v7(
    root: Iterable[Element],
) -> tuple[dict[int, str], dict[str, IdGen]]:
    for t in root:
        sputm.render(t)
        if t.tag == 'RNAM':
            rnam = dict(read_rnam(t.data, key=0xFF))
            pprint.pprint(rnam)
        elif t.tag == 'MAXS':
            print('MAXS not yet supported')
        elif t.tag == 'DROO':
            droo = dict(read_directory_leg(t.data))
            pprint.pprint(droo)
        elif t.tag == 'DRSC':
            drsc = dict(read_directory_leg(t.data))
            pprint.pprint(drsc)
        elif t.tag == 'DSCR':
            dscr = dict(read_directory_leg(t.data))
            pprint.pprint(dscr)
        elif t.tag == 'DSOU':
            dsou = dict(read_directory_leg(t.data))
            pprint.pprint(dsou)
        elif t.tag == 'DCOS':
            dcos = dict(read_directory_leg(t.data))
            pprint.pprint(dcos)
        elif t.tag == 'DCHR':
            dchr = dict(read_directory_leg(t.data))
            pprint.pprint(dchr)
        elif t.tag == 'DOBJ':
            print('DOBJ not yet supported')
        elif t.tag == 'ANAM':
            anam = dict(read_anam(t.data))
            pprint.pprint(anam)
    return rnam, {
        'LFLF': droo,
        'OBIM': read_inner_uint16le_v7,
        'OBCD': read_inner_uint16le_v7,
        'LSCR': read_uint16le,
        'SCRP': compare_pid_off(dscr),
        'CHAR': compare_pid_off(dchr),
        'SOUN': compare_pid_off(dsou),
        'COST': compare_pid_off(dcos),
        'AKOS': compare_pid_off(dcos),
    }


def read_index_v8(
    root: Iterable[Element],
) -> tuple[dict[int, str], dict[str, IdGen]]:
    for t in root:
        sputm.render(t)
        if t.tag == 'RNAM':
            rnam = dict(read_rnam(t.data, key=0xFF))
            pprint.pprint(rnam)
        elif t.tag == 'MAXS':
            print('MAXS not yet supported')
        elif t.tag == 'DROO':
            droo = dict(read_directory_leg_v8(t.data))
            pprint.pprint(droo)
        elif t.tag == 'DRSC':
            drsc = dict(read_directory_leg_v8(t.data))
            pprint.pprint(drsc)
        elif t.tag == 'DSCR':
            dscr = dict(read_directory_leg_v8(t.data))
            pprint.pprint(dscr)
        elif t.tag == 'DSOU':
            dsou = dict(read_directory_leg_v8(t.data))
            pprint.pprint(dsou)
        elif t.tag == 'DCOS':
            dcos = dict(read_directory_leg_v8(t.data))
            pprint.pprint(dcos)
        elif t.tag == 'DCHR':
            dchr = dict(read_directory_leg_v8(t.data))
            pprint.pprint(dchr)
        elif t.tag == 'DOBJ':
            dobj = dict(read_dobj_v8(t.data))
            pprint.pprint(dobj)
        elif t.tag == 'ANAM':
            anam = dict(read_anam(t.data))
            pprint.pprint(anam)
    return rnam, {
        'LFLF': droo,
        'OBIM': get_object_id_from_name_v8(dobj),
        'OBCD': read_inner_uint16le_v7,
        'LSCR': read_uint32le,
        'RMSC': compare_pid_off(drsc, 8),
        'SCRP': compare_pid_off(dscr, 8),
        'CHAR': compare_pid_off(dchr, 8),
        'SOUN': compare_pid_off(dsou, 8),
        'COST': compare_pid_off(dcos, 8),
        'AKOS': compare_pid_off(dcos, 8),
    }


def get_object_id_from_name_v8(dobj: dict[str, tuple[int, int, int, int]]) -> IdGen:
    def compare_name(pid: int, data: ArrayBuffer, off: int) -> int:
        name = bytes(data[8:48]).split(b'\0')[0].decode()
        return dobj[name][0]

    return compare_name


def read_index_he(
    root: Iterable[Element],
) -> tuple[dict[int, str], dict[str, IdGen]]:
    dtlk = {}  # prevent `referenced before assignment` error
    dmul = {}
    for t in root:
        # sputm.render(t)
        if t.tag == 'RNAM':
            rnam = dict(read_rnam_he(t.data, key=0x00))
            # pprint.pprint(rnam)
        elif t.tag == 'MAXS':
            pass
            # print('MAXS not yet supported')
        elif t.tag == 'DIRI':
            droo = dict(read_directory_leg(t.data))
            # pprint.pprint(droo)
        elif t.tag == 'DIRS':
            dscr = dict(read_directory_leg(t.data))
            # pprint.pprint(dscr)
        elif t.tag == 'DIRC':
            dcos = dict(read_directory_leg(t.data))
            # pprint.pprint(dcos)
        elif t.tag == 'DIRF':
            dchr = dict(read_directory_leg(t.data))
            # pprint.pprint(dchr)
        elif t.tag == 'DIRN':
            dsou = dict(read_directory_leg(t.data))
            # pprint.pprint(dsou)
        elif t.tag == 'DIRT':
            dtlk = dict(read_directory_leg(t.data))
            # pprint.pprint(dtlk)
        elif t.tag == 'DIRM':
            dmul = dict(read_directory_leg(t.data))
            # pprint.pprint(dmul)
        elif t.tag == 'DIRR':
            drmd = dict(read_directory_leg(t.data))
            # pprint.pprint(drmd)
        elif t.tag == 'DISK':
            # TODO
            # all values are `idx: (1, 0)`
            disk = dict(read_directory_leg(t.data))
            # pprint.pprint(disk)
        elif t.tag == 'DLFL':
            dlfl = dict(read_dlfl(t.data))
            # pprint.pprint(dlfl)
            pass
    return rnam, {
        'LFLF': compare_off_he(dlfl),
        'OBIM': read_inner_uint16le,
        'OBCD': read_inner_uint16le,
        'LSCR': read_uint8le,
        'LSC2': read_uint32le,
        'SCRP': compare_pid_off(dscr),
        'CHAR': compare_pid_off(dchr),
        'DIGI': compare_pid_off(dsou),
        'SOUN': compare_pid_off(dsou),
        'AKOS': compare_pid_off(dcos),
        'MULT': compare_pid_off(dmul),
        'AWIZ': compare_pid_off(dmul),
        'RMDA': compare_pid_off(drmd),
        'TALK': compare_pid_off(dsou),
        'TLKE': compare_pid_off(dtlk),
    }
