# genbar

Problem: Gym membership cards are too chunky and make my keychain too bulky.

This is a Python script that generates smaller printable barcodes for keychain tags.

![Example showing original large memebrship card above 3x smaller labelled tag](https://i.imgur.com/EjY2SXQ.jpeg)

## Usage

Designed for use with [ptouch-print](https://git.familie-radermacher.ch/linux/ptouch-print.git/) on a Brother PT-2430PC. Uses only the python stdlib.

```
python genbar.py FK2169670 x.png && ptouch-print -i x.png
```
