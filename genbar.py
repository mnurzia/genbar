from argparse import ArgumentParser, FileType
from struct import pack
from zlib import crc32, compress
from typing import Iterator


def code39(s) -> str:
    def unit(ch) -> str:
        base = "04140124021234031323"
        spaces = "2341"
        alpha = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ-. *"
        code = alpha.index(ch)
        pattern = list("IIIII")
        for idx in map(int, base[(code % 10) * 2 :][:2]):
            pattern[idx] = "X"
        space = int(spaces[code // 10])
        pattern.insert(space, " ")
        return " ".join(pattern).replace("X", "III")

    return " ".join(unit(ch) for ch in "*" + s + "*")


def code128(s) -> str:
    def unit(n) -> str:
        return str(
            [
                [212222, 222122, 222221, 121223, 121322, 131222, 122213, 122312],
                [132212, 221213, 221312, 231212, 112232, 122132, 122231, 113222],
                [123122, 123221, 223211, 221132, 221231, 213212, 223112, 312131],
                [311222, 321122, 321221, 312212, 322112, 322211, 212123, 212321],
                [232121, 111323, 131123, 131321, 112313, 132113, 132311, 211313],
                [231113, 231311, 112133, 112331, 132131, 113123, 113321, 133121],
                [313121, 211331, 231131, 213113, 213311, 213131, 311123, 311321],
                [331121, 312113, 312311, 332111, 314111, 221411, 431111, 111224],
                [111422, 121124, 121421, 141122, 141221, 112214, 112412, 122114],
                [122411, 142112, 142211, 241211, 221114, 413111, 241112, 134111],
                [111242, 121142, 121241, 114212, 124112, 124211, 411212, 421112],
                [421211, 212141, 214121, 412121, 111143, 111341, 131141, 114113],
                [114311, 411113, 411311, 113141, 114131, 311141, 411131, 211412],
                [211214, 211232, 2331112],
            ][n // 8][n % 8]
        )

    def opt(typ: str, suf: str) -> Iterator[tuple[str, str, int]]:
        first, rest = suf[0], suf[1:]
        second = rest[0] if len(rest) else None
        if first.isdigit():
            if typ == "X":
                yield ("C", suf, 105)  # start C
                yield ("B", suf, 104)  # start B
            elif typ == "B":
                yield ("C", suf, 99)  # switch C
                yield ("B", rest, ord(first) - 32)  # keep B
            else:  # typ == "C"
                if second is not None and second.isdigit():
                    yield ("C", rest[1:], int(first + second))  # two digits, stay C
                else:
                    yield ("B", suf, 100)  # switch B
        else:
            if typ == "X":
                yield ("B", suf, 104)  # start B
            elif typ == "B":
                yield ("B", rest, ord(first) - 32)  # keep B
            else:  # typ == "C"
                yield ("B", suf, 100)  # switch B

    def search():
        q = [(typ, suf, [] + [num]) for typ, suf, num in opt("X", s)]
        while True:
            nextq = []
            for typ, suf, syms in q:
                for nexttyp, nextsuf, nextsym in opt(typ, suf):
                    nextq.append((nexttyp, nextsuf, syms + [nextsym]))
                    if nextsuf == "":
                        return nextq[-1][2]
            q = nextq

    enc = search()
    idxs = [(enc[0], 1)] + [(ch, i + 1) for i, ch in enumerate(enc[1:])]
    cksum = sum((o % 103) * w for o, w in idxs) % 103
    units = [o for o, _ in idxs] + [cksum] + [106]
    return "".join(
        "".join(
            ("I" if i % 2 == 0 else " ") * int(ch)
            for u in units
            for i, ch in enumerate(unit(u))
        )
    )


def bar(pat: str) -> int:
    return {"I": 0, " ": 255}[pat]


FONT_WIDTH = 7
FONT_HEIGHT = 9
FONT = {
    "A": [119, 99, 99, 73, 73, 28, 0, 28, 28],
    "B": [65, 25, 25, 25, 65, 25, 25, 25, 65],
    "C": [71, 19, 57, 121, 121, 121, 121, 19, 71],
    "D": [64, 25, 25, 25, 25, 25, 25, 25, 64],
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
    return [[255 for _ in range(w)] for _ in range(h)]


def text(t: str) -> list[list[int]]:
    img = empty(FONT_WIDTH * len(t), FONT_HEIGHT)
    for x in range(len(img[0])):
        (i, ox) = divmod(x, FONT_WIDTH)
        for y in range(FONT_HEIGHT):
            img[y][x] = ((FONT[t[i]][y] >> ox) & 1) * 255
    return img


def png(img: list[list[int]]) -> bytes:
    def chunk(ty: bytes, data: bytes) -> bytes:
        tydat = pack(f"4s{len(data)}s", ty, data)
        return pack(f"!I{len(tydat)}sI", len(data), tydat, crc32(tydat))

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", pack("!IIBBBBB", len(img[0]), len(img), 8, 0, 0, 0, 0))
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
    ap.add_argument("--type", choices=["39", "128"], default="39")
    args = ap.parse_args()
    pattern = code39(args.code) if args.type == "39" else code128(args.code)
    bars = tuple(bar(p) for p in pattern)
    length = len(bars)
    w = BAR_LEADIN + length + BAR_LEADIN
    h = BAR_HEIGHT + TEXT_PADDING + TEXT_HEIGHT + TEXT_PADDING
    img = empty(w, h)
    x = BAR_LEADIN
    for color in bars:
        for y in range(0, BAR_HEIGHT):
            img[y][x] = color
        x += 1
    for y, row in enumerate(text(args.code)):
        for x, col in enumerate(row):
            img[BAR_HEIGHT + TEXT_PADDING + y][w // 2 - len(row) // 2 + x] = col
    args.dest.write(png(img))
