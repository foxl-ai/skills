"""Fuse adjacent tracked-change wrappers of the same kind and author.

A document that was revised in many small edits ends up with long runs of
consecutive <w:ins> (or <w:del>) siblings. Collapsing each such run into a single
wrapper leaves the visible markup unchanged but makes the XML far easier to reason
about.

Rules:
  - only <w:ins> fuses with <w:ins>, and <w:del> with <w:del>,
  - only when the w:author attribute matches (the w:date is ignored),
  - only when the two wrappers are immediate siblings (nothing but the sibling in
    between). The children of the second are appended to the first.
"""
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


AUTHOR = f"{{{W}}}author"


def _fuse(container, tag: str) -> int:
    fused = 0
    prev = None
    for child in list(container):
        if child.tag != _q(tag):
            prev = None
            continue
        if prev is not None and prev.get(AUTHOR) == child.get(AUTHOR) and prev.getnext() is child:
            for grandchild in list(child):
                prev.append(grandchild)
            container.remove(child)
            fused += 1
        else:
            prev = child
    return fused


def simplify_redlines(unpacked_dir: str) -> tuple[int, str]:
    doc = Path(unpacked_dir) / "word" / "document.xml"
    if not doc.exists():
        return 0, f"Error: {doc} not found"

    tree = etree.parse(str(doc))
    root = tree.getroot()

    fused = 0
    for container in list(root.iter(_q("p"))) + list(root.iter(_q("tc"))):
        fused += _fuse(container, "ins")
        fused += _fuse(container, "del")

    tree.write(str(doc), xml_declaration=True, encoding="UTF-8", standalone=True)
    return fused, f"Simplified {fused} tracked change(s)"
