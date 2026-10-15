#!/usr/bin/env python3
"""add_slide.py - Add a slide to an unpacked PPTX, either by duplicating an
existing slide or by creating a fresh slide from a layout.

    python add_slide.py <unpacked_dir> slide2.xml        # duplicate slide 2
    python add_slide.py <unpacked_dir> slideLayout2.xml  # new slide off layout 2

The new part is written as ``ppt/slides/slide{next}.xml`` where ``next`` is one
past the highest existing slide number. The tool also:

  - writes the slide's ``_rels`` (a clone of the source slide's rels when
    duplicating; a single slideLayout relationship when starting from a layout),
  - adds the ``<Override>`` for the new slide to ``[Content_Types].xml``,
  - adds a slide relationship to ``ppt/_rels/presentation.xml.rels`` with a
    fresh ``rId``.

It deliberately does NOT edit ``<p:sldIdLst>`` in ``presentation.xml``. Instead
it PRINTS the ``<p:sldId>`` element to paste into the list at the position you
want the slide to appear - inserting it is how you choose the slide's order, so
that stays a human decision (this is the documented contract).
"""
import argparse
import posixpath
import re
import sys
from pathlib import Path

from lxml import etree

# Namespaces (Clark notation {uri}local for lxml).
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Relationship Type URIs.
REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
SLIDE_REL_TYPE = f"{REL_BASE}/slide"
LAYOUT_REL_TYPE = f"{REL_BASE}/slideLayout"

# The content type for a slide part.
SLIDE_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"

SLIDE_RE = re.compile(r"^slide(\d+)\.xml$")
LAYOUT_RE = re.compile(r"^slideLayout(\d+)\.xml$")


def _parse(path: Path):
    parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
    return etree.parse(str(path), parser)


def _write(tree, path: Path) -> None:
    tree.write(str(path), pretty_print=True, xml_declaration=True,
               encoding="UTF-8", standalone=True)


def _next_slide_number(slides_dir: Path) -> int:
    """One past the highest slideN.xml already present (1 if there are none)."""
    numbers = [int(m.group(1)) for p in slides_dir.glob("slide*.xml")
               if (m := SLIDE_RE.match(p.name))]
    return max(numbers) + 1 if numbers else 1


def _next_relationship_id(rels_root) -> str:
    """A fresh rIdN not already used in the given <Relationships> element."""
    used = set()
    for rel in rels_root:
        rid = rel.get("Id") or ""
        if rid.startswith("rId") and rid[3:].isdigit():
            used.add(int(rid[3:]))
    return f"rId{(max(used) + 1) if used else 1}"


def _next_slide_id(sld_id_lst) -> int:
    """A fresh <p:sldId> id. PowerPoint ids live in [256, 2^31); we take one
    past the current maximum, or 256 when the list is empty."""
    ids = [int(el.get("id")) for el in sld_id_lst.iter(f"{{{P_NS}}}sldId")
           if (el.get("id") or "").isdigit()]
    return max(ids) + 1 if ids else 256


def _empty_slide_xml() -> "etree._ElementTree":
    """A minimal, schema-valid <p:sld> whose placeholders inherit from a layout
    (an empty shape tree plus the master colour-map override)."""
    nsmap = {"a": A_NS, "r": R_NS, "p": P_NS}
    sld = etree.Element(f"{{{P_NS}}}sld", nsmap=nsmap)
    c_sld = etree.SubElement(sld, f"{{{P_NS}}}cSld")
    sp_tree = etree.SubElement(c_sld, f"{{{P_NS}}}spTree")

    nv_grp = etree.SubElement(sp_tree, f"{{{P_NS}}}nvGrpSpPr")
    c_nv_pr = etree.SubElement(nv_grp, f"{{{P_NS}}}cNvPr")
    c_nv_pr.set("id", "1")
    c_nv_pr.set("name", "")
    etree.SubElement(nv_grp, f"{{{P_NS}}}cNvGrpSpPr")
    etree.SubElement(nv_grp, f"{{{P_NS}}}nvPr")

    grp_pr = etree.SubElement(sp_tree, f"{{{P_NS}}}grpSpPr")
    xfrm = etree.SubElement(grp_pr, f"{{{A_NS}}}xfrm")
    # CT_GroupTransform2D (ECMA-376) fixes this child order: off, ext, chOff, chExt.
    off = etree.SubElement(xfrm, f"{{{A_NS}}}off")
    off.set("x", "0"); off.set("y", "0")
    ext = etree.SubElement(xfrm, f"{{{A_NS}}}ext")
    ext.set("cx", "0"); ext.set("cy", "0")
    ch_off = etree.SubElement(xfrm, f"{{{A_NS}}}chOff")
    ch_off.set("x", "0"); ch_off.set("y", "0")
    ch_ext = etree.SubElement(xfrm, f"{{{A_NS}}}chExt")
    ch_ext.set("cx", "0"); ch_ext.set("cy", "0")

    clr_map_ovr = etree.SubElement(sld, f"{{{P_NS}}}clrMapOvr")
    etree.SubElement(clr_map_ovr, f"{{{A_NS}}}masterClrMapping")
    return etree.ElementTree(sld)


def _rels_root() -> "etree._Element":
    return etree.Element(f"{{{RELS_NS}}}Relationships", nsmap={None: RELS_NS})


