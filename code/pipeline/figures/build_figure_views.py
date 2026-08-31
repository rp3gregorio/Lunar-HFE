#!/usr/bin/env python3
"""Rebuild figures/_by_document/ — a symlink view of which figure each
document uses.

The one physical figure home is the top-level ``figures/`` folder; generators
write only there and every document reaches it through its own ``figures``
symlink. Moving figures into per-document folders would break both halves, so
this builds a *view* instead: one folder per document, filled with relative
symlinks back into ``figures/``.

Run after adding or removing a figure::

    .venv/bin/python code/pipeline/figures/build_figure_views.py
"""
from __future__ import annotations

import collections
import os
import re
import shutil
from pathlib import Path

from lunar._bootstrap import find_repo_root

ROOT = find_repo_root()                    # code/
FIG = ROOT.parent / "figures"
DOCS_ROOT = Path(os.environ.get("LUNAR_DOCS", ROOT.parent.parent / "Others"))

DOCUMENTS = {
    "letter":    ["jgr/letter/letter.tex"],
    "guidebook": ["jgr/guidebook/guidebook.tex"],
    "thesis":    ["gedes/thesis/thesis.tex"],
    "abstract":  ["gedes/abstract/gedes_abstract.tex"],
}

INCLUDE_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
BARE_RE = re.compile(r"([A-Za-z0-9_\-]+)\.(?:pdf|png|gif|jpg|jpeg)")
FIG_EXTS = (".pdf", ".png", ".gif", ".jpg", ".jpeg")

README = """# Figure views by document

**These are symlinks, not copies.** The one physical figure home is the parent
`figures/` folder — generators write only there, and every document reaches it
through its own `figures` symlink. This folder exists purely to answer "which
figures does document X use?" without moving anything.

Rebuild after adding or removing a figure:

```bash
.venv/bin/python code/pipeline/figures/build_figure_views.py
```

| View | Meaning |
|---|---|
| `letter/` | the JGR:Planets article — **the active focus** |
| `guidebook/` | teaching companion |
| `thesis/` | GEDES thesis (submitted) |
| `abstract/` | GEDES extended abstract (submitted) |
| `_unused-by-any-doc/` | referenced by no document — review before deleting |
"""


def referenced_by_document() -> dict[str, set[str]]:
    """Map figure stem -> set of documents that reference it."""
    use: dict[str, set[str]] = collections.defaultdict(set)
    for doc, rels in DOCUMENTS.items():
        for rel in rels:
            f = DOCS_ROOT / rel
            if not f.exists():
                continue
            s = f.read_text(errors="ignore")
            for m in INCLUDE_RE.findall(s):
                use[Path(m).stem].add(doc)
            for m in BARE_RE.findall(s):
                use[m].add(doc)
    return use


def main() -> None:
    use = referenced_by_document()
    view = FIG / "_by_document"
    if view.exists():
        shutil.rmtree(view)

    buckets: dict[str, list[Path]] = collections.defaultdict(list)
    for p in sorted(FIG.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in FIG_EXTS:
            continue
        if "_archive" in p.parts or "_by_document" in p.parts:
            continue
        docs = use.get(p.stem, set())
        if not docs:
            buckets["_unused-by-any-doc"].append(p)
        for d in docs:
            buckets[d].append(p)

    for name, files in sorted(buckets.items()):
        d = view / name
        d.mkdir(parents=True, exist_ok=True)
        for p in files:
            os.symlink(os.path.relpath(p, d), d / p.name)
        print(f"  {name:22s} {len(files):3d} figures")

    (view / "README.md").write_text(README)
    print(f"\nwrote {view.relative_to(FIG.parent)}/")


if __name__ == "__main__":
    main()
