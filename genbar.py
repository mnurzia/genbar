from argparse import ArgumentParser, FileType
from struct import pack
from zlib import crc32, compress
from typing import Iterator
from base64 import b85decode


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
        first, second, rest = suf[0], suf[1] if len(suf) > 1 else None, suf[1:]
        if typ == "X":
            if first.isdigit():
                yield ("C", suf, 105)  # start C
            yield ("B", suf, 104)  # start B
        elif typ == "B":
            if first.isdigit():
                yield ("C", suf, 99)  # switch C
            yield ("B", rest, ord(first) - 32)  # encode B
        else:  # typ == "C":
            if first.isdigit() and second is not None and second.isdigit():
                yield ("C", rest[1:], int(first + second))  # encode C
            else:
                yield ("B", suf, 100)  # switch B

    def search():
        q, nextq = [("X", s, [])], []
        while True:
            for typ, suf, syms in q:
                for nexttyp, nextsuf, nextsym in opt(typ, suf):
                    nextq.append((nexttyp, nextsuf, syms + [nextsym]))
                    if nextsuf == "":
                        return nextq[-1][2]
            q, nextq = nextq, []

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
FONT_HEIGHT = 11
FONT_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
FONT = """
5B&4bJ`Bl|F#rFCWXYIjOqqxO{(Sl8&z^k9AOGQ*GG-5+dFTKC49WBGeEBj5|M2tR$&(H|`~UyLGIacN
=S;)@{0W|U=bt)eAOGNU=g*%$9Q*(OhGfZ;CQO-!|M(NWdFP&e$RGdV=g*!QlO|06{&Gy5eeubXbN~CY
WWgv<p~Ij5_s5P*nI{e$|Na@1CQO+!WY7Qb^XJc>K6Ide|Au7g_<mfOhyVGBGH}T<WXuoe;mIga;lq+~
|Nq0!m?lh_GXwwpa!wpLaO9kS|Cur*ND?GWng9IZLWK$d5OC-J;0*cm=g*%!KmRc%Oq@7m$ua-_IWlL@
pFVhh|KaD)pFVu~;s5?*$&(;VnKEbp@Z`*y6X(e||Nr6V&YU`Y$$|g;2|je;)8<SM|L_c%GGxh<FhBo}
PtTt|T$7Lg{1YZj!7^mbAOFrA0CG&6c>Dh
"""


def empty(w: int, h: int) -> list[list[int]]:
    return [[255 for _ in range(w)] for _ in range(h)]


def text(t: str) -> list[list[int]]:
    dec = int.from_bytes(b85decode(FONT.replace("\n", "")))
    img = empty(FONT_WIDTH * len(t), FONT_HEIGHT)
    for x in range(len(img[0])):
        (i, ox) = divmod(x, FONT_WIDTH)
        for y in range(FONT_HEIGHT):
            idx = (
                FONT_ALPHA.index(t[i]) * (FONT_WIDTH * FONT_HEIGHT)
                + y * FONT_WIDTH
                + ox
            )
            img[y][x] = 255 if dec & (1 << idx) else 0
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
