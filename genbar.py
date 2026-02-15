from argparse import ArgumentParser, FileType
from struct import pack
from zlib import crc32, compress
import struct


def code39(ch):
    base = "04140124021234031323"
    spaces = "2341"
    alpha = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ-. *"
    code = alpha.index(ch)
    pattern = list("IIIII")
    for idx in map(int, base[(code % 10) * 2 :][:2]):
        pattern[idx] = "X"
    space = int(spaces[code // 10])
    pattern.insert(space, " ")
    return "".join(pattern)


def bar(pat):
    return {"I": (0, 1), "X": (0, 3), " ": (255, 1)}[pat]


FONT_WIDTH = 7
FONT_HEIGHT = 9
FONT = {
    "E": [1, 19, 115, 83, 67, 83, 115, 19, 1],
    "F": [1, 19, 115, 83, 67, 83, 115, 115, 97],
    "0": [67, 25, 25, 25, 25, 25, 25, 25, 67],
    "1": [111, 103, 97, 103, 103, 103, 103, 103, 1],
    "2": [67, 25, 29, 31, 79, 103, 115, 25, 1],
    "3": [67, 25, 29, 31, 71, 31, 29, 25, 67],
    "4": [95, 79, 71, 67, 73, 73, 65, 79, 7],
    "5": [1, 25, 121, 121, 65, 31, 31, 25, 67],
    "6": [79, 103, 115, 121, 65, 25, 25, 25, 67],
    "7": [1, 25, 31, 79, 79, 79, 103, 103, 103],
    "8": [67, 25, 25, 25, 67, 25, 25, 25, 67],
    "9": [67, 25, 25, 25, 3, 31, 79, 103, 115],
}


def empty(w: int, h: int) -> list[list[int]]:
    return [[255 for x in range(w)] for y in range(h)]


def text(t: str) -> list[list[int]]:
    img = empty(FONT_WIDTH * len(t), FONT_HEIGHT)
    for x in range(len(img[0])):
        (i, ox) = divmod(x, FONT_WIDTH)
        for y in range(FONT_HEIGHT):
            img[y][x] = ((FONT[t[i]][y] >> ox) & 1) * 255
    return img


def png(img: list[list[int]]) -> bytes:
    def chunk(ty: bytes, data: bytes) -> bytes:
        tydat = struct.pack(f"4s{len(data)}s", ty, data)
        return struct.pack(f"!I{len(tydat)}sI", len(data), tydat, crc32(tydat))

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack("!IIBBBBB", len(img[0]), len(img), 8, 0, 0, 0, 0))
    idat = chunk(b"IDAT", compress(bytes([y for x in img for y in [0] + x])))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


BAR_HEIGHT = 60
BAR_LEADIN = 4
TEXT_HEIGHT = 10
TEXT_PADDING = 3

if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("code", type=str)
    ap.add_argument("dest", type=FileType("wb"))
    args = ap.parse_args()

    pattern = " ".join(" ".join(code39(ch)) for ch in "*" + args.code + "*")
    bars = tuple(bar(p) for p in pattern)
    length = sum(b[1] for b in bars)
    w, h = (
        BAR_LEADIN + length + BAR_LEADIN,
        BAR_HEIGHT + TEXT_PADDING + TEXT_HEIGHT + TEXT_PADDING,
    )
    img = empty(w, h)
    x = BAR_LEADIN
    for color, length in bars:
        for i in range(length):
            for y in range(0, BAR_HEIGHT):
                img[y][x] = color
            x += 1
    for y, row in enumerate(text(args.code)):
        for x, col in enumerate(row):
            img[BAR_HEIGHT + TEXT_PADDING + y][w // 2 - len(row) // 2 + x] = col
    args.dest.write(png(img))
