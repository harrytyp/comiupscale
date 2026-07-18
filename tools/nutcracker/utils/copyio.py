import functools
import io
from collections.abc import Callable, Iterator


def buffered(
    source: Callable[[int | None], bytes],
    buffer_size: int = io.DEFAULT_BUFFER_SIZE,
) -> Iterator[bytes]:
    return iter(functools.partial(source, buffer_size), b'')
