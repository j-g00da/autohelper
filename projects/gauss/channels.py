import arc
import hikari
from pydantic import BaseModel

from autohelper.abstract.channels import Category, Channel
from autohelper.framework import read_settings
from autohelper.framework.app import get_app

app = get_app()
plugin = arc.GatewayPlugin(__name__)
app.client.add_plugin(plugin)


class CommunityCategory(Category):
    main: Channel[hikari.GuildTextChannel]
    forum: Channel[hikari.GuildTextChannel]


class InternalCategory(Category):
    admins: Channel[hikari.GuildTextChannel]


class ChannelsConfig(BaseModel):
    community: CommunityCategory
    internal: InternalCategory


settings = read_settings(ChannelsConfig, section="channels")
