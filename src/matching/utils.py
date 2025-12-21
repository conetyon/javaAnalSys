# src/matching/utils.py
import json

def safe_read_json(raw, default=None):
    if default is None: default = {}
    if raw is None: return default
    try:
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode('utf-8', errors='ignore')
        return json.loads(raw)
    except Exception:
        return default

def tokenize_to_set(tokens):
    out = set()
    for t in (tokens or []):
        if isinstance(t, str):
            s = t.strip().lower()
            if s: out.add(s)
    return out
