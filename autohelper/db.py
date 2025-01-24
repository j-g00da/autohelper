from sqlalchemy.orm import registry

__all__ = ("cache_metadata",)

cache_registry = registry()
cache_metadata = cache_registry.metadata
