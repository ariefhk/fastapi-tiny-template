from slowapi import Limiter
from slowapi.util import get_remote_address

from commons.config import get_configs

_cfg = get_configs()


limiter = Limiter(
    key_func=get_remote_address,
    enabled=_cfg.RATE_LIMIT_ENABLED,
    storage_uri=_cfg.RATE_LIMIT_STORAGE_URI,
)


RATE_LIMIT_CONFIGS = {
    "read": "15/15seconds;60/minute;2000/hour",
    "write": "10/15seconds;30/minute;600/hour",
    "auth": "5/minute;100/hour",
    "sensitive": "5/30seconds;10/minute;50/hour",
    "public": "5/15seconds;20/minute;300/hour",
}
