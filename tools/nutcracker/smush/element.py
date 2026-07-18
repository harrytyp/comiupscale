from collections.abc import Iterator

from nutcracker.kernel2.element import Element


def check_tag(target: str, elem: Element) -> Element:
    if elem.tag != target:
        raise ValueError(f'expected tag to be {target} but got {elem.tag}')
    return elem


def read_elements(target: str, elem: Element) -> Iterator[Element]:
    return check_tag(target, elem).children()


def read_data(target: str, elem: Element) -> bytes:
    return check_tag(target, elem).data
