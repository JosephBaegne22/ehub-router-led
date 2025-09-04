# receiver/patch_map.py
from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import csv, os

# mapping: (ip, universe) -> { from_channel: [to_channels...] }
PatchTable = Dict[Tuple[str, int], Dict[int, List[int]]]

def load_patch_csv(path: Optional[str]) -> PatchTable:
    table: PatchTable = {}
    if not path or not os.path.isfile(path):
        return table
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            ip = str(row["ip"]).strip()
            uni = int(row["universe"])
            src = int(row["from_channel"])
            dst = int(row["to_channel"])
            key = (ip, uni)
            table.setdefault(key, {}).setdefault(src, []).append(dst)
    return table

def apply_patch(ip: str, uni: int, dmx: bytearray, patch: PatchTable) -> bytearray:
    """Duplique les valeurs de channels source vers cibles. Retourne une copie patchée."""
    if not patch:
        return dmx
    key = (ip, uni)
    if key not in patch:
        return dmx
    out = bytearray(dmx)  # copie
    for src_ch, dst_list in patch[key].items():
        i = src_ch - 1  # DMX terrain = 1-indexé
        if 0 <= i < 512:
            val = dmx[i]
            for dst in dst_list:
                j = dst - 1
                if 0 <= j < 512:
                    out[j] = val
    return out
