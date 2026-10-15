#!/usr/bin/env python3
"""thumbnail.py - Contact sheet of every slide in a deck, labeled by XML part.

    python thumbnail.py input.pptx [output_prefix] [--cols N]

Each tile is a ~300px-wide thumbnail of one slide, captioned with the slide's
XML filename (``slide1.xml`` ...) so a rendered layout can be mapped straight
back to the part you would edit. Hidden slides (``show="0"`` on ``<p:sld>``) are
not rasterized; they get a distinct crosshatched placeholder tile instead.

Rendering is delegated to ``officecli view <file> screenshot`` (which needs a
headless browser on the machine); the tiles are then composed into a JPEG with
Pillow. A deck of up to 12 slides yields one ``<prefix>.jpg``; a larger deck is
split across ``<prefix>-1.jpg``, ``<prefix>-2.jpg`` ... The default prefix is
``thumbnails`` -> ``thumbnails.jpg``.

If ``officecli`` cannot rasterize a slide the script FAILS with a message naming
what is missing, rather than emitting a blank sheet.
"""
import argparse
import io
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

THUMB_W = 300          # target thumbnail width in px
LABEL_H = 24           # caption strip height in px
PAD = 12               # gap around and between tiles
MAX_COLS = 6           # hard cap on columns
PER_GRID = 12          # tiles per output image before splitting

# EMU dimensions of a default 4:3 slide, used only if <p:sldSz> is absent.
DEFAULT_CX, DEFAULT_CY = 9144000, 6858000

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _load_font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _read_zip_text(zf: zipfile.ZipFile, name: str) -> bytes | None:
    try:
        return zf.read(name)
    except KeyError:
        return None


def _slide_order(pptx: Path):
    """Return (ordered_slide_filenames, hidden_flags, slide_aspect).

    Slides are ordered exactly as <p:sldIdLst> lists them (which is the order
    officecli renders), mapped through presentation.xml.rels to their part
    filenames, with each slide's show="0" state and the deck aspect ratio.
    """
    with zipfile.ZipFile(pptx) as zf:
        pres = _read_zip_text(zf, "ppt/presentation.xml")
        if pres is None:
            raise ValueError("ppt/presentation.xml missing - not a valid PPTX")
        pres_root = etree.fromstring(pres)

        rels = _read_zip_text(zf, "ppt/_rels/presentation.xml.rels")
        rid_to_target: dict[str, str] = {}
        if rels is not None:
            for rel in etree.fromstring(rels):
                rid_to_target[rel.get("Id")] = rel.get("Target") or ""

        # Deck aspect ratio from <p:sldSz>.
        cx, cy = DEFAULT_CX, DEFAULT_CY
        sld_sz = pres_root.find(f"{{{P_NS}}}sldSz")
        if sld_sz is not None:
            cx = int(sld_sz.get("cx") or DEFAULT_CX)
            cy = int(sld_sz.get("cy") or DEFAULT_CY)
        aspect = cy / cx

        filenames: list[str] = []
        hidden: list[bool] = []
        sld_id_lst = pres_root.find(f"{{{P_NS}}}sldIdLst")
        if sld_id_lst is not None:
            for sld_id in sld_id_lst.iter(f"{{{P_NS}}}sldId"):
                rid = sld_id.get(f"{{{R_NS}}}id")
                target = rid_to_target.get(rid, "")
                # Target is relative to ppt/, e.g. "slides/slide3.xml".
                name = target.rsplit("/", 1)[-1] if target else f"(rId {rid})"
                part = "ppt/" + target.lstrip("/") if target else None
                is_hidden = False
                if part:
                    body = _read_zip_text(zf, part)
                    if body is not None:
                        is_hidden = (etree.fromstring(body).get("show") == "0")
                filenames.append(name)
                hidden.append(is_hidden)
    return filenames, hidden, aspect


def _render_slide(pptx: Path, index_1based: int, out_png: Path) -> None:
    """Rasterize one slide (1-based, presentation order) with officecli.

    Raises RuntimeError with an actionable message if the render did not
    produce a real image - we never want to paste a blank tile.
    """
    proc = subprocess.run(
        ["officecli", "view", str(pptx), "screenshot",
         "--start", str(index_1based), "--end", str(index_1based),
         "-o", str(out_png)],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0 or not out_png.exists() or out_png.stat().st_size < 100:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(
            f"officecli could not rasterize slide {index_1based}. "
            f"PNG capture needs a headless browser (Playwright / Chrome / Edge / "
            f"Firefox) on this machine. officecli said: {detail or '(no output)'}"
        )
    try:
        with Image.open(out_png) as im:
            im.load()
    except Exception as exc:  # noqa: BLE001 - report whatever Pillow saw
        raise RuntimeError(
            f"officecli wrote an unreadable image for slide {index_1based}: {exc}"
        ) from exc


def _resize_to_width(im: Image.Image, width: int, height: int) -> Image.Image:
    return im.convert("RGB").resize((width, height), Image.LANCZOS)


def _placeholder_tile(width: int, height: int) -> Image.Image:
    """A crosshatched grey tile that clearly reads as 'not rendered / hidden'."""
    tile = Image.new("RGB", (width, height), (221, 221, 221))
    draw = ImageDraw.Draw(tile)
    step = 16
    for x in range(-height, width, step):
        draw.line([(x, 0), (x + height, height)], fill=(170, 170, 170), width=1)
    draw.rectangle([0, 0, width - 1, height - 1], outline=(136, 136, 136), width=2)
    font = _load_font(20)
    text = "HIDDEN"
    tb = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (tb[2] - tb[0])) / 2, (height - (tb[3] - tb[1])) / 2 - tb[1]),
              text, fill=(90, 90, 90), font=font)
    return tile


