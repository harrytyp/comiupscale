import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def suppress_stdout() -> Iterator[None]:
    """
    Context manager that suppresses all print output.
    Within this context, output to sys.stdout is redirected to os.devnull.
    """
    with Path(os.devnull).open('w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
