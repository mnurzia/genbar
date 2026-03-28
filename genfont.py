from PIL import Image
from string import ascii_uppercase, digits
from base64 import b85encode
from itertools import batched

with open("raster.png", "rb") as raster:
    raster = Image.open(raster)
    raster = raster.convert("L")
    for y in range(raster.size[1]):
        for x in range(raster.size[0]):
            raster.putpixel((x, y), 255 if raster.getpixel((x, y)) < 250 else 0)
    w, h = raster.size[0] // 16, raster.size[1] // 16
    fontbits = []
    for char in ascii_uppercase + digits:
        oy = ord(char) // 16
        ox = ord(char) % 16
        for i in range(h):
            for j in range(w):
                fontbits.append(
                    (0 if raster.getpixel((ox * w + j, oy * h + i)) == 0 else 1)
                )
    fontbits.reverse()
    fontstr = b85encode(
        int("".join(map(str, fontbits)), 2).to_bytes((len(fontbits) + 7) // 8)
    ).decode()
    print('"""')
    list(print("".join(line)) for line in batched(fontstr, 80))
    print('"""')