def _tile(image: Image.Image, label: str, width: int, height: int) -> Image.Image:
    """Thumbnail image plus a caption strip underneath."""
    canvas = Image.new("RGB", (width, height + LABEL_H), (255, 255, 255))
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(13)
    tb = draw.textbbox((0, 0), label, font=font)
    tw = tb[2] - tb[0]
    draw.text(((width - tw) / 2, height + (LABEL_H - (tb[3] - tb[1])) / 2 - tb[1]),
              label, fill=(20, 20, 20), font=font)
    return canvas


def _compose_grid(tiles: list[Image.Image], cols: int) -> Image.Image:
    tile_w = tiles[0].width
    tile_h = tiles[0].height
    rows = (len(tiles) + cols - 1) // cols
    grid_w = cols * tile_w + (cols + 1) * PAD
    grid_h = rows * tile_h + (rows + 1) * PAD
    grid = Image.new("RGB", (grid_w, grid_h), (245, 245, 245))
    for idx, tile in enumerate(tiles):
        r, c = divmod(idx, cols)
        x = PAD + c * (tile_w + PAD)
        y = PAD + r * (tile_h + PAD)
        grid.paste(tile, (x, y))
    return grid


def build_thumbnails(pptx_path: str, prefix: str, cols: int) -> int:
    pptx = Path(pptx_path)
    if not pptx.exists():
        print(f"Error: {pptx_path} does not exist", file=sys.stderr)
        return 1
    if pptx.suffix.lower() != ".pptx":
        print(f"Error: {pptx_path} must be a .pptx file", file=sys.stderr)
        return 1
    if shutil.which("officecli") is None:
        print("Error: officecli is not on PATH - it is required to rasterize slides. "
              "Install it: curl -fsSL https://d.officecli.ai/install.sh | bash",
              file=sys.stderr)
        return 1

    cols = max(1, min(cols, MAX_COLS))
    filenames, hidden, aspect = _slide_order(pptx)
    if not filenames:
        print(f"Error: {pptx_path} has no slides to thumbnail", file=sys.stderr)
        return 1

    thumb_h = max(1, round(THUMB_W * aspect))
    tiles: list[Image.Image] = []
    tmp = Path(tempfile.mkdtemp(prefix="pptx-thumb-"))
    try:
        for i, (name, is_hidden) in enumerate(zip(filenames, hidden), start=1):
            if is_hidden:
                thumb = _placeholder_tile(THUMB_W, thumb_h)
                label = f"{name} (hidden)"
            else:
                png = tmp / f"slide-{i}.png"
                _render_slide(pptx, i, png)      # raises on failure - no blank tiles
                with Image.open(png) as im:
                    thumb = _resize_to_width(im, THUMB_W, thumb_h)
                label = name
            tiles.append(_tile(thumb, label, THUMB_W, thumb_h))
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        shutil.rmtree(tmp, ignore_errors=True)
        return 1
    finally:
        pass

    # Split into pages of at most PER_GRID tiles.
    pages = [tiles[i:i + PER_GRID] for i in range(0, len(tiles), PER_GRID)]
    outputs: list[str] = []
    for page_no, page_tiles in enumerate(pages, start=1):
        grid = _compose_grid(page_tiles, cols)
        if len(pages) == 1:
            out_name = f"{prefix}.jpg"
        else:
            out_name = f"{prefix}-{page_no}.jpg"
        grid.save(out_name, "JPEG", quality=85)
        outputs.append(out_name)

    shutil.rmtree(tmp, ignore_errors=True)

    n_hidden = sum(hidden)
    print(f"Wrote {len(outputs)} thumbnail sheet(s) for {len(filenames)} slide(s) "
          f"({n_hidden} hidden) at {cols} column(s):")
    for out_name in outputs:
        size = Path(out_name).stat().st_size
        print(f"  {out_name} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Build a labeled thumbnail grid of a deck's slides")
    ap.add_argument("input", help="input .pptx")
    ap.add_argument("output_prefix", nargs="?", default="thumbnails",
                    help="output filename prefix (default: thumbnails)")
    ap.add_argument("--cols", type=int, default=3, help="columns per grid (default 3, max 6)")
    args = ap.parse_args()
    sys.exit(build_thumbnails(args.input, args.output_prefix, args.cols))
