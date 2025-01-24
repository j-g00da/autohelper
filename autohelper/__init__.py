from .app import configure, run

__all__ = ("configure", "run")


def script_run(package_name: str) -> None:
    import logfire

    from autohelper.framework import Feature

    logfire.configure()
    this = Feature(
        package_name=package_name,
        update_state_registry=True,
    )
    this.call("configure")
    this.call("run")


if __name__ == "__main__":
    script_run(__name__)