def add_slide(unpacked_dir: str, source: str) -> int:
    root = Path(unpacked_dir)
    if not root.is_dir():
        print(f"Error: {unpacked_dir} is not a directory", file=sys.stderr)
        return 1

    slides_dir = root / "ppt" / "slides"
    layouts_dir = root / "ppt" / "slideLayouts"
    pres_rels = root / "ppt" / "_rels" / "presentation.xml.rels"
    content_types = root / "[Content_Types].xml"
    for required in (slides_dir, pres_rels, content_types):
        if not required.exists():
            print(f"Error: missing {required} - not an unpacked PPTX", file=sys.stderr)
            return 1

    source_name = posixpath.basename(source)
    next_n = _next_slide_number(slides_dir)
    new_slide_name = f"slide{next_n}.xml"
    new_slide_path = slides_dir / new_slide_name
    new_rels_path = slides_dir / "_rels" / f"{new_slide_name}.rels"
    new_rels_path.parent.mkdir(parents=True, exist_ok=True)

    if SLIDE_RE.match(source_name):
        # --- Duplicate an existing slide: copy the part and clone its rels. ---
        src_slide = slides_dir / source_name
        if not src_slide.exists():
            print(f"Error: source slide {src_slide} does not exist", file=sys.stderr)
            return 1
        # Re-serialise through lxml so the copy matches the unpack conventions.
        _write(_parse(src_slide), new_slide_path)

        src_rels = slides_dir / "_rels" / f"{source_name}.rels"
        if src_rels.exists():
            _write(_parse(src_rels), new_rels_path)
        else:
            _write(etree.ElementTree(_rels_root()), new_rels_path)
        origin = f"duplicate of {source_name}"

    elif LAYOUT_RE.match(source_name):
        # --- Fresh slide from a layout: empty slide + one layout relationship.-
        src_layout = layouts_dir / source_name
        if not src_layout.exists():
            print(f"Error: source layout {src_layout} does not exist", file=sys.stderr)
            return 1
        _write(_empty_slide_xml(), new_slide_path)

        rels_root_el = _rels_root()
        rel = etree.SubElement(rels_root_el, f"{{{RELS_NS}}}Relationship")
        rel.set("Id", "rId1")
        rel.set("Type", LAYOUT_REL_TYPE)
        rel.set("Target", f"../slideLayouts/{source_name}")
        _write(etree.ElementTree(rels_root_el), new_rels_path)
        origin = f"new slide from {source_name}"

    else:
        print(f"Error: source must be slideN.xml or slideLayoutN.xml, got {source_name}",
              file=sys.stderr)
        return 1

    # --- Register the new part in [Content_Types].xml. ---
    ct_tree = _parse(content_types)
    override = etree.SubElement(ct_tree.getroot(), f"{{{CT_NS}}}Override")
    override.set("PartName", f"/ppt/slides/{new_slide_name}")
    override.set("ContentType", SLIDE_CONTENT_TYPE)
    _write(ct_tree, content_types)

    # --- Add the slide relationship to presentation.xml.rels. ---
    pres_rels_tree = _parse(pres_rels)
    pres_rels_root = pres_rels_tree.getroot()
    new_rid = _next_relationship_id(pres_rels_root)
    rel = etree.SubElement(pres_rels_root, f"{{{RELS_NS}}}Relationship")
    rel.set("Id", new_rid)
    rel.set("Type", SLIDE_REL_TYPE)
    rel.set("Target", f"slides/{new_slide_name}")
    _write(pres_rels_tree, pres_rels)

    # --- Compute a fresh sldId and PRINT the element to paste. ---
    pres = root / "ppt" / "presentation.xml"
    sld_id_lst = _parse(pres).getroot().find(f"{{{P_NS}}}sldIdLst")
    new_id = _next_slide_id(sld_id_lst) if sld_id_lst is not None else 256
    # Slides added by an earlier run whose <p:sldId> was not pasted yet still
    # own the ids printed for them, so skip past every pending slide
    # relationship (the one just added counts as the first).
    listed = set()
    if sld_id_lst is not None:
        listed = {el.get(f"{{{R_NS}}}id") for el in sld_id_lst.iter(f"{{{P_NS}}}sldId")}
    pending = [r for r in pres_rels_root.iter(f"{{{RELS_NS}}}Relationship")
               if r.get("Type") == SLIDE_REL_TYPE and r.get("Id") not in listed]
    new_id += max(len(pending) - 1, 0)

    print(f"Created ppt/slides/{new_slide_name} ({origin})")
    print(f"  rels:          ppt/slides/_rels/{new_slide_name}.rels")
    print(f"  content type:  added <Override> for /ppt/slides/{new_slide_name}")
    print(f"  relationship:  added {new_rid} -> slides/{new_slide_name} in presentation.xml.rels")
    print()
    print("Add this <p:sldId> to <p:sldIdLst> in ppt/presentation.xml, at the "
          "position where you want the slide to appear:")
    print()
    print(f'    <p:sldId id="{new_id}" r:id="{new_rid}"/>')
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Duplicate a slide, or create a new one from a layout, in an unpacked PPTX")
    ap.add_argument("unpacked_dir", help="directory produced by office/unpack.py")
    ap.add_argument("source", help="slideN.xml (duplicate) or slideLayoutN.xml (from layout)")
    args = ap.parse_args()
    sys.exit(add_slide(args.unpacked_dir, args.source))
