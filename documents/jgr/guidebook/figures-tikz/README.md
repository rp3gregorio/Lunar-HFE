# TikZ figures with fast iteration

Each text-heavy flow chart lives here as a self-contained `tikzpicture` body
that the main book reads via `\input`. Iterate on a single figure without
recompiling the whole 61-page document.

## Files

| File | What it is |
|---|---|
| `_preamble.tex` | Shared preamble (colors + TikZ libraries) used by the standalone wrappers. |
| `pipeline.tex` | Body of Fig 1.4 (the retrieval pipeline). |
| `eqnflow.tex` | Body of Fig 1.5 (the equation flow). |
| `*_standalone.tex` | One-page wrappers — compile these for fast iteration. |
| `build.sh` | Rebuild one or all standalone PDFs. |

## Workflow

Edit the figure body (e.g. `eqnflow.tex`), then:

```bash
./build.sh eqnflow         # ~1-2 s, writes eqnflow_standalone.pdf
open eqnflow_standalone.pdf
```

When the layout looks right, recompile the full book in the usual way:

```bash
cd .. && pdflatex guidebook.tex
```

The main book picks up the edited body through `\input{figures-tikz/<name>}`
inside its `figure` environment (which supplies the `\caption` and `\label`).

## Caveats

The standalone wrappers stub `\ref{eq:foo}` as the literal text `[eq:foo]`
because the figure has no access to the book's `.aux`. Layout matches; the
equation numbers fill in correctly only when the figure is embedded in the
full book.
