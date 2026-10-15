#!/usr/bin/env python3
"""clean.py - Drop unreferenced parts from an unpacked PPTX directory.

Given a directory produced by ``office/unpack.py``, this walks the OPC
relationship graph outward from the package root (``_rels/.rels``) and
``ppt/presentation.xml`` and then deletes every part the graph never reaches:

  - slides present on disk but no longer listed in ``<p:sldIdLst>``,
  - the notes slides, media, embeddings, charts, diagrams, drawings and ink
    parts that only those orphan slides referenced,
  - theme parts no surviving master or notes-master points at,
  - a stray ``[trash]`` directory if one is present.

Whenever a part is removed its ``_rels`` file goes with it, any relationship
that pointed at it is pruned from the surviving ``.rels`` files, and its
``<Override>`` is dropped from ``[Content_Types].xml`` - so the package stays
internally consistent and re-packs cleanly.

Conservative by design: a part is deleted only when NOTHING in the reachable
graph references it. Slides are the single special case - a slide counts as
referenced only while ``presentation.xml``'s ``<p:sldIdLst>`` still lists the
``r:id`` that targets it, which is exactly how a slide the user dropped from the
list becomes an orphan this tool can collect.

Usage:
    python clean.py <unpacked_dir>
"""
import argparse
import posixpath
import shutil
import sys
from pathlib import Path

from lxml import etree

# OPC / OOXML namespaces we touch directly (Clark notation: {uri}local).
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# The bare suffix of the relationship Type that means "this target is a slide".
# We must match it exactly: "slideLayout" and "slideMaster" also end in "slide".
SLIDE_REL_LOCAL = "slide"

PRESENTATION_PART = "ppt/presentation.xml"


def _parse(path: Path):
    """Parse an XML part, collapsing existing indentation so we can re-pretty."""
    parser = etree.XMLParser(remove_blank_text=True, resolve_entities=False)
    return etree.parse(str(path), parser)


def _write(tree, path: Path) -> None:
    """Write a part back using the same conventions as office/pack.py."""
    tree.write(str(path), pretty_print=True, xml_declaration=True,
               encoding="UTF-8", standalone=True)


def _rels_path_for_part(part: str) -> str:
    """The .rels path that carries the relationships owned by ``part``.

    ``ppt/presentation.xml`` -> ``ppt/_rels/presentation.xml.rels``; the empty
    string (the package itself) -> ``_rels/.rels``.
    """
    directory, name = posixpath.split(part)
    if directory:
        return posixpath.join(directory, "_rels", name + ".rels")
    return posixpath.join("_rels", name + ".rels")


def _part_for_rels(rels_rel: str) -> str:
    """Inverse of :func:`_rels_path_for_part`: the part a .rels file belongs to.

    ``ppt/slides/_rels/slide1.xml.rels`` -> ``ppt/slides/slide1.xml``;
    ``_rels/.rels`` -> ``""`` (the package root, which always survives).
    """
    directory, name = posixpath.split(rels_rel)          # ".../ _rels", "x.rels"
    owner_name = name[:-len(".rels")]                     # strip ".rels"
    parent = posixpath.dirname(directory)                 # drop the "_rels" leaf
    return posixpath.join(parent, owner_name) if parent else owner_name


def _resolve_target(part: str, target: str) -> str:
    """Resolve a relationship Target (relative to the owning part) to a package
    path. A leading '/' means it is already relative to the package root."""
    if target.startswith("/"):
        return posixpath.normpath(target.lstrip("/"))
    base = posixpath.dirname(part)
    return posixpath.normpath(posixpath.join(base, target))


def _read_relationships(root: Path, rels_rel: str):
    """Yield (rId, Type, resolved_internal_target_or_None, is_external) tuples."""
    rels_file = root / rels_rel
    if not rels_file.exists():
        return
    for rel in _parse(rels_file).getroot():
        if etree.QName(rel).localname != "Relationship":
            continue
        rid = rel.get("Id")
        rtype = rel.get("Type") or ""
        target = rel.get("Target") or ""
        external = (rel.get("TargetMode") == "External")
        yield rid, rtype, (None if external else _resolve_target(_part_for_rels(rels_rel), target)), external


def _slide_rids_in_list(root: Path) -> set[str]:
    """The r:id of every <p:sldId> still present in <p:sldIdLst>."""
    pres = root / PRESENTATION_PART
    rids: set[str] = set()
    if not pres.exists():
        return rids
    for sld_id in _parse(pres).getroot().iter(f"{{{P_NS}}}sldId"):
        rid = sld_id.get(f"{{{R_NS}}}id")
        if rid:
            rids.add(rid)
    return rids


def _reachable_parts(root: Path, slide_rids: set[str]) -> set[str]:
    """Breadth-first walk of the relationship graph from the package root.

    At ``presentation.xml`` we follow a *slide* relationship only when its r:id
    is still listed in <p:sldIdLst>; every other relationship is followed
    normally. Everything the walk lands on is a live part.
    """
    reachable: set[str] = set()
    seen_rels_owners: set[str] = set()
    # Seed with the package root and the presentation part explicitly, so
    # docProps/* (reached only from _rels/.rels) are never mistaken for orphans.
    queue = ["", PRESENTATION_PART]
    reachable.add(PRESENTATION_PART)
    while queue:
        part = queue.pop()
        if part in seen_rels_owners:
            continue
        seen_rels_owners.add(part)
        rels_rel = _rels_path_for_part(part)
        for rid, rtype, target, external in _read_relationships(root, rels_rel):
            if external or target is None:
                continue
            # Gate slide relationships on <p:sldIdLst> membership.
            if part == PRESENTATION_PART and rtype.rsplit("/", 1)[-1] == SLIDE_REL_LOCAL:
                if rid not in slide_rids:
                    continue
            if target not in reachable:
                reachable.add(target)
            queue.append(target)
    return reachable


