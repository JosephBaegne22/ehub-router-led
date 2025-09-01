import struct, gzip
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union

MAGIC = b"eHuB"

@dataclass
class ConfigFrame:
    universe: int
    ranges: List[Tuple[int,int,int,int]]

@dataclass
class UpdateFrame:
    universe: int
    entities: List[Tuple[int,int,int,int,int]]  # (id, r, g, b, w)

def parse_packet(data: bytes) -> Tuple[Optional[Union[ConfigFrame, UpdateFrame]], Optional[str]]:
    if len(data) < 10 or data[:4] != MAGIC:
        return None, "bad_magic_or_too_short"

    p = 4
    pkt_type = data[p]; p += 1
    universe  = data[p]; p += 1
    count     = struct.unpack_from("<H", data, p)[0]; p += 2
    comp_len  = struct.unpack_from("<H", data, p)[0]; p += 2

    if len(data) < p + comp_len:
        return None, "truncated_payload"

    comp_payload = data[p:p+comp_len]
    try:
        payload = gzip.decompress(comp_payload)
    except Exception as e:
        return None, f"gzip_error:{e}"

    if pkt_type == 1:  # CONFIG
        ranges = []
        off = 0
        while off + 8 <= len(payload):
            ss, se, es, ee = struct.unpack_from("<HHHH", payload, off)
            ranges.append((ss, se, es, ee))
            off += 8
        return ConfigFrame(universe, ranges), None

    elif pkt_type == 2:  # UPDATE
        ents = []
        off = 0
        while off + 6 <= len(payload):
            eid, r, g, b, w = struct.unpack_from("<HBBBB", payload, off)
            ents.append((eid, r, g, b, w))
            off += 6
        return UpdateFrame(universe, ents), None

    else:
        return None, f"unsupported_type:{pkt_type}"
