from __future__ import annotations

from typing import cast

import hikari
from pydantic import model_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic_settings import BaseSettings, SettingsConfigDict

from autohelper.framework.app import get_app

__all__ = (
    "Category",
    "Channel",
    "Channels",
    "GuildForumChannel",
    "GuildTextChannel",
    "GuildVoiceChannel",
)


@pydantic_dataclass
class Channel[
    HikariChannel: hikari.PrivateChannel | hikari.GuildChannel = hikari.GuildTextChannel  # type: ignore[misc]
]:
    channel_id: int

    def get_channel(self) -> HikariChannel:
        app = get_app()
        channel = app.bot.cache.get_guild_channel(self.channel_id)
        if not channel:
            msg = f"Channel {self.channel_id} not found in cache"
            raise LookupError(msg)
        return cast("HikariChannel", channel)

    @model_validator(mode="before")
    @classmethod
    def _maybe_from_int(cls, obj: object) -> object:
        if isinstance(obj, int):
            return {"channel_id": obj}
        return obj


type GuildTextChannel = Channel[hikari.GuildTextChannel]
type GuildForumChannel = Channel[hikari.GuildForumChannel]
type GuildVoiceChannel = Channel[hikari.GuildVoiceChannel]


class Channels(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")


class Category(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")
