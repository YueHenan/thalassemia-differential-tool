"""Reject accidental renaming of a non-Windows binary; report PE architecture/hash."""
import hashlib
import json
from pathlib import Path
import struct
import sys

path = Path(sys.argv[1])
data = path.read_bytes()
if data[:2] != b"MZ" or len(data) < 64:
    raise SystemExit("Not a Windows MZ/PE executable")
header = struct.unpack_from("<I", data, 0x3C)[0]
if header + 6 > len(data) or data[header:header + 4] != b"PE\x00\x00":
    raise SystemExit("Missing PE signature")
machine = struct.unpack_from("<H", data, header + 4)[0]
if machine != 0x8664:
    raise SystemExit(f"Expected Windows AMD64 (0x8664), found {machine:#x}")
print(json.dumps({"file": path.name, "format": "Windows PE", "architecture": "AMD64",
                  "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}, indent=2))
