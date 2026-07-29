#!/usr/bin/env node
/**
 * SPEAKER_SCRIPT.md  ->  SPEAKER_SCRIPT.docx
 *
 * The markdown stays the single source of truth; this only renders it. Re-run
 * after any edit to the script rather than editing the .docx by hand, or the
 * two drift apart.
 *
 * Podium-oriented layout, not a generic markdown dump:
 *   - spoken text is 13 pt, 1.5-spaced, indented, with a coral rule down the
 *     left margin, so at a glance you can see what to SAY versus what to DO
 *   - stage directions are small grey italics and can never be mistaken for
 *     lines to read out
 *   - each `---` in the markdown starts a new page, which puts Part 1, Part 2,
 *     Backup, Q&A and the numbers table on their own pages
 *
 *   node make_script_docx.js
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageBreak, Header, Footer, PageNumber, VerticalAlign,
} = require("docx");

const HERE = __dirname;
const SRC = path.join(HERE, "SPEAKER_SCRIPT.md");
const OUT = path.join(HERE, "SPEAKER_SCRIPT.docx");

// US Letter, 0.75 in side margins -> 10080 DXA of content
const PAGE = { W: 12240, H: 15840, M: 1080 };
const CONTENT = PAGE.W - 2 * PAGE.M;

const CORAL = "B85B3A";   // project accent, used for the spoken-text rule
const CHAR = "2A2520";
const DIM = "6E6862";
const GRID = "D8D4CE";

// ---------------------------------------------------------------- inline
// **bold**, *italic*, `code`  ->  TextRun[]
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  const push = (t, extra) => {
    if (t) out.push(new TextRun({ text: t, ...base, ...extra }));
  };
  while ((m = re.exec(text)) !== null) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) push(tok.slice(2, -2), { bold: true });
    else if (tok.startsWith("`")) push(tok.slice(1, -1), { font: "Consolas", size: (base.size || 22) - 2 });
    else push(tok.slice(1, -1), { italics: true });
    last = m.index + tok.length;
  }
  push(text.slice(last));
  return out.length ? out : [new TextRun({ text: "", ...base })];
}

// ---------------------------------------------------------------- blocks
const children = [];

function spoken(lines) {
  // one docx paragraph per markdown paragraph inside the blockquote
  lines.forEach((para) => {
    children.push(new Paragraph({
      children: runs(para, { size: 26, color: CHAR }),   // 13 pt
      spacing: { line: 360, before: 100, after: 200 },   // 1.5 lines
      indent: { left: 400, right: 200 },
      border: { left: { style: BorderStyle.SINGLE, size: 18, color: CORAL, space: 14 } },
    }));
  });
}

function stage(text) {
  children.push(new Paragraph({
    children: runs(text, { size: 19, color: DIM, italics: true }),
    spacing: { before: 120, after: 160 },
  }));
}

function table(rows) {
  const ncol = rows[0].length;
  // narrow first column for the numbered backup/index tables
  const firstNarrow = rows.every((r) => r[0].length <= 4);
  let widths;
  if (firstNarrow && ncol >= 2) {
    const rest = Math.floor((CONTENT - 700) / (ncol - 1));
    widths = [CONTENT - rest * (ncol - 1), ...Array(ncol - 1).fill(rest)];
  } else {
    const w = Math.floor(CONTENT / ncol);
    widths = Array(ncol).fill(w);
    widths[0] = CONTENT - w * (ncol - 1);
  }
  const border = { style: BorderStyle.SINGLE, size: 1, color: GRID };
  const borders = { top: border, bottom: border, left: border, right: border };
  children.push(new Table({
    width: { size: CONTENT, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((cells, ri) => new TableRow({
      tableHeader: ri === 0,
      children: cells.map((c, ci) => new TableCell({
        borders,
        width: { size: widths[ci], type: WidthType.DXA },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        verticalAlign: VerticalAlign.CENTER,
        shading: ri === 0 ? { fill: "F2EFEA", type: ShadingType.CLEAR } : undefined,
        children: [new Paragraph({
          children: runs(c, { size: 19, color: CHAR, bold: ri === 0 }),
          spacing: { before: 20, after: 20 },
        })],
      })),
    })),
  }));
  children.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
}

// ---------------------------------------------------------------- parse
const lines = fs.readFileSync(SRC, "utf8").split("\n");
let i = 0;
while (i < lines.length) {
  const line = lines[i];

  if (/^---\s*$/.test(line)) {                       // section break -> new page
    children.push(new Paragraph({ children: [new PageBreak()] }));
    i++; continue;
  }

  if (/^\s*$/.test(line)) { i++; continue; }

  // ---- tables
  if (/^\|/.test(line)) {
    const rows = [];
    while (i < lines.length && /^\|/.test(lines[i])) {
      const cells = lines[i].split("|").slice(1, -1).map((c) => c.trim());
      if (!cells.every((c) => /^:?-{2,}:?$/.test(c))) rows.push(cells);
      i++;
    }
    table(rows);
    continue;
  }

  // ---- blockquote = spoken text
  if (/^>/.test(line)) {
    const paras = []; let buf = [];
    while (i < lines.length && /^>/.test(lines[i])) {
      const t = lines[i].replace(/^>\s?/, "").trimEnd();
      if (t === "") { if (buf.length) { paras.push(buf.join(" ")); buf = []; } }
      else buf.push(t);
      i++;
    }
    if (buf.length) paras.push(buf.join(" "));
    spoken(paras);
    continue;
  }

  // ---- headings
  const h = line.match(/^(#{1,3})\s+(.*)$/);
  if (h) {
    const depth = h[1].length;
    const text = h[2].trim();
    if (depth === 1) {
      children.push(new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: runs(text, { size: 34, bold: true, color: CHAR }),
        spacing: { before: 240, after: 200 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: CORAL, space: 6 } },
      }));
    } else if (depth === 2) {
      // "Slide 10 · Title — 70 s"  ->  time rendered in the accent colour
      const m = text.match(/^(.*?)\s+—\s+(\d+\s*s)$/);
      const kids = m
        ? [...runs(m[1], { size: 26, bold: true, color: CHAR }),
           new TextRun({ text: "   " + m[2], size: 22, bold: true, color: CORAL })]
        : runs(text, { size: 26, bold: true, color: CHAR });
      children.push(new Paragraph({
        heading: HeadingLevel.HEADING_2, children: kids,
        spacing: { before: 320, after: 100 },
      }));
    } else {
      children.push(new Paragraph({
        heading: HeadingLevel.HEADING_3,
        children: runs(text, { size: 23, bold: true, color: CHAR }),
        spacing: { before: 240, after: 100 },
      }));
    }
    i++; continue;
  }

  // ---- lists
  const cb = line.match(/^-\s+\[[ x]\]\s+(.*)$/);
  const bu = line.match(/^-\s+(.*)$/);
  const nu = line.match(/^(\d+)\.\s+(.*)$/);
  if (cb || bu || nu) {
    let body = (cb ? cb[1] : bu ? bu[1] : nu[2]);
    // absorb continuation lines
    while (i + 1 < lines.length && /^\s{2,}\S/.test(lines[i + 1])) {
      body += " " + lines[++i].trim();
    }
    children.push(new Paragraph({
      numbering: { reference: nu ? "nums" : "bullets", level: 0 },
      children: runs(body, { size: 21, color: CHAR }),
      spacing: { before: 40, after: 40 },
    }));
    i++; continue;
  }

  // ---- whole-line italic = stage direction
  if (/^\*[^*].*\*$/.test(line.trim())) {
    let body = line.trim();
    while (!/\*$/.test(body) && i + 1 < lines.length) body += " " + lines[++i].trim();
    stage(body.replace(/^\*|\*$/g, ""));
    i++; continue;
  }

  // ---- plain paragraph (join wrapped lines)
  let buf = [line.trim()];
  while (i + 1 < lines.length && lines[i + 1].trim() !== ""
         && !/^[#>|-]/.test(lines[i + 1]) && !/^\d+\./.test(lines[i + 1])) {
    buf.push(lines[++i].trim());
  }
  children.push(new Paragraph({
    children: runs(buf.join(" "), { size: 21, color: CHAR }),
    spacing: { before: 60, after: 120, line: 276 },
  }));
  i++;
}

// ---------------------------------------------------------------- document
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 21, color: CHAR } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
        quickFormat: true, run: { size: 34, bold: true, font: "Arial", color: CHAR },
        paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
        quickFormat: true, run: { size: 26, bold: true, font: "Arial", color: CHAR },
        paragraph: { spacing: { before: 320, after: 100 }, outlineLevel: 1,
                     keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal",
        quickFormat: true, run: { size: 23, bold: true, font: "Arial", color: CHAR },
        paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 2,
                     keepNext: true } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET,
          text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 260 } } } }] },
      { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL,
          text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 260 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: { size: { width: PAGE.W, height: PAGE.H },
              margin: { top: 1080, right: PAGE.M, bottom: 1080, left: PAGE.M } },
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({
          text: "GEDES defense · speaker script · 24M58378 Gregorio",
          size: 16, color: DIM })],
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: GRID, space: 6 } },
      })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], size: 16, color: DIM })],
      })] }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log(`wrote ${OUT}  (${(buf.length / 1024).toFixed(0)} kB, ${children.length} blocks)`);
});
