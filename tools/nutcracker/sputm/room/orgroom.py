#!/usr/bin/env python3

import io
import os
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass

import numpy as np
from PIL import Image

from nutcracker.kernel2.element import Element
from nutcracker.sputm.preset import sputm

from .encode_image import encode_block_v8
from .pproom import get_rooms, read_room_settings
from .proom import (
    read_imhd,
    read_imhd_v7,
    read_imhd_v8,
    read_room_background,
    read_room_background_v8,
)


def read_room(header, rmim):
    if rmim.tag == 'RMIM':
        # 'Game Version < 7'
        for imxx in sputm.findall('IM{:02x}', rmim):
            assert imxx.tag == 'IM00', imxx.tag
            yield from imxx.children()
    else:
        # TODO: check for multiple IMAG in room bg (different image state)
        assert rmim.tag == 'IMAG'
        wrap = sputm.find('WRAP', rmim)
        _, *frames = wrap.children()
        assert len(frames) == 1, len(frames)
        yield from frames


@dataclass
class ObjectHeader:
    height: int
    width: int
    xoff: int
    yoff: int


def read_objects(room, version):
    for obim in sputm.findall('OBIM', room):
        imhd = sputm.find('IMHD', obim).data
        if version < 8:
            print('IMHD', len(imhd), imhd)
            if version == 7:
                assert len(imhd) < 80, len(imhd)
                obj_id, obj_height, obj_width, obj_x, obj_y = read_imhd_v7(imhd)
            else:
                obj_id, obj_height, obj_width, obj_x, obj_y = read_imhd(imhd)

            assert obj_id == obim.attribs['gid'], (obj_id, obim.attribs['gid'])

            for imxx in sputm.findall('IM{:02x}', obim):
                path = imxx.attribs['path']
                name = f'{obj_id:04d}_{imxx.tag}'
                children = list(imxx.children())

                yield (
                    path,
                    name,
                    children[0],
                    ObjectHeader(
                        height=obj_height,
                        width=obj_width,
                        xoff=obj_x,
                        yoff=obj_y,
                    ),
                )
        else:
            # Game version == 8
            obj_name, obj_height, obj_width, obj_x, obj_y = read_imhd_v8(imhd)
            for idx, imag in enumerate(sputm.findall('IMAG', obim)):
                assert idx == 0
                wrap = sputm.find('WRAP', imag)
                yield (
                    wrap.attribs['path'],
                    obj_name,
                    wrap,
                    ObjectHeader(
                        height=obj_height,
                        width=obj_width,
                        xoff=obj_x,
                        yoff=obj_y,
                    ),
                )
                # for iidx, bomp in enumerate(wrap.children[1:]):

                #     path = bomp.attribs['path']
                #     name = f'{obj_name}_{iidx:04d}'

                #     yield path, name, bomp, obj_x, obj_y


def encode_images_v8(
    basedir: str,
    imag: Element,
    obj_name: str,
    room_id: int,
    rnam: str,
) -> Iterator[tuple[Element, bytes | None]]:
    _, *frames = imag.children()
    for iidx, imxx in enumerate(frames):
        path = imxx.attribs['path']
        name = f'{obj_name}_{iidx:04d}'

        im_path = f'{room_id:04d}_{name}' if room_id in rnam else path
        im_path = im_path.replace(os.path.sep, '_')
        im_path = os.path.join(basedir, f'{im_path}.png')

        chunk = bytes(sputm.mktag(imxx.tag, imxx.data))
        s = sputm.generate_schema(chunk)
        image = next(sputm(schema=s).map_chunks(chunk))
        print(image)

        if os.path.exists(im_path):
            encoded = encode_block_v8(im_path, imxx.tag, ref=imxx)
            if image.tag == 'SMAP':
                zpln = sputm.find('ZPLN', image)
                assert (
                    bytes(sputm.mktag('BSTR', sputm.find('BSTR', image).data))
                    + bytes(sputm.mktag('ZPLN', zpln.data))
                    == imxx.data
                )
                assert zpln
                encoded += bytes(sputm.mktag('ZPLN', zpln.data))
                print(zpln.data)
                print('ORIG')
                sputm.render(image)
                print('ENCODED')
                sputm.render(
                    next(
                        sputm(schema=s).map_chunks(bytes(sputm.mktag('SMAP', encoded)))
                    ),
                )
            yield imxx, encoded
            print((im_path, imxx))
            # # uncomment for testing image import without changes
            # if imxx.tag == 'BOMP':
            #     assert encoded == imxx.data, (encoded, imxx.data)
        else:
            yield imxx, None


def make_wrap(images: Sequence[tuple[Element, bytes | None]]) -> bytes:
    off = 8 + 4 * len(images)
    with io.BytesIO() as offstream, io.BytesIO() as datastream:
        for imxx, custome in images:
            elim = bytes(sputm.mktag(imxx.tag, custome if custome else imxx.data))
            offstream.write(off.to_bytes(4, byteorder='little', signed=False))
            datastream.write(elim)
            off += len(elim)
        return bytes(
            sputm.mktag(
                'WRAP',
                bytes(sputm.mktag('OFFS', offstream.getvalue()))
                + datastream.getvalue(),
            )
        )


