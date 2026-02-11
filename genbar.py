from argparse import ArgumentParser, FileType
from PIL import Image


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
    if pat == "I":
        return (0, 1)
    elif pat == "X":
        return (0, 2)
    elif pat == " ":
        return (255, 1)
    else:
        assert False


def font() -> Image.Image:
    with open("raster.png", "rb") as raster:
        # https://github.com/idispatch/raster-fonts
        raster = Image.open(raster)
        raster = raster.convert("L")
        for y in range(raster.size[1]):
            for x in range(raster.size[0]):
                raster.putpixel((x, y), 255 if raster.getpixel((x, y)) < 250 else 0)
        return raster


FONT = font()


def text(t: str) -> Image.Image:
    x, y = FONT.size[0] // 16, FONT.size[1] // 16
    text_img = Image.new("L", (x * len(t), y))
    for i, ch in enumerate(t):
        oy = ord(ch) // 16
        ox = ord(ch) % 16
        text_img.paste(
            FONT.crop((ox * x, oy * y, (ox + 1) * x, (oy + 1) * y)), (x * i, 0)
        )
    return text_img


BAR_HEIGHT = 60
BAR_LEADIN = 4
TEXT_HEIGHT = 10
TEXT_PADDING = 3

if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("code", type=str)
    ap.add_argument("dest", type=FileType("wb"))
    args = ap.parse_args()

    pattern = " ".join(" ".join(code39(ch)) for ch in "*" + args.code + "*").replace(
        "   ", "  "
    )
    bars = tuple(bar(p) for p in pattern)
    length = sum(b[1] for b in bars)
    size = (
        BAR_LEADIN + length + BAR_LEADIN,
        BAR_HEIGHT + TEXT_PADDING + TEXT_HEIGHT + TEXT_PADDING,
    )
    img = Image.new(
        "L",
        size,
        255,
    )
    x = BAR_LEADIN
    for color, length in bars:
        for i in range(length):
            for y in range(0, BAR_HEIGHT):
                img.putpixel((x, y), color)
            x += 1
    text_img = text(args.code)
    img.paste(
        text_img, ((size[0] // 2) - (text_img.size[0] // 2), BAR_HEIGHT + TEXT_PADDING)
    )
    img.save(args.dest)
