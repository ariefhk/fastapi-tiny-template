from __future__ import annotations

from typing import TYPE_CHECKING

from commons.config import get_configs
from loggers.helper import get_logger

if TYPE_CHECKING:
    from sshtunnel import SSHTunnelForwarder

logger = get_logger(__name__)

_tunnel1: SSHTunnelForwarder | None = None
_tunnel2: SSHTunnelForwarder | None = None


def open_ssh_tunnels() -> SSHTunnelForwarder | None:
    """Open one or two SSH tunnels based on config and return the one to bind the engine to.

    Single hop  (DB_SSH_2_ENABLED=false): tunnel1 → DB
    Dual hop    (DB_SSH_2_ENABLED=true):  tunnel1 → jump host SSH, tunnel2 → DB
    Returns None when DB_SSH_ENABLED is false.
    """
    from sshtunnel import SSHTunnelForwarder as _Forwarder

    global _tunnel1, _tunnel2

    cfg = get_configs()

    if not cfg.DB_SSH_ENABLED:
        return None

    if cfg.DB_SSH_2_ENABLED:
        hop1_remote = (cfg.DB_SSH_2_HOST, cfg.DB_SSH_2_PORT)
    else:
        hop1_remote = (cfg.DB_SSH_REMOTE_BIND_HOST, cfg.DB_SSH_REMOTE_BIND_PORT)

    _tunnel1 = _Forwarder(
        (cfg.DB_SSH_HOST, cfg.DB_SSH_PORT),
        ssh_username=cfg.DB_SSH_USER,
        ssh_pkey=cfg.DB_SSH_PRIVATE_KEY_PATH,
        remote_bind_address=hop1_remote,
    )
    _tunnel1.start()
    logger.info(
        "ssh tunnel hop-1: connected to %s:%d", cfg.DB_SSH_HOST, cfg.DB_SSH_PORT
    )

    if cfg.DB_SSH_2_ENABLED:
        _tunnel2 = _Forwarder(
            ("127.0.0.1", _tunnel1.local_bind_port),
            ssh_username=cfg.DB_SSH_2_USER,
            ssh_pkey=cfg.DB_SSH_2_PRIVATE_KEY_PATH,
            remote_bind_address=(
                cfg.DB_SSH_REMOTE_BIND_HOST,
                cfg.DB_SSH_REMOTE_BIND_PORT,
            ),
        )
        _tunnel2.start()
        logger.info(
            "ssh tunnel hop-2: connected to %s:%d", cfg.DB_SSH_2_HOST, cfg.DB_SSH_2_PORT
        )
        return _tunnel2

    return _tunnel1


def close_ssh_tunnels() -> None:
    """Stop tunnels in reverse order (hop-2 first, then hop-1)."""
    global _tunnel1, _tunnel2

    for tunnel in (_tunnel2, _tunnel1):
        if tunnel is not None:
            try:
                tunnel.stop()
            except Exception:
                pass

    _tunnel1 = None
    _tunnel2 = None
