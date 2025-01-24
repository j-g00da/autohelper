from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from dataclasses import InitVar, dataclass
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

import arc
import hikari
import logfire
from hikari.impl.config import CacheSettings, HTTPSettings, ProxySettings
from hikari.internal.data_binding import JSONDecoder, JSONEncoder

from autohelper.framework.features import Feature, FeatureSet
from autohelper.settings import AutoHelperSettings, get_app_settings

if TYPE_CHECKING:
    from _typeshed import StrPath

_app_state_var: ContextVar[AppState] = ContextVar("app_state")


def get_app_state() -> AppState:
    return _app_state_var.get()


class BotArgs(TypedDict, total=False):
    allow_color: bool
    banner: str | None
    force_color: bool
    cache_settings: CacheSettings | None
    http_settings: HTTPSettings | None
    dumps: JSONEncoder
    loads: JSONDecoder
    intents: hikari.Intents
    auto_chunk_members: bool
    logs: StrPath | int | dict[str, Any]
    max_rate_limit: float
    max_retries: int
    proxy_settings: ProxySettings | None
    rest_url: str | None


class RunArgs(TypedDict, total=False):
    activity: hikari.Activity | None
    afk: bool
    check_for_updates: bool
    coroutine_tracking_depth: int | None
    enable_signal_handlers: bool | None
    idle_since: datetime | None
    ignore_session_start_limit: bool
    large_threshold: int
    propagate_interrupts: bool
    status: hikari.Status
    shard_ids: Sequence[int] | None
    shard_count: int | None


@dataclass(frozen=True)
class AppState:
    settings: AutoHelperSettings
    update_current_context: InitVar[bool]

    def __post_init__(self, update_current_context: bool) -> None:
        if not update_current_context:
            return
        _app_state_var.set(self)

    @cached_property
    def bot_args(self) -> BotArgs:
        return BotArgs()

    @cached_property
    def run_args(self) -> RunArgs:
        return RunArgs()

    @cached_property
    def bot(self) -> hikari.GatewayBot:
        return hikari.GatewayBot(
            self.settings.bot_token.get_secret_value(),
            suppress_optimization_warning=True,
            executor=ThreadPoolExecutor(thread_name_prefix="autohelper_"),
            **self.bot_args,
        )

    @cached_property
    def client(self) -> arc.GatewayClient:
        return arc.GatewayClient(
            self.bot,
            default_enabled_guilds=self.settings.default_enabled_guilds,
            is_dm_enabled=self.settings.dm_enabled,
        )

    @cached_property
    def feature_set(self) -> FeatureSet:
        return FeatureSet(
            [
                Feature(package_name, update_state_registry=True)
                for package_name in self.settings.install_features
                + self.settings.extra_features
            ]
        )

    def configure(self) -> None:
        self.feature_set.call("configure")

    def run(self) -> None:
        import __main__

        self.feature_set.call("setup")

        with logfire.span(
            "Starting the bot initiated by {module}...",
            module=Path(__main__.__file__).relative_to(Path.cwd()),
        ):
            self.bot.run(
                **self.run_args,
                asyncio_debug=__debug__,
                close_passed_executor=True,
            )

    async def stop(self) -> None:
        await self.bot.close()


def configure() -> None:
    app = AppState(get_app_settings(), update_current_context=True)
    app.configure()


def run() -> None:
    get_app_state().run()
