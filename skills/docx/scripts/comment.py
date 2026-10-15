"""Add a comment (or a threaded reply) to an unpacked DOCX.

Writes into the four Word comment parts, creating any that are missing along with
their relationships and content-type overrides:

  word/comments.xml            the comment body (w:comment)
  word/commentsExtended.xml    threading (w15: paraId -> paraIdParent)
  word/commentsIds.xml         a stable durableId per comment (w16cid)
  word/commentsExtensible.xml  the comment's UTC timestamp (w16cex)

Comment TEXT is passed as plain text - this script escapes it, so write & and
quotes literally, not as XML entities.

After running, anchor the comment in word/document.xml by wrapping the commented
range (the markers are direct children of <w:p>, never inside a <w:r>):

    <w:commentRangeStart w:id="0"/>
    ... the runs being commented on ...
    <w:commentRangeEnd w:id="0"/>
    <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>

Usage:
    python comment.py <unpacked_dir> <comment_id> "<text>" [--parent ID] [--author NAME] [--initials XX]
"""
import argparse
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "w16cid": "http://schemas.microsoft.com/office/word/2016/wordml/cid",
    "w16cex": "http://schemas.microsoft.com/office/word/2018/wordml/cex",
}
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

PARTS = {
    "comments.xml": (
        "w:comments",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
    ),
    "commentsExtended.xml": (
        "w15:commentsEx",
        "http://schemas.microsoft.com/office/2011/relationships/commentsExtended",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml",
    ),
    "commentsIds.xml": (
        "w16cid:commentsIds",
        "http://schemas.microsoft.com/office/2016/09/relationships/commentsIds",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsIds+xml",
    ),
    "commentsExtensible.xml": (
        "w16cex:commentsExtensible",
        "http://schemas.microsoft.com/office/2018/08/relationships/commentsExtensible",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtensible+xml",
    ),
}


def _qn(prefixed: str) -> str:
    prefix, local = prefixed.split(":")
    return f"{{{NS[prefix]}}}{local}"


def _hex_id() -> str:
    return f"{secrets.randbelow(0x7FFFFFFF) + 1:08X}"


def _load_or_create(path: Path, root_prefixed: str):
    if path.exists():
        return etree.parse(str(path)), False
    root = etree.Element(_qn(root_prefixed), nsmap=NS)
    return etree.ElementTree(root), True


def _write(tree, path: Path) -> None:
    tree.write(str(path), xml_declaration=True, encoding="UTF-8", standalone=True)


def _find_parent_para_id(comments_tree, parent_id: int) -> str | None:
    for comment in comments_tree.getroot():
        if comment.get(_qn("w:id")) == str(parent_id):
            para = comment.find(_qn("w:p"))
            if para is not None:
                return para.get(_qn("w14:paraId"))
    return None


def _ensure_rels_and_content_types(unpacked: Path) -> None:
    rels_path = unpacked / "word" / "_rels" / "document.xml.rels"
    if rels_path.exists():
        rels = etree.parse(str(rels_path))
        root = rels.getroot()
        targets = {r.get("Target") for r in root}
        used = {int(r.get("Id")[3:]) for r in root if (r.get("Id") or "").startswith("rId") and r.get("Id")[3:].isdigit()}
        nid = (max(used) + 1) if used else 1
        for name, (_, rel_type, _) in PARTS.items():
            if name not in targets:
                el = etree.SubElement(root, f"{{{REL_NS}}}Relationship")
                el.set("Id", f"rId{nid}")
                el.set("Type", rel_type)
                el.set("Target", name)
                nid += 1
        _write(rels, rels_path)

    ct_path = unpacked / "[Content_Types].xml"
    if ct_path.exists():
        ct = etree.parse(str(ct_path))
        root = ct.getroot()
        present = {o.get("PartName") for o in root if etree.QName(o).localname == "Override"}
        for name, (_, _, content_type) in PARTS.items():
            part_name = f"/word/{name}"
            if part_name not in present:
                el = etree.SubElement(root, f"{{{CT_NS}}}Override")
                el.set("PartName", part_name)
                el.set("ContentType", content_type)
        _write(ct, ct_path)


