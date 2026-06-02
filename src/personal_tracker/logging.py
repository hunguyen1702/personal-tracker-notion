from __future__ import annotations

import logging
import time
from zoneinfo import ZoneInfo

from .config import DEFAULT_TZ


def setup_logging(verbose: bool = False, tz: str = DEFAULT_TZ) -> logging.Logger:
    zone = ZoneInfo(tz)

    def _converter(secs: float | None) -> time.struct_time:
        from datetime import datetime

        ts = secs if secs is not None else time.time()
        return datetime.fromtimestamp(ts, tz=zone).timetuple()

    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    formatter.converter = _converter  # type: ignore[assignment]

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger("personal_tracker")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.propagate = False
    return root
