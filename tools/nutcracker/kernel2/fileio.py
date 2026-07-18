import tempfile
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from types import TracebackType
from typing import cast, overload

import numpy as np
from numpy.typing import ArrayLike


class ResourceFile(AbstractContextManager[memoryview]):
    __slots__ = ('buffer', 'closed')

    def __init__(self, buffer: ArrayLike) -> None:
        self.buffer = memoryview(buffer)  # type: ignore[arg-type]
        self.closed = False

    def __len__(self) -> int:
        return len(self.buffer)

    def __buffer__(self, _flags: int) -> memoryview:
        return self.buffer

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> bool | None:
        self.close()
        return None

    @overload
    def __getitem__(self, index: slice) -> ArrayLike: ...
    @overload
    def __getitem__(self, index: int) -> int: ...
    def __getitem__(self, index: slice | int) -> ArrayLike | int:
        if not self.closed:
            return self.buffer[index]
        raise OSError('I/O operation on closed file')  # noqa: TRY003

    @classmethod
    @contextmanager
    def load(cls, file_path: str, key: int = 0x00) -> Iterator[memoryview]:
        data = np.memmap(file_path, dtype='u1', mode='r')

        # if key == 0x00:
        #     yield cast(memoryview, cls(data))
        #     return

        with tempfile.TemporaryFile() as tmp:
            result = np.memmap(tmp, dtype='u1', mode='w+', shape=data.shape)
            result[:] = data ^ key
            result.flush()
            del result
            with cls(np.memmap(tmp, dtype='u1', mode='r', shape=data.shape)) as f:
                yield f

    def close(self) -> None:
        self.closed = True


def read_file(file_path: str, key: int = 0x00) -> bytes:
    with ResourceFile.load(file_path, key=key) as res:
        return bytes(res)
