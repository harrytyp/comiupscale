import io
import os
import sys
from collections.abc import Iterable, Iterator
from typing import IO

from parse import parse  # type: ignore[import-untyped]

from nutcracker.kernel2.element import Element


def findall(tag: str, root: Iterable[Element] | Element | None) -> Iterator[Element]:
    if not root:
        return
    if isinstance(root, Element):
        root = root.children()
    for elem in root:
        if parse(tag, elem.tag, evaluate_result=False):
            yield elem


def find(tag: str, root: Iterable[Element] | Element | None) -> Element | None:
    return next(findall(tag, root), None)


def findpath(
    path: str, root: Iterable[Element] | Element | None
) -> Iterable[Element] | Element | None:
    path = os.path.normpath(path)
    if not path or path == '.':
        return root
    dirname, basename = os.path.split(path)
    return find(basename, findpath(dirname, root))


def render(
    element: Element,
    level: int = 0,
    stream: IO[str] = sys.stdout,
) -> None:
    attribs = ''.join(
        f' {key}="{value}"'
        for key, value in element.attribs.items()
        if value is not None
    )
    indent = '    ' * level
    children = list(element.children())
    closing = '' if children else ' /'
    print(f'{indent}<{element.tag}{attribs}{closing}>', file=stream)
    if children:
        for elem in children:
            render(elem, level=level + 1, stream=stream)
        print(f'{indent}</{element.tag}>', file=stream)


def renders(element: Element) -> str:
    with io.StringIO() as stream:
        render(element, stream=stream)
        return stream.getvalue()
