from PIL import Image

with open("raster.png", "rb") as raster:
    raster = Image.open(raster)
    raster = raster.convert("L")
    for y in range(raster.size[1]):
        for x in range(raster.size[0]):
            raster.putpixel((x, y), 255 if raster.getpixel((x, y)) < 250 else 0)
    w, h = raster.size[0] // 16, raster.size[1] // 16
    print("{")
    for char in "EF0123456789":
        oy = ord(char) // 16
        ox = ord(char) % 16
        l = []
        for i in range(h):
            b = 0
            for j in range(w):
                b |= (0 if raster.getpixel((ox * w + j, oy * h + i)) == 0 else 1) << j
            l.append(b)
        print(repr(char), ":", repr(l[1:-1]), ",")
    print("}")
