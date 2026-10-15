"""Coalesce adjacent runs that share identical formatting in word/document.xml.

Heavily-authored Word documents fragment their text across many <w:r> runs that
carry the same <w:rPr>. That fragmentation makes the unpacked XML hard to edit by
hand, so this pass rejoins them:

  - remove <w:proofErr> markers (spell/grammar hints that split runs),
  - drop w:rsid* attributes from runs (revision bookkeeping, no visual effect),
  - merge neighbouring <w:r> whose <w:rPr> serialises identically, then fold the
    text of their <w:t> children together, adding xml:space="preserve" when the
    joined text starts or ends with a space.

Runs are merged wherever they live: straight inside a paragraph, or wrapped in a
tracked-change element (<w:ins>/<w:del>).
"""
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _q(tag: str) -> str:
    return f"{{{W}}}{tag}"


def _local(tag) -> str:
    return etree.QName(tag).localname if isinstance(tag, str) and tag.startswith("{") else str(tag)


def _rpr_signature(run) -> str | None:
    rpr = run.find(_q("rPr"))
    if rpr is None:
        return None
    return etree.tostring(rpr, encoding="unicode")


def _text_children(run):
    return [c for c in run if c.tag == _q("t")]


def _merge_pair(target, source) -> None:
    # Move everything except the formatting block from source into target.
    for child in list(source):
        if child.tag != _q("rPr"):
            target.append(child)


def _coalesce_text(run) -> None:
    ts = _text_children(run)
    for i in range(len(ts) - 1, 0, -1):
        prev, curr = ts[i - 1], ts[i]
        # Only fuse if nothing but the two <w:t> sit next to each other.
        if prev.getnext() is not curr:
            continue
        joined = (prev.text or "") + (curr.text or "")
        prev.text = joined
        if joined[:1] == " " or joined[-1:] == " ":
            prev.set(XML_SPACE, "preserve")
        elif XML_SPACE in prev.attrib:
            del prev.attrib[XML_SPACE]
        run.remove(curr)


def merge_runs(unpacked_dir: str) -> tuple[int, str]:
    doc = Path(unpacked_dir) / "word" / "document.xml"
    if not doc.exists():
        return 0, f"Error: {doc} not found"

    tree = etree.parse(str(doc))
    root = tree.getroot()

    for pe in list(root.iter(_q("proofErr"))):
        pe.getparent().remove(pe)

    for run in root.iter(_q("r")):
        for name in list(run.attrib):
            if _local(name).lower().startswith("rsid"):
                del run.attrib[name]

    containers = {run.getparent() for run in root.iter(_q("r")) if run.getparent() is not None}

    merged = 0
    for container in containers:
        run = None
        for child in list(container):
            if child.tag != _q("r"):
                run = None
                continue
            if run is not None and _rpr_signature(run) == _rpr_signature(child):
                _merge_pair(run, child)
                container.remove(child)
                merged += 1
            else:
                run = child
        for child in container:
            if child.tag == _q("r"):
                _coalesce_text(child)

    tree.write(str(doc), xml_declaration=True, encoding="UTF-8", standalone=True)
    return merged, f"Merged {merged} run(s)"
