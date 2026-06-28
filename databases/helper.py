def build_database_url(
    host: str, port: int, name: str, user: str, password: str
) -> str:
    """Assemble the asyncpg connection URL from individual components."""
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