def add_comment(unpacked_dir: str, comment_id: int, text: str,
                author: str = "Foxl", initials: str = "F",
                parent_id: int | None = None) -> tuple[str, str]:
    word = Path(unpacked_dir) / "word"
    if not word.exists():
        return "", f"Error: {word} not found"

    para_id, durable_id = _hex_id(), _hex_id()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    comments_path = word / "comments.xml"
    first = not comments_path.exists()
    comments, _ = _load_or_create(comments_path, "w:comments")

    comment = etree.SubElement(comments.getroot(), _qn("w:comment"))
    comment.set(_qn("w:id"), str(comment_id))
    comment.set(_qn("w:author"), author)
    comment.set(_qn("w:date"), stamp)
    comment.set(_qn("w:initials"), initials)
    para = etree.SubElement(comment, _qn("w:p"))
    para.set(_qn("w14:paraId"), para_id)
    para.set(_qn("w14:textId"), "77777777")
    run = etree.SubElement(para, _qn("w:r"))
    rpr = etree.SubElement(run, _qn("w:rPr"))
    etree.SubElement(rpr, _qn("w:rStyle")).set(_qn("w:val"), "CommentReference")
    etree.SubElement(run, _qn("w:annotationRef"))
    body = etree.SubElement(para, _qn("w:r"))
    etree.SubElement(body, _qn("w:t")).text = text
    _write(comments, comments_path)

    ext_path = word / "commentsExtended.xml"
    ext, _ = _load_or_create(ext_path, "w15:commentsEx")
    ex = etree.SubElement(ext.getroot(), _qn("w15:commentEx"))
    ex.set(_qn("w15:paraId"), para_id)
    if parent_id is not None:
        parent_para = _find_parent_para_id(comments, parent_id)
        if not parent_para:
            return "", f"Error: parent comment {parent_id} not found"
        ex.set(_qn("w15:paraIdParent"), parent_para)
    ex.set(_qn("w15:done"), "0")
    _write(ext, ext_path)

    ids_path = word / "commentsIds.xml"
    ids, _ = _load_or_create(ids_path, "w16cid:commentsIds")
    cid = etree.SubElement(ids.getroot(), _qn("w16cid:commentId"))
    cid.set(_qn("w16cid:paraId"), para_id)
    cid.set(_qn("w16cid:durableId"), durable_id)
    _write(ids, ids_path)

    cex_path = word / "commentsExtensible.xml"
    cex, _ = _load_or_create(cex_path, "w16cex:commentsExtensible")
    ce = etree.SubElement(cex.getroot(), _qn("w16cex:commentExtensible"))
    ce.set(_qn("w16cex:durableId"), durable_id)
    ce.set(_qn("w16cex:dateUtc"), stamp)
    _write(cex, cex_path)

    if first:
        _ensure_rels_and_content_types(Path(unpacked_dir))

    kind = "reply" if parent_id is not None else "comment"
    return para_id, f"Added {kind} {comment_id} (paraId={para_id})"


def _marker_hint(comment_id: int, parent_id: int | None) -> str:
    if parent_id is None:
        return (f"\nAnchor it in document.xml (markers are children of <w:p>):\n"
                f'  <w:commentRangeStart w:id="{comment_id}"/>\n'
                f"  ... commented runs ...\n"
                f'  <w:commentRangeEnd w:id="{comment_id}"/>\n'
                f'  <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
                f'<w:commentReference w:id="{comment_id}"/></w:r>')
    return (f"\nNest the reply inside parent {parent_id}'s range in document.xml:\n"
            f'  <w:commentRangeStart w:id="{parent_id}"/><w:commentRangeStart w:id="{comment_id}"/>\n'
            f"  ... commented runs ...\n"
            f'  <w:commentRangeEnd w:id="{comment_id}"/><w:commentRangeEnd w:id="{parent_id}"/>\n'
            f'  <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
            f'<w:commentReference w:id="{parent_id}"/></w:r>\n'
            f'  <w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr>'
            f'<w:commentReference w:id="{comment_id}"/></w:r>')


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Add a comment to an unpacked DOCX")
    ap.add_argument("unpacked_dir")
    ap.add_argument("comment_id", type=int)
    ap.add_argument("text")
    ap.add_argument("--parent", type=int, default=None)
    ap.add_argument("--author", default="Foxl")
    ap.add_argument("--initials", default="F")
    args = ap.parse_args()
    _, msg = add_comment(args.unpacked_dir, args.comment_id, args.text,
                         args.author, args.initials, args.parent)
    print(msg)
    if msg.startswith("Error"):
        sys.exit(1)
    print(_marker_hint(args.comment_id, args.parent))
