# Post-build review brief (queued 2026-07-27)

Run **after** the fresh guidebook is drafted and builds clean. Panel review, then
apply the findings to the document.

## What the panel must check

1. **Accessibility of tone.** The primary test. A reader with little or no
   background must be able to follow every chapter. Any passage that assumes
   undergraduate physics, numerical analysis, or statistics without unpacking it
   first is a defect, not a style preference. The document's job is to make the
   author understand his own study end to end.

2. **Figure quality.** Every figure that appears in the book gets rendered at
   dpi >= 300 and inspected. Report anything that looks bad: text on data,
   clipped labels, unreadable at print size, overlapping legends, dead space,
   illegible at the size it is placed.

3. **Completeness.** Nothing in the thesis left uncovered.

4. **Internal consistency.** Every number traceable to `code/results/*.json` or
   `code/src/lunar/config.py`. No stale value survives.

## Reviewer / author separation

The reviewer panel is READ-ONLY and produces reports only. Applying the findings
is a separate authoring pass afterwards. Do not let a reviewer edit the book.

## Unresolved: the figure conflict

Two instructions from the user are in tension:

- *"if a figure is already out there dont try to remove or improve it i want some
  consistency"*
- *"make sure no figures look bad, if it is re design"*

This matters because `documents/jgr/guidebook/figures` is a **symlink** to the
repo-wide `figures/` directory, shared with the thesis and the letter. Redesigning
a shared figure changes it in the submitted thesis and the frozen letter too.

**Default adopted unless the user overrides:**

| Asset | Policy |
|---|---|
| Shared matplotlib PDFs (`figures/*.pdf`) | **Frozen.** If one renders badly, report it with evidence and propose a fix; do not silently change it. |
| TikZ diagrams (`figures-tikz/*.tex`) | **Guidebook-local, fair game.** Redraw freely to the lunar-figures connector rules. |
| New diagrams | TikZ only, so the shared set is never touched. |

Rationale: the thesis PDF `24M58378GregorioMT.pdf` is a submission artifact.
Silently changing a figure it depends on would desync a submitted document.
