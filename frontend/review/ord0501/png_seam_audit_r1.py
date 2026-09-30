"""ORD-0501: read the poster PNG back pixel by pixel with the standard library only.

Why not "the layout looks fine in the screenshot": the claim under test is geometric -- does the
picture actually hold one block per day, is there a visible seam between blocks, and is anything cut
off at the bottom. Those are questions about pixels, so they get answered by pixels, not by counting
DOM nodes and hoping the canvas agreed with them.

Decodes the PNG (zlib + the five filters), then reports:
  * rows that are entirely the picture's own background colour ("seam rows");
  * the run of seam rows between the last ink of one day block and the first ink of the next;
  * whether the bottom-most ink row is inside the raster (nothing clipped).
"""
import struct
import sys
import zlib

FILTERS = ("none", "sub", "up", "average", "paeth")


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("not a PNG")
    pos = 8
    idat = bytearray()
    width = height = depth = color = None
    while pos < len(data):
        (size,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + size]
        if kind == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", body[:10])
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + size
    if depth != 8 or color not in (2, 6):
        raise SystemExit("unsupported colour type %s depth %s" % (color, depth))
    channels = 3 if color == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    out = bytearray(height * stride)
    for y in range(height):
        line_start = y * stride
        filt = raw[y * (stride + 1)]
        src = raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
        prev = line_start - stride
        for x in range(len(src)):
            a = out[line_start + x - channels] if x >= channels else 0
            b = out[prev + x] if y > 0 else 0
            c = out[prev + x - channels] if (y > 0 and x >= channels) else 0
            v = src[x]
            if FILTERS[filt] == "sub":
                v = (v + a) & 255
            elif FILTERS[filt] == "up":
                v = (v + b) & 255
            elif FILTERS[filt] == "average":
                v = (v + ((a + b) >> 1)) & 255
            elif FILTERS[filt] == "paeth":
                v = (v + paeth(a, b, c)) & 255
            out[line_start + x] = v
    return width, height, channels, out


def analyse(path):
    width, height, channels, px = decode(path)
    # The picture's own background is its top-left pixel; every row is judged against it.
    bg = tuple(px[:channels][:3])

    def row_is_background(y):
        base = y * width * channels
        for x in range(0, width, 3):  # sampled every third column: a seam is a whole row, not a dot
            i = base + x * channels
            if abs(px[i] - bg[0]) > 6 or abs(px[i + 1] - bg[1]) > 6 or abs(px[i + 2] - bg[2]) > 6:
                return False
        return True

    ink_rows = [y for y in range(height) if not row_is_background(y)]
    if not ink_rows:
        return {"file": path, "blank": True}

    # Runs of background rows inside the inked span are the seams between blocks.
    seams = []
    y = ink_rows[0] + 1
    run_start = None
    while y < ink_rows[-1]:
        if row_is_background(y):
            if run_start is None:
                run_start = y
        elif run_start is not None:
            seams.append((run_start, y - 1, y - run_start))
            run_start = None
        y += 1
    if run_start is not None:
        seams.append((run_start, ink_rows[-1], ink_rows[-1] - run_start + 1))

    bg_mean = (bg[0] + bg[1] + bg[2]) / 3.0

    def row_darker_than_background(y):
        """A hairline is the one row that is DARKER than the page background across the picture's
        width; a card's white fill is lighter, and text is dark but only where glyphs are. Counting
        rows that are darker over most of the width therefore counts card edges and drawn seams and
        nothing else."""
        base = y * width * channels
        dark = 0
        for x in range(width):
            i = base + x * channels
            if (px[i] + px[i + 1] + px[i + 2]) / 3.0 < bg_mean - 8:
                dark += 1
        return dark / float(width)

    """A card edge and a drawn day divider are both near-full-width hairlines, so the count of them
    is what separates "two cards with a gap" from "two cards with a gap AND a drawn seam": a block
    contributes its top and bottom edge, and every break between two blocks contributes one more.
    Stubbing the stroke away therefore changes the number, which is what the counterexample needs."""
    hairline_rows = [y for y in range(height) if row_darker_than_background(y) >= 0.8]
    groups = []
    for y in hairline_rows:
        if groups and y - groups[-1][-1] <= 2:
            groups[-1].append(y)
        else:
            groups.append([y])

    return {
        "file": path,
        "hairline_groups": len(groups),
        "hairline_group_rows": [g[0] for g in groups],
        "width": width,
        "height": height,
        "background_rgb": list(bg),
        "first_ink_row": ink_rows[0],
        "last_ink_row": ink_rows[-1],
        "bottom_padding_rows": height - 1 - ink_rows[-1],
        "seam_runs": len(seams),
        "seams_wider_than_8px": sum(1 for _, _, n in seams if n > 8),
        "widest_seam_px": max((n for _, _, n in seams), default=0),
        "seams": [{"from_row": a, "to_row": b, "px": n} for a, b, n in seams if n > 8][:8],
    }


if __name__ == "__main__":
    import json
    for arg in sys.argv[1:]:
        print(json.dumps(analyse(arg), ensure_ascii=False))
