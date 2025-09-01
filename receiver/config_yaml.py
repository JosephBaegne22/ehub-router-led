# receiver/config_yaml.py
from typing import Any, Dict, Optional
import os, yaml

DEFAULTS: Dict[str, Any] = {
    "excel": "faker/Ecran (2).xlsx",
    "fps": 40.0,
    "order": "RGB",
    "listen_ip": "0.0.0.0",
    "listen_port": 50000,
    "dmx_monitor": False,
    "monitor_every": 20,
    "monitor_channels": 12,
    "patch_csv": None,
}

def load_config(path: Optional[str]) -> Dict[str, Any]:
    cfg = DEFAULTS.copy()
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for k, v in data.items():
            if k in cfg:
                cfg[k] = v
    return cfg
