import arc
from pydantic import BaseModel

from autohelper.app import get_app_state
from autohelper.features.channels import Category, GuildTextChannel
from autohelper.framework import use_config

plugin = arc.GatewayPlugin(__name__)


class CommunityCategory(Category):
    main: GuildTextChannel
    forum: GuildTextChannel


class InternalCategory(Category):
    admins: GuildTextChannel


class ChannelsConfig(BaseModel):
    community: CommunityCategory
    internal: InternalCategory


configure, get_channels, get_state = use_config(
    ChannelsConfig,
    section="gauss-channels",
)


def setup() -> None:
    app = get_app_state()
    app.client.add_plugin(plugin)
