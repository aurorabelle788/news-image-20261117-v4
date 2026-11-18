#!/usr/bin/env python3
"""Entry point for news-image-20261117 v4.

Copies the pre-rendered front-page image to the output directory
after checking it is a whole JPEG (SOI at the start, EOI at the end)
with a readable frame header of exactly 1024x1024, then verifies the
copy is byte-for-byte identical to the source and still 1024x1024.
A one-line verification summary goes to stderr.
"""
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "entry.png")
EXPECTED_SIZE = (1024, 1024)

# Markers with no length field (standalone): TEM, RST0-RST7, SOI, EOI.
_STANDALONE = {0x01, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9}
_SOF = {0xC0, 0xC2}  # baseline / progressive frame headers


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def jpeg_dimensions(data):
    """Return (width, height) from the JPEG SOF0/SOF2 frame header.

    Walks the marker segments (stdlib only, no pixel decoding).
    Returns None when no frame header can be read.
    """
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None
    pos = 2
    while pos + 1 < len(data):
        if data[pos] != 0xFF:
            return None
        # Skip padding 0xFF bytes; a 0x00 after 0xFF is stuffed data.
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            return None
        marker = data[pos]
        pos += 1
        if marker == 0x00:
            return None
        if marker in _STANDALONE:
            continue
        if pos + 2 > len(data):
            return None
        seg_len = (data[pos] << 8) | data[pos + 1]
        if seg_len < 2:
            return None
        if marker in _SOF:
            if pos + 7 > len(data):
                return None
            height = (data[pos + 3] << 8) | data[pos + 4]
            width = (data[pos + 5] << 8) | data[pos + 6]
            return (width, height)
        if marker == 0xDA:  # start of scan: no frame header before it
            return None
        pos += seg_len
    return None


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    with open(SRC, "rb") as f:
        data = f.read()
    if data[0:2] != b"\xff\xd8" or data[-2:] != b"\xff\xd9":
        print("entry.png is not a whole JPEG (bad SOI/EOI)", file=sys.stderr)
        return 1
    dims = jpeg_dimensions(data)
    if dims is None:
        print("entry.png has no readable JPEG frame header", file=sys.stderr)
        return 1
    if dims != EXPECTED_SIZE:
        print("entry.png is %dx%d, expected 1024x1024" % dims,
              file=sys.stderr)
        return 1
    dst = os.path.join(out_dir, "entry.png")
    shutil.copyfile(SRC, dst)
    if sha256(SRC) != sha256(dst):
        print("copy is not byte-identical to entry.png", file=sys.stderr)
        return 1
    with open(dst, "rb") as f:
        copy_dims = jpeg_dimensions(f.read())
    if copy_dims != EXPECTED_SIZE:
        print("copy is not 1024x1024", file=sys.stderr)
        return 1
    digest = sha256(dst)
    print("wrote", dst, "sha256", digest)
    print("verified entry.png: %d bytes, sha256 %s…, %dx%d, byte-identical"
          % (len(data), digest[:8], dims[0], dims[1]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
