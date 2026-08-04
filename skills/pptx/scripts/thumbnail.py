"""Create thumbnail grids from PowerPoint presentation slides.

Creates a grid layout of slide thumbnails for quick visual analysis.
Labels each thumbnail with its XML filename (e.g., slide1.xml).
Hidden slides are shown with a placeholder pattern.

Usage:
    python thumbnail.py input.pptx [output_prefix] [--cols N]

Examples:
    python thumbnail.py presentation.pptx
    # Creates: thumbnails.jpg

    python thumbnail.py template.pptx grid --cols 4
    # Creates: grid.jpg (or grid-1.jpg, grid-2.jpg for large decks)
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import defusedxml.minidom
from PIL import Image, ImageDraw, ImageFont

THUMBNAIL_WIDTH = 300
SCREENSHOT_WIDTH = 1280
MAX_COLS = 6
DEFAULT_COLS = 3
JPEG_QUALITY = 95
GRID_PADDING = 20
BORDER_WIDTH = 2
FONT_SIZE_RATIO = 0.10
LABEL_PADDING_RATIO = 0.4


def main():
    parser = argparse.ArgumentParser(
        description="Create thumbnail grids from PowerPoint slides."
    )
    parser.add_argument("input", help="Input PowerPoint file (.pptx)")
    parser.add_argument(
        "output_prefix",
        nargs="?",
        default="thumbnails",
        help="Output prefix for image files (default: thumbnails)",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=DEFAULT_COLS,
        help=f"Number of columns (default: {DEFAULT_COLS}, max: {MAX_COLS})",
    )

    args = parser.parse_args()

    cols = min(args.cols, MAX_COLS)
    if args.cols > MAX_COLS:
        print(f"Warning: Columns limited to {MAX_COLS}")

    input_path = Path(args.input)
    if not input_path.exists() or input_path.suffix.lower() != ".pptx":
        print(f"Error: Invalid PowerPoint file: {args.input}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(f"{args.output_prefix}.jpg")

    if shutil.which("officecli") is None:
        print(
            "Error: officecli not found. Install it with:\n"
            "  curl -fsSL https://d.officecli.ai/install.sh | bash\n"
            "  (Windows PowerShell: irm https://d.officecli.ai/install.ps1 | iex)",
            file=sys.stderr,
        )
        sys.exit(1)

    # CRITICAL: flush first. officecli keeps edited decks in a resident process,
    # and get_slide_info() reads the .pptx ZIP straight off disk - without this
    # a deck just built with `officecli add` reports "No slides found".
    subprocess.run(
        ["officecli", "save", str(input_path.absolute())],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    try:
        slide_info = get_slide_info(input_path)

        visible_count = sum(1 for s in slide_info if not s["hidden"])

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            visible_images = convert_to_images(input_path, temp_path, visible_count)

            if not visible_images and not any(s["hidden"] for s in slide_info):
                print("Error: No slides found", file=sys.stderr)
                sys.exit(1)

            slides = build_slide_list(slide_info, visible_images, temp_path)

            grid_files = create_grids(slides, cols, THUMBNAIL_WIDTH, output_path)

            print(f"Created {len(grid_files)} grid(s):")
            for grid_file in grid_files:
                print(f"  {grid_file}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def get_slide_info(pptx_path: Path) -> list[dict]:
    with zipfile.ZipFile(pptx_path, "r") as zf:
        rels_content = zf.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
        rels_dom = defusedxml.minidom.parseString(rels_content)

        rid_to_slide = {}
        for rel in rels_dom.getElementsByTagName("Relationship"):
            rid = rel.getAttribute("Id")
            target = rel.getAttribute("Target")
            rel_type = rel.getAttribute("Type")
            # Match the slide relationship type exactly - "slide" as a substring
            # also matches slideMaster and slideLayout.
            if not rel_type.endswith("/slide"):
                continue
            # Target may be relative to ppt/ ("slides/slide1.xml") OR an
            # absolute part name ("/ppt/slides/slide1.xml"). Both are valid OPC;
            # officecli writes the absolute form, PowerPoint writes the relative
            # one. Keying on the basename handles both.
            normalized = target.replace("\\", "/").rstrip("/")
            if "/slides/" not in f"/{normalized.lstrip('/')}" and not normalized.startswith("slides/"):
                continue
            rid_to_slide[rid] = normalized.rsplit("/", 1)[-1]

        pres_content = zf.read("ppt/presentation.xml").decode("utf-8")
        pres_dom = defusedxml.minidom.parseString(pres_content)

        slides = []
        for sld_id in pres_dom.getElementsByTagName("p:sldId"):
            rid = sld_id.getAttribute("r:id")
            if rid not in rid_to_slide:
                continue
            name = rid_to_slide[rid]
            # A hidden slide is `show="0"`. Per the OOXML spec that attribute
            # lives on the SLIDE's own <p:sld> root (what officecli and
            # PowerPoint write); some writers also mirror it onto <p:sldId>.
            # Check both, or hidden slides are silently rendered as visible and
            # every later slide gets the wrong label.
            hidden = sld_id.getAttribute("show") == "0"
            if not hidden:
                hidden = _slide_marked_hidden(zf, name)
            slides.append({"name": name, "hidden": hidden})

        return slides


def _slide_marked_hidden(zf: zipfile.ZipFile, slide_name: str) -> bool:
    try:
        slide_xml = zf.read(f"ppt/slides/{slide_name}").decode("utf-8")
    except KeyError:
        return False

    dom = defusedxml.minidom.parseString(slide_xml)
    roots = dom.getElementsByTagName("p:sld") or dom.getElementsByTagName("sld")
    if not roots:
        return False
    return roots[0].getAttribute("show") == "0"


def build_slide_list(
    slide_info: list[dict],
    visible_images: list[Path],
    temp_dir: Path,
) -> list[tuple[Path, str]]:
    if visible_images:
        with Image.open(visible_images[0]) as img:
            placeholder_size = img.size
    else:
        placeholder_size = (1920, 1080)

    slides = []
    visible_idx = 0

    for info in slide_info:
        if info["hidden"]:
            placeholder_path = temp_dir / f"hidden-{info['name']}.jpg"
            placeholder_img = create_hidden_placeholder(placeholder_size)
            placeholder_img.save(placeholder_path, "JPEG")
            slides.append((placeholder_path, f"{info['name']} (hidden)"))
        else:
            if visible_idx < len(visible_images):
                slides.append((visible_images[visible_idx], info["name"]))
                visible_idx += 1

    return slides


def create_hidden_placeholder(size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, color="#F0F0F0")
    draw = ImageDraw.Draw(img)
    line_width = max(5, min(size) // 100)
    draw.line([(0, 0), size], fill="#CCCCCC", width=line_width)
    draw.line([(size[0], 0), (0, size[1])], fill="#CCCCCC", width=line_width)
    return img


def convert_to_images(pptx_path: Path, temp_dir: Path, visible_count: int) -> list[Path]:
    """Render each VISIBLE slide to its own PNG via officecli.

    officecli's `view ... screenshot` writes exactly ONE image per invocation
    (a --start/--end range is composed into that single file), so a per-slide
    series needs one call per slide. --start/--end index VISIBLE slides only,
    which matches what this function is expected to return.
    """
    if shutil.which("officecli") is None:
        raise RuntimeError(
            "officecli not found. Install it with:\n"
            "  curl -fsSL https://d.officecli.ai/install.sh | bash\n"
            "(Windows: irm https://d.officecli.ai/install.ps1 | iex)"
        )

    images: list[Path] = []
    for index in range(1, visible_count + 1):
        out_path = temp_dir / f"slide-{index:03d}.png"
        result = subprocess.run(
            [
                "officecli",
                "view",
                str(pptx_path),
                "screenshot",
                "--start",
                str(index),
                "--end",
                str(index),
                "--screenshot-width",
                str(SCREENSHOT_WIDTH),
                "-o",
                str(out_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not out_path.exists():
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(
                f"officecli failed to render slide {index}"
                + (f": {detail}" if detail else "")
            )
        images.append(out_path)

    return images


def create_grids(
    slides: list[tuple[Path, str]],
    cols: int,
    width: int,
    output_path: Path,
) -> list[str]:
    max_per_grid = cols * (cols + 1)
    grid_files = []

    for chunk_idx, start_idx in enumerate(range(0, len(slides), max_per_grid)):
        end_idx = min(start_idx + max_per_grid, len(slides))
        chunk_slides = slides[start_idx:end_idx]

        grid = create_grid(chunk_slides, cols, width)

        if len(slides) <= max_per_grid:
            grid_filename = output_path
        else:
            stem = output_path.stem
            suffix = output_path.suffix
            grid_filename = output_path.parent / f"{stem}-{chunk_idx + 1}{suffix}"

        grid_filename.parent.mkdir(parents=True, exist_ok=True)
        grid.save(str(grid_filename), quality=JPEG_QUALITY)
        grid_files.append(str(grid_filename))

    return grid_files


def create_grid(
    slides: list[tuple[Path, str]],
    cols: int,
    width: int,
) -> Image.Image:
    font_size = int(width * FONT_SIZE_RATIO)
    label_padding = int(font_size * LABEL_PADDING_RATIO)

    with Image.open(slides[0][0]) as img:
        aspect = img.height / img.width
    height = int(width * aspect)

    rows = (len(slides) + cols - 1) // cols
    grid_w = cols * width + (cols + 1) * GRID_PADDING
    grid_h = rows * (height + font_size + label_padding * 2) + (rows + 1) * GRID_PADDING

    grid = Image.new("RGB", (grid_w, grid_h), "white")
    draw = ImageDraw.Draw(grid)

    try:
        font = ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()

    for i, (img_path, slide_name) in enumerate(slides):
        row, col = i // cols, i % cols
        x = col * width + (col + 1) * GRID_PADDING
        y_base = (
            row * (height + font_size + label_padding * 2) + (row + 1) * GRID_PADDING
        )

        label = slide_name
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (width - text_w) // 2, y_base + label_padding),
            label,
            fill="black",
            font=font,
        )

        y_thumbnail = y_base + label_padding + font_size + label_padding

        with Image.open(img_path) as img:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            w, h = img.size
            tx = x + (width - w) // 2
            ty = y_thumbnail + (height - h) // 2
            grid.paste(img, (tx, ty))

            if BORDER_WIDTH > 0:
                draw.rectangle(
                    [
                        (tx - BORDER_WIDTH, ty - BORDER_WIDTH),
                        (tx + w + BORDER_WIDTH - 1, ty + h + BORDER_WIDTH - 1),
                    ],
                    outline="gray",
                    width=BORDER_WIDTH,
                )

    return grid


if __name__ == "__main__":
    main()