def make_room_images_patch(
    root: Iterable[Element],
    basedir: str,
    rnam: str,
    version: int,
    verify: bool = True,
) -> Iterator[tuple[str, bytes]]:
    for t in root:
        for lflf in get_rooms(t.children()):
            header, palette, room, rmim = read_room_settings(lflf)
            room_bg = None
            room_id = lflf.attribs.get('gid')

            for imxx in read_room(header, rmim):
                if imxx.tag.startswith('ZP'):
                    # TODO: handle ZPXX
                    continue

                im_path = (
                    f'{room_id:04d}_{rnam.get(room_id)}'
                    if room_id in rnam
                    else os.path.dirname(imxx.attribs['path'])
                )
                im_path = im_path.replace(os.path.sep, '_')
                im_path = os.path.join(basedir, 'backgrounds', f'{im_path}.png')

                chunk = bytes(sputm.mktag(imxx.tag, imxx.data))
                s = sputm.generate_schema(chunk)
                image = next(sputm(schema=s).map_chunks(chunk))

                if os.path.exists(im_path):
                    # res_path = os.path.join(dirname, imxx.attribs['path'])
                    encoded = encode_block_v8(
                        im_path,
                        imxx.tag,
                        version=version,
                        ref=imxx,
                    )
                    if encoded:
                        if image.tag == 'SMAP':
                            if version >= 8:
                                zpln = sputm.find('ZPLN', image)
                                assert (
                                    bytes(
                                        sputm.mktag(
                                            'BSTR', sputm.find('BSTR', image).data
                                        )
                                    )
                                    + bytes(sputm.mktag('ZPLN', zpln.data))
                                    == imxx.data
                                )
                                assert zpln
                                encoded += bytes(sputm.mktag('ZPLN', zpln.data))
                        yield (
                            imxx.attribs['path'],
                            bytes(sputm.mktag(imxx.tag, encoded)),
                        )

                        if verify:
                            el = next(sputm(schema=s).map_chunks(bytes(sputm.mktag(imxx.tag, encoded))))

                            im = Image.open(im_path)
                            npim = np.asarray(im, dtype=np.uint8)

                            read_image = read_room_background if version < 8 else read_room_background_v8

                            assert  np.array_equal(read_image(
                                el,
                                header.width,
                                header.height,
                                header.zbuffers,
                            ), npim)
                        # os.makedirs(os.path.dirname(res_path), exist_ok=True)
                        # write_file(res_path, sputm.mktag(imxx.tag, encoded))
                    print((im_path, imxx.attribs['path'], imxx.tag))

            for path, obj_name, imag, obj_header in read_objects(room, version):
                if imag.tag == 'WRAP':
                    images = list(
                        encode_images_v8(
                            os.path.join(basedir, 'objects'),
                            imag,
                            obj_name,
                            room_id,
                            rnam,
                        ),
                    )
                    if any(custome is not None for imxx, custome in images):
                        # res_path = os.path.join(dirname, imag.attribs['path'])
                        yield imag.attribs['path'], make_wrap(images)
                        # os.makedirs(os.path.dirname(res_path), exist_ok=True)
                        # write_file(res_path, make_wrap(images))

                        # path = bomp.attribs['path']
                        # name = f'{obj_name}_{iidx:04d}'

                        # im_path = f'{room_id:04d}_{name}' if room_id in rnam else path
                        # im_path = im_path.replace(os.path.sep, '_')
                        # im_path = os.path.join(basedir, 'objects', f'{im_path}.png')

                        # if os.path.exists(im_path):
                        #     res_path = os.path.join(dirname, imxx.attribs['path'])
                        #     encoded = encode_block(im_path, imxx.tag)
                        #     if encoded:
                        #         # TODO: fix OFFS when inside WRAP
                        #         # maybe should avoid flattening the generator
                        #         os.makedirs(os.path.dirname(res_path), exist_ok=True)
                        #         write_file(
                        #             res_path,
                        #             encoded
                        #         )
                        #     print((im_path, res_path, imxx.tag))
                else:
                    im_path = f'{room_id:04d}_{obj_name}' if room_id in rnam else path

                    im_path = im_path.replace(os.path.sep, '_')
                    im_path = os.path.join(basedir, 'objects', f'{im_path}.png')

                    chunk = bytes(sputm.mktag(imag.tag, imag.data))
                    s = sputm.generate_schema(chunk)
                    image = next(sputm(schema=s).map_chunks(chunk))

                    # print(im_path, imag)
                    if os.path.exists(im_path):
                        print('exists')
                        encoded = encode_block_v8(
                            im_path,
                            imag.tag,
                            version=version,
                            ref=imag,
                        )
                        if encoded:
                            yield (
                                imag.attribs['path'],
                                bytes(sputm.mktag(imag.tag, encoded)),
                            )
                            # os.makedirs(os.path.dirname(res_path), exist_ok=True)
                            # write_file(res_path, sputm.mktag(imxx.tag, encoded))
                            if verify:
                                el = next(sputm(schema=s).map_chunks(bytes(sputm.mktag(imag.tag, encoded))))

                                im = Image.open(im_path)
                                npim = np.asarray(im, dtype=np.uint8)

                                read_image = read_room_background if version < 8 else read_room_background_v8

                                assert  np.array_equal(read_image(
                                    el,
                                    *im.size,
                                    0,
                                ), npim)

                        print((im_path, imag.attribs['path'], imag.tag))
