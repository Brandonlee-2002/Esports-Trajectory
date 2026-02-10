import json
from typing import Any, Dict


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # minimal defaults
    cfg.setdefault("max_players", 0)
    cfg.setdefault("request_timeout_s", 30)
    cfg.setdefault("throttle_s", 0.5)
    return cfg
