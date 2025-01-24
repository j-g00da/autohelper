from __future__ import annotations

import sys
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Self

from autohelper.framework import debugging

__all__ = (
    "ExceptionSink",
    "guess_module_name",
)


@dataclass
class ExceptionSink:
    exception_list: list[Exception] = field(default_factory=list)
    message: str = "Caught some exceptions"

    def __post_init__(self) -> None:
        debugging.save_location(self, stack_offset=2)

    def throw(self, message: str | None = None) -> None:
        if not self.exception_list:
            return
        try:
            raise ExceptionGroup(message or self.message, self.exception_list)
        finally:
            self.exception_list.clear()

    @contextmanager
    def collect(self) -> Generator[None]:
        try:
            yield
        except Exception as exc:  # noqa: BLE001
            self.exception_list.append(exc)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        match exc_info:
            case [_, Exception() as exc, _] if exc is not None:
                self.exception_list.append(exc)
            case _:
                pass
        self.throw()

    def __del__(self) -> None:
        if not self.exception_list:
            return
        location = debugging.get_location_info(self)
        msg = (
            f"{len(self.exception_list)} exceptions gathered in "
            f"{'a' if location is None else 'this'} stack were never propagated!"
        )
        if location is None:
            warnings.warn(
                msg,
                category=RuntimeWarning,
                stacklevel=1,
            )
        else:
            warnings.warn_explicit(
                msg,
                category=RuntimeWarning,
                filename=location.filename,
                lineno=location.lineno,
            )


def guess_module_name(stack_offset: int = 2) -> str:
    name: str = sys._getframe(stack_offset).f_globals["__name__"]  # noqa: SLF001
    return name
