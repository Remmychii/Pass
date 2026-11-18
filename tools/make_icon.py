"""Draw the Pass (パス) icon: a sand phone with a rose arrow going in and a sand arrow coming out,
on a deep plum tile. Same family as ループ Loop (ICON_PLAYBOOK style: flat, muted, soft grain at 64px+).

    python tools/make_icon.py            -> icon.ico + icon.png
    python tools/make_icon.py --sheet X  -> preview sheet at X (256 + small sizes, light and dark strip)
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

S = 2048
TILE, ROSE, SAND = (46, 36, 40), (214, 108, 124), (238, 231, 219)
SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]
GRAIN = 3.5
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def arrow(d, x0, x1, y, h, fill, right=True):
    """Flat arrow between x0 and x1 on row y, shaft thickness h, pointing right or left."""
    head = h * 1.75
    if right:
        base = x1 - head * 1.1
        d.rounded_rectangle((x0, y - h / 2, base + 8, y + h / 2), radius=h * 0.5, fill=fill)
        d.polygon([(base, y - head), (x1, y), (base, y + head)], fill=fill)
    else:
        base = x0 + head * 1.1
        d.rounded_rectangle((base - 8, y - h / 2, x1, y + h / 2), radius=h * 0.5, fill=fill)
        d.polygon([(base, y - head), (x0, y), (base, y + head)], fill=fill)


def phone(d, box, stroke, fill):
    x0, y0, x1, y1 = box
    w = x1 - x0
    d.rounded_rectangle(box, radius=w * 0.22, fill=fill)
    d.rounded_rectangle((x0 + stroke, y0 + stroke, x1 - stroke, y1 - stroke), radius=max(w * 0.22 - stroke, stroke * 0.35), fill=TILE)
    d.rounded_rectangle((x0 + w * 0.36, y1 - stroke * 2.4, x1 - w * 0.36, y1 - stroke * 1.6), radius=stroke * 0.4, fill=fill)


def draw(small=False):
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=450, fill=TILE)
    if small:   # taskbar / title bar: bigger shapes, thicker lines, less margin
        phone(d, (1130, 300, 1760, 1748), 150, SAND)
        arrow(d, 250, 1020, 790, 210, ROSE, right=True)
        arrow(d, 250, 1020, 1260, 210, SAND, right=False)
    else:
        phone(d, (1120, 444, 1620, 1604), 105, SAND)
        arrow(d, 430, 1020, 840, 140, ROSE, right=True)
        arrow(d, 430, 1020, 1208, 140, SAND, right=False)
    return im


def finish(big, size, seed=11):
    im = big.resize((size, size), Image.LANCZOS)
    if size < 64:
        return im
    a = np.array(im).astype(np.float32)
    a[..., :3] += np.random.default_rng(seed + size).normal(0, GRAIN, a[..., :3].shape)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def sizes():
    big, small = draw(), draw(small=True)
    return {s: finish(small if s <= 32 else big, s) for s in SIZES}


def sheet(path):
    z = sizes()
    sh = Image.new('RGB', (660, 330), '#f4f2ee')
    d = ImageDraw.Draw(sh)
    d.rectangle((300, 165, 660, 330), fill='#1d1f24')
    sh.paste(z[256], (24, 37), z[256])
    x = 320
    for s in (48, 32, 24, 16):
        sh.paste(z[s], (x, 60 + (48 - s) // 2), z[s]); sh.paste(z[s], (x, 225 + (48 - s) // 2), z[s]); x += s + 30
    sh.save(path)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--sheet':
        sheet(sys.argv[2])
    else:
        z = sizes()
        z[256].save(os.path.join(HERE, 'icon.png'))
        z[256].save(os.path.join(HERE, 'icon.ico'), sizes=[(s, s) for s in SIZES],
                    append_images=[z[s] for s in SIZES if s != 256])
        print('icon written')