def _all_files(root: Path) -> list[str]:
    """Every file in the tree as a posix path relative to ``root``."""
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def _prune_dangling_relationships(root: Path, deleted: set[str]) -> int:
    """Drop <Relationship> entries whose internal target we just removed."""
    pruned = 0
    for rels_file in list(root.rglob("*.rels")):
        if not rels_file.exists():
            continue
        rels_rel = rels_file.relative_to(root).as_posix()
        tree = _parse(rels_file)
        root_el = tree.getroot()
        changed = False
        for rel in list(root_el):
            if etree.QName(rel).localname != "Relationship":
                continue
            if rel.get("TargetMode") == "External":
                continue
            target = _resolve_target(_part_for_rels(rels_rel), rel.get("Target") or "")
            if target in deleted:
                root_el.remove(rel)
                pruned += 1
                changed = True
        if changed:
            _write(tree, rels_file)
    return pruned


def _delete_orphan_rels(root: Path) -> list[str]:
    """Remove any .rels file whose owning part no longer exists on disk."""
    removed = []
    for rels_file in list(root.rglob("*.rels")):
        rels_rel = rels_file.relative_to(root).as_posix()
        owner = _part_for_rels(rels_rel)
        if owner == "":            # _rels/.rels belongs to the package - keep it
            continue
        if not (root / owner).exists():
            rels_file.unlink()
            removed.append(rels_rel)
    return removed


def _prune_content_types(root: Path, deleted: set[str]) -> int:
    """Remove <Override> entries in [Content_Types].xml for deleted parts."""
    ct_file = root / "[Content_Types].xml"
    if not ct_file.exists():
        return 0
    tree = _parse(ct_file)
    root_el = tree.getroot()
    removed = 0
    for override in list(root_el):
        if etree.QName(override).localname != "Override":
            continue
        partname = (override.get("PartName") or "").lstrip("/")
        if partname in deleted:
            root_el.remove(override)
            removed += 1
    if removed:
        _write(tree, ct_file)
    return removed


def _remove_empty_dirs(root: Path) -> None:
    """Bottom-up sweep that removes directories left empty by the deletions."""
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()),
                            key=lambda p: len(p.parts), reverse=True):
        try:
            next(directory.iterdir())
        except StopIteration:
            directory.rmdir()


def clean(unpacked_dir: str) -> int:
    root = Path(unpacked_dir)
    if not root.is_dir():
        print(f"Error: {unpacked_dir} is not a directory", file=sys.stderr)
        return 1
    if not (root / PRESENTATION_PART).exists():
        print(f"Error: {unpacked_dir} has no {PRESENTATION_PART} - not an unpacked PPTX",
              file=sys.stderr)
        return 1

    slide_rids = _slide_rids_in_list(root)
    reachable = _reachable_parts(root, slide_rids)

    deleted: set[str] = set()
    removed_parts: list[str] = []

    # 1) A [trash] directory (unpack leaves nothing there, but hand-edits and
    #    other tools sometimes do) is removed wholesale.
    trash = root / "[trash]"
    if trash.exists():
        for f in sorted(trash.rglob("*")):
            if f.is_file():
                rel = f.relative_to(root).as_posix()
                deleted.add(rel)
                removed_parts.append(rel)
                print(f"removed [trash] part: {rel}")
        shutil.rmtree(trash)

    # 2) Content parts (everything that is neither the content-type map nor a
    #    .rels file) that the graph never reached.
    content_parts = [
        f for f in _all_files(root)
        if f != "[Content_Types].xml" and not f.endswith(".rels")
        and not f.startswith("[trash]/")
    ]
    for part in content_parts:
        if part not in reachable:
            (root / part).unlink()
            deleted.add(part)
            removed_parts.append(part)
            print(f"removed unreferenced part: {part}")

    # 3) Keep the package consistent: prune relationships to the parts we cut,
    #    delete now-orphaned .rels files, and drop their content-type overrides.
    pruned_rels = _prune_dangling_relationships(root, deleted)
    orphan_rels = _delete_orphan_rels(root)
    for rels_rel in orphan_rels:
        print(f"removed orphaned rels: {rels_rel}")
    removed_overrides = _prune_content_types(root, deleted)

    _remove_empty_dirs(root)

    print(
        f"\nSummary: removed {len(removed_parts)} part(s), "
        f"{len(orphan_rels)} orphaned rels file(s), "
        f"{removed_overrides} content-type override(s); "
        f"pruned {pruned_rels} dangling relationship(s)."
    )
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Remove unreferenced parts from an unpacked PPTX")
    ap.add_argument("unpacked_dir", help="directory produced by office/unpack.py")
    args = ap.parse_args()
    sys.exit(clean(args.unpacked_dir))
