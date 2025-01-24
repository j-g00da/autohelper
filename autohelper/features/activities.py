import arc
import hikari
from pydantic_settings import BaseSettings

from autohelper.app import get_app_state
from autohelper.framework import use_config

__all__ = (
    "configure",
    "get_config",
    "setup",
)

plugin = arc.GatewayPlugin(__name__)


class ActivityConfig(BaseSettings):
    initial_activity_name: str | None = None
    initial_activity_state: str | None = None


def update_run_args() -> None:
    app, config = get_app_state(), get_config()

    if config.initial_activity_name:
        app.run_args["activity"] = hikari.Activity(
            name=config.initial_activity_name,
            state=config.initial_activity_state,
        )


configure, get_config, get_state = use_config(
    ActivityConfig,
    section="builtin.activities",
    hooks=[update_run_args],
)


def setup() -> None:
    app = get_app_state()
    app.client.add_plugin(plugin)
