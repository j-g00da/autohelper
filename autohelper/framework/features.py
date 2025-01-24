from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Sequence
from dataclasses import KW_ONLY, InitVar, dataclass, field
from functools import cached_property, partial
from threading import local
from typing import TYPE_CHECKING, Any, Final

import logfire
from pydantic import BaseModel

from autohelper.framework import debugging
from autohelper.framework.utils import ExceptionSink, guess_module_name
from autohelper.settings import get_app_settings

__all__ = ("Feature", "get_state", "use_config")


class FeatureConfigurationError(ValueError):
    """Raised when a feature module is missing required components."""


class FeatureNotReadyError(RuntimeError):
    """Raised when a feature module is not ready for an operation."""


class FeatureStateNotFoundError(RuntimeError):
    """Raised when a feature's state could not have been found."""


@dataclass
class FeatureState[SettingsModel: BaseModel]:
    package_name: Final[str]  # type: ignore[misc]  # "must be initialized"
    config_hooks: list[Callable[[], object]] = field(default_factory=list)

    _config = None

    def get_config(self) -> SettingsModel:
        if self._config is None:
            msg = (
                f"Tried to access feature {self.package_name!r} "
                "configuration, but it was not created yet"
            )
            raise FeatureNotReadyError(msg)
        return self._config

    @property
    def config(self) -> SettingsModel:
        return self.get_config()

    @config.setter
    def config(self, value: SettingsModel) -> None:
        old_config, new_config = self._config, value
        self._config = new_config
        if old_config == new_config or not self.config_hooks:
            return
        with ExceptionSink(
            message="Error calling configuration hooks",
        ) as sink:
            for hook in self.config_hooks:
                with sink.collect():
                    hook()


_state_registry = local()


def get_state_safe(
    package_name: str | None = None,
    stack_offset: int = 1,
) -> FeatureState[Any] | None:
    if package_name is None:
        package_name = guess_module_name(stack_offset=stack_offset + 1)
    return getattr(_state_registry, package_name, None)


def get_state(
    package_name: str | None = None,
    stack_offset: int = 1,
) -> FeatureState[Any]:
    if package_name is None:
        package_name = guess_module_name(stack_offset=stack_offset + 1)
    maybe_state = get_state_safe(package_name)
    if maybe_state is None:
        msg = (
            f"Tried to access feature state of {package_name!r}, "
            "but its state is unknown"
        )
        raise FeatureStateNotFoundError(msg)
    return maybe_state


@dataclass
class Feature:
    package_name: str
    _: KW_ONLY
    update_state_registry: InitVar[bool]

    if TYPE_CHECKING:
        state: FeatureState[Any] = field(init=False)

    def __post_init__(self, update_state_registry: bool) -> None:
        self.state = FeatureState(self.package_name)
        if not update_state_registry:
            return
        setattr(_state_registry, self.package_name, self.state)

    def import_package(self) -> Any:
        settings = get_app_settings()
        sys.path.extend(map(str, settings.feature_paths))
        try:
            return importlib.import_module(self.package_name)
        except ImportError as exc:
            msg = f"Could not import {self.package_name!r}"
            raise FeatureConfigurationError(msg) from exc

    @cached_property
    def package(self) -> Any:
        return self.import_package()

    def call(
        self,
        routine_name: str,
        *,
        required: bool = False,
        warn_on_missing: bool = True,
    ) -> None:
        settings = get_app_settings()
        routine = getattr(self.package, routine_name, None)

        where = ""
        if not settings.quiet:
            where = " (enable __debug__ to reveal location)"
        if __debug__:
            location = debugging.get_location(routine)
            where = f" @ {location}" if location else ""

        if routine is not None:
            with logfire.span(
                "Routine {package_name}.{routine_name}{where}",
                routine_name=routine_name,
                package_name=self.package_name,
                where=where,
            ):
                routine()
            return

        if required:
            msg = f"Module {self.package_name!r} does not export {routine_name!r}"
            raise FeatureConfigurationError(msg)

        if warn_on_missing:
            logfire.warn(
                "Routine doesn't exist: {package_name}.{routine_name}",
                package_name=self.package_name,
                routine_name=routine_name,
            )


@dataclass
class FeatureSet:
    features: Sequence[Feature]

    def call(
        self,
        routine_name: str,
        *,
        required: bool = False,
        warn_on_missing: bool = True,
    ) -> None:
        with ExceptionSink(
            message=f"Got errors calling {routine_name!r}",
        ) as exc_stack:
            for feature in self.features:
                with exc_stack.collect():
                    feature.call(
                        routine_name,
                        required=required,
                        warn_on_missing=warn_on_missing,
                    )


def update_config[**P, SettingsModel: BaseModel](
    model: Callable[P, SettingsModel],
    name: str,
    state: FeatureState[SettingsModel],
    /,
    *new_args: P.args,
    **new_kwargs: P.kwargs,
) -> None:
    from autohelper.settings import get_app_settings

    debugging.save_location(model)

    settings = get_app_settings()

    try:
        feature_config: SettingsModel = state.get_config()
    except FeatureNotReadyError:
        old_kwargs = settings.features.get(name) or {}
        state.config = model(*new_args, **old_kwargs | new_kwargs)
        return

    if new_args or new_kwargs:
        old_kwargs = feature_config.model_dump(round_trip=True)
        state.config = model(*new_args, **old_kwargs | new_kwargs)


def use_config[**P, M: BaseModel](
    model: Callable[P, M],
    *,
    section: str,
    hooks: Sequence[Callable[[], object]] = (),
) -> tuple[Callable[P, None], Callable[[], M], Callable[[], FeatureState[M]]]:
    package_name = guess_module_name(stack_offset=2)
    state = get_state(package_name)
    state.config_hooks.extend(hooks)
    configure_callback = partial(update_config, model, section, state)  # type: ignore[call-arg]
    debugging.save_location(configure_callback, stack_offset=2)
    return (configure_callback, state.get_config, partial(get_state, package_name))
