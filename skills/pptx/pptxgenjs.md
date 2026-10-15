# Building decks from scratch with pptxgenjs

`pptxgenjs` is a JavaScript library for generating `.pptx` files programmatically.
Use it when there is no template or reference deck to start from. The notes below
were checked against version 4.0.1.

## Setup and basic structure

- Import the library with `require("pptxgenjs")`.
- The default export is a constructor; create a presentation with `new pptxgen()`.
- Presentation-level properties: `pres.layout` (the NAME of a layout, as a string),
  `pres.author`, and `pres.title`.
- `pres.addSlide()` adds a slide and returns the slide object.
- `slide.addText(text, options)` puts text on a slide.
- `pres.writeFile({ fileName: "..." })` writes the file and returns a Promise -
  `await` it, or chain `.then()`.

Install it locally in the working directory (`npm install pptxgenjs`);
`require("pptxgenjs")` does not find a global `npm install -g`.

`officecli validate` reports one schema error on EVERY pptxgenjs 4.0.1 file
(`notesMasterIdLst` in `ppt/presentation.xml`) and one per bar chart (`c:axId` in
`c:barChart`). Those come from the library itself and officecli still renders
the deck; treat any OTHER validate error as real.

```js
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Revenue Team";
pres.title = "Third Quarter Review";

const slide = pres.addSlide();
slide.addText("Third quarter in review", {
  x: 0.6,
  y: 0.5,
  fontSize: 32,
  color: "1E2761",
});

pres.writeFile({ fileName: "q3-review.pptx" }).then((name) => {
  console.log(`wrote ${name}`);
});
```

## Layout dimensions

All coordinates are measured in inches. The layout name you assign to `pres.layout`
sets the slide size:

| Layout | Size |
| --- | --- |
| `LAYOUT_16x9` | 10" x 5.625" (the default) |
| `LAYOUT_16x10` | 10" x 6.25" |
| `LAYOUT_4x3` | 10" x 7.5" |
| `LAYOUT_WIDE` | 13.33" x 7.5" |

## Text and formatting

`slide.addText(textOrArray, options)` accepts either a plain string or an array of
run objects.

Common options: `x`, `y`, `w`, `h`, `fontSize`, `fontFace`, `color` (6-character
hex, no `#`), `bold`, `italic`, `align`, `valign`, and `margin`.

- `align` is `"left"`, `"center"`, or `"right"` (`"justify"` is also accepted).
- `valign` is `"top"`, `"middle"`, or `"bottom"`.
- For character spacing, use `charSpacing` (in points). `letterSpacing` is silently
  ignored - measured, `charSpacing: 6` emits spacing while `letterSpacing` emits none.
- For rich text, pass an ARRAY of run objects shaped `{ text, options: { ... } }`, so
  each run can carry its own `bold`, `italic`, and so on.
- For multiple lines, every run except the last needs `breakLine: true`.
- `margin: 0` strips the text box's internal padding. Use it when text must line up
  exactly with shapes, rules, or icons that share the same `x`.

Basic text box:

```js
slide.addText("Centered heading", {
  x: 1,
  y: 0.8,
  w: 8,
  h: 1,
  fontSize: 28,
  fontFace: "Georgia",
  color: "222222",
  bold: true,
  align: "center",
  valign: "middle",
});
```

Character spacing (and a reminder that `letterSpacing` does nothing):

```js
slide.addText("TRACKED HEADLINE", {
  x: 1,
  y: 2,
  fontSize: 18,
  charSpacing: 6, // points; a letterSpacing key here would be ignored
});
```

Rich text with per-run styling:

```js
slide.addText(
  [
    { text: "Revenue ", options: { bold: true } },
    { text: "grew 42%", options: { italic: true } },
  ],
  { x: 1, y: 3, fontSize: 20 }
);
```

Multiple lines (breakLine on all but the last run):

```js
slide.addText(
  [
    { text: "First line", options: { breakLine: true } },
    { text: "Second line", options: { breakLine: true } },
    { text: "Third line" },
  ],
  { x: 1, y: 3.6, fontSize: 16 }
);
```

A title with the internal padding removed so it lines up against a rule at the same x:

```js
slide.addText("Aligned title", {
  x: 0.5,
  y: 0.4,
  w: 9,
  h: 0.7,
  fontSize: 30,
  bold: true,
  margin: 0,
});
```

## Lists and bullets

- A bulleted list is an array of runs, each carrying `bullet: true`; add
  `breakLine: true` to every run except the last.
- Never prefix the text with a unicode bullet character - that produces double
  bullets.
- For a sub-item, use `bullet: true` with `indentLevel: 1` (an integer nesting level).
- For a numbered list, pass a bullet object: `bullet: { type: "number" }`. The `type`
  is `"bullet"` or `"number"`, and the object also supports `characterCode`, `indent`,
  and `numberType`.

Correct bulleted list:

```js
slide.addText(
  [
    { text: "Discovery", options: { bullet: true, breakLine: true } },
    { text: "Design", options: { bullet: true, breakLine: true } },
    { text: "Delivery", options: { bullet: true } },
  ],
  { x: 1, y: 1, w: 6, h: 3, fontSize: 18 }
);
```

WRONG - a hard-coded bullet glyph in the string gives you two bullets:

```js
slide.addText("• Discovery", { x: 1, y: 1, bullet: true }); // double bullet
```

A sub-item nested one level in:

```js
slide.addText(
  [{ text: "Design system tokens", options: { bullet: true, indentLevel: 1 } }],
  { x: 1, y: 2, fontSize: 16 }
);
```

A numbered run:

```js
slide.addText(
  [{ text: "First milestone", options: { bullet: { type: "number" } } }],
  { x: 1, y: 3, fontSize: 16 }
);
```

## Shapes

Add a shape with `slide.addShape(pres.shapes.<NAME>, options)`.

Shape names on `pres.shapes`: `RECTANGLE`, `OVAL`, `LINE`, `ROUNDED_RECTANGLE` (their
underlying OOXML values are `rect`, `ellipse`, `line`, `roundRect`).

Options: `x`, `y`, `w`, `h`; `fill: { color, transparency }` (transparency 0-100);
`line: { color, width, dashType }` (for example `dashType: "dash"`); `rectRadius`
(0.0-1.0, and ONLY effective on `ROUNDED_RECTANGLE`); and `shadow` (below). Draw a
horizontal line with `h: 0` and a `line` option.

Gradient fills are not supported natively - use a gradient image as the background
instead.

Watch the `rectRadius` gotcha: if you overlay a rectangular accent bar on a
`ROUNDED_RECTANGLE`, the bar cannot cover the rounded corners, so they poke out. Use
`RECTANGLE` when you need a clean edge to align against.

The `shadow` object:

| Field | Values |
| --- | --- |
| `type` | `"outer"`, `"inner"`, or `"none"` |
| `color` | 6-character hex, no `#`, and no 8-character hex |
| `blur` | number, 0-100 pt |
| `offset` | number, 0-200 pt; must be non-negative (a negative value corrupts the file) |
| `angle` | number, 0-359 degrees; the direction the shadow falls (135 = bottom-right, 270 = upward) |
| `opacity` | number, 0.0-1.0; use this for transparency, never encode it in the color string |

To throw a shadow upward - for instance beneath a footer bar - use `angle: 270` with a
POSITIVE offset, not a negative one.

```js
// Filled rectangle with an outline
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 0.5, w: 3, h: 1.5,
  fill: { color: "2C5F2D" },
  line: { color: "1B3A1C", width: 2 },
});

// Oval
slide.addShape(pres.shapes.OVAL, {
  x: 4, y: 0.5, w: 1.5, h: 1.5,
  fill: { color: "97BC62" },
});

// Horizontal line
slide.addShape(pres.shapes.LINE, {
  x: 0.5, y: 2.5, w: 9, h: 0,
  line: { color: "888888", width: 1.5, dashType: "dash" },
});

// Semi-transparent fill
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 3, w: 3, h: 1,
  fill: { color: "F96167", transparency: 50 },
});

// Rounded rectangle
slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 4, y: 3, w: 3, h: 1,
  fill: { color: "065A82" },
  rectRadius: 0.15,
});

// Rectangle with a full shadow
slide.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 4.3, w: 3, h: 1,
  fill: { color: "FFFFFF" },
  shadow: { type: "outer", color: "333333", blur: 8, offset: 4, angle: 135, opacity: 0.4 },
});
```

## Images

Add an image with `slide.addImage(options)`.

Three sources:
- `path: "local/or/relative.png"` - a local or relative file path.
- `path: "https://..."` - a URL.
- `data: "image/png;base64,...."` - inline base64, with no file I/O.

Options: `x`, `y`, `w`, `h`; `rotate` (0-359 degrees); `rounding: true` (a circular
crop); `transparency` (0-100); `flipH` and `flipV` (booleans); `altText`
(accessibility); and `hyperlink: { url }`.

Sizing modes via `sizing: { type, ... }`:
- `type: 'contain'` - fit inside the box, keep the ratio (`w`, `h`).
- `type: 'cover'` - fill the box, keep the ratio, cropping if needed (`w`, `h`).
- `type: 'crop'` - cut out a portion (`x`, `y`, `w`, `h`).

To keep the aspect ratio, compute the width from a target height and the source ratio,
then center the image.

Supported formats: PNG, JPG, and GIF (animated GIFs play in Microsoft 365). SVG works
in modern PowerPoint / Microsoft 365.

```js
// Local path
slide.addImage({ path: "assets/logo.png", x: 1, y: 1, w: 2, h: 2 });

// URL
slide.addImage({ path: "https://example.com/hero.jpg", x: 4, y: 1, w: 3, h: 2 });

// Base64
slide.addImage({ data: "image/png;base64,iVBORw0KGgoAAAANSUhEUg...", x: 8, y: 1, w: 1.5, h: 1.5 });

// Full option set
slide.addImage({
  path: "assets/badge.png",
  x: 1, y: 3.5, w: 2, h: 2,
  rotate: 15,
  rounding: true,
  transparency: 20,
  flipH: true,
  flipV: false,
  altText: "Certification badge",
  hyperlink: { url: "https://example.com" },
});

// One call per sizing mode
slide.addImage({ path: "assets/photo.jpg", x: 1, y: 6, w: 2, h: 1.5, sizing: { type: "contain", w: 2, h: 1.5 } });
slide.addImage({ path: "assets/photo.jpg", x: 3.5, y: 6, w: 2, h: 1.5, sizing: { type: "cover", w: 2, h: 1.5 } });
slide.addImage({ path: "assets/photo.jpg", x: 6, y: 6, w: 2, h: 1.5, sizing: { type: "crop", x: 0.2, y: 0.2, w: 2, h: 1.5 } });

// Preserve aspect ratio and center horizontally
const origW = 1600;
const origH = 900;
const maxHeight = 3;
const calcWidth = maxHeight * (origW / origH);
const slideWidth = 10;
const centerX = (slideWidth - calcWidth) / 2;
slide.addImage({ path: "assets/wide.jpg", x: centerX, y: 1, w: calcWidth, h: maxHeight });
```

## Icons

To get a crisp icon that renders everywhere, render a react-icons component to SVG,
rasterize that SVG to PNG with `sharp`, and add the PNG as a base64 image.

Modules involved: `react`, `react-dom/server` (for `renderToStaticMarkup`), `sharp`,
and an icon set from `react-icons/*` (such as `react-icons/fa`).

Render the icon component with `{ color, size }` props (pass `size` as a string),
rasterize the resulting SVG buffer with `sharp(...).png().toBuffer()`, and prefix the
base64 output with `"image/png;base64,"`. Add it with
`slide.addImage({ data, x, y, w, h })`, where `w` and `h` are inches.

Set `size` to at least 256: it controls the raster RESOLUTION, not the on-slide
display size (that is `w` and `h` in inches). A larger `size` gives you a sharper icon
at the same physical dimensions.

Install (locally): `npm install react-icons react react-dom sharp`.

Popular sets: `react-icons/fa` (Font Awesome), `react-icons/md` (Material Design),
`react-icons/hi` (Heroicons), and `react-icons/bi` (Bootstrap Icons).

```js
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const { FaRocket } = require("react-icons/fa");

function iconToSvg(Icon, color, size) {
  return renderToStaticMarkup(React.createElement(Icon, { color, size }));
}

async function iconToDataUri(Icon, color, size) {
  const svg = iconToSvg(Icon, color, size);
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

// inside an async function (CommonJS has no top-level await)
const iconData = await iconToDataUri(FaRocket, "F96167", "256");
slide.addImage({ data: iconData, x: 1, y: 1, w: 0.6, h: 0.6 });
```

## Slide backgrounds

Set `slide.background = { ... }`:
- Solid color: `{ color }` (6-character hex).
- Solid with transparency: `{ color, transparency }` (0-100).
- Image from a URL: `{ path: "https://..." }`.
- Image from base64: `{ data: "image/png;base64,..." }`.

```js
slide.background = { color: "1E2761" };
slide.background = { color: "1E2761", transparency: 30 };
slide.background = { path: "https://example.com/bg.jpg" };
slide.background = { data: "image/png;base64,iVBORw0KGgoAAAANSUhEUg..." };
```

## Tables

`slide.addTable(rows, options)` takes `rows` as an array of row arrays. Each cell is
either a plain string or an object `{ text, options }`.

Table options: `x`, `y`, `w`, `h`; `border: { pt, color }`; `fill: { color }`; and
`colW: [..]` (per-column widths). Cell options: `fill: { color }`, `color`, `bold`,
`colspan`, and `rowspan`.

Simple 2x2 table:

```js
slide.addTable(
  [
    ["Quarter", "Revenue"],
    ["Q1", "$1.2M"],
  ],
  { x: 0.5, y: 1, w: 6, border: { pt: 1, color: "CCCCCC" }, fill: { color: "F5F5F5" } }
);
```

Advanced table with a styled header cell, a spanning cell, and per-column widths:

```js
slide.addTable(
  [
    [
      { text: "Region", options: { fill: { color: "1E2761" }, color: "FFFFFF", bold: true } },
      { text: "Q1" },
      { text: "Q2" },
    ],
    [{ text: "Combined total", options: { colspan: 2 } }, { text: "$3.4M" }],
  ],
  { x: 0.5, y: 1, w: 8, colW: [3, 2.5, 2.5] }
);
```

## Charts

`slide.addChart(pres.charts.<TYPE>, dataArray, options)`.

Chart types on `pres.charts`: `BAR`, `LINE`, `PIE`, `DOUGHNUT`, `SCATTER`, `BUBBLE`,
and `RADAR` (`AREA`, `BAR3D`, and `BUBBLE3D` also exist). Their OOXML values are
lowercase - `bar`, `line`, `pie`, and so on, with the 3D variants written `bar3D` and
`bubble3D`.

A data series is shaped `{ name, labels: [...], values: [...] }`; pass an array of
them.

Common options: `x`, `y`, `w`, `h`; `barDir: 'col'` (bar orientation); `showTitle` and
`title`; `lineSize` and `lineSmooth` (line charts); and `showPercent` (pie).

Styling options for a modern look:
- `chartColors: [hex, ...]` - the series or segment colors; match your palette.
- `chartArea: { fill: { color }, border, roundedCorners }` - the chart background.
- `catAxisLabelColor` and `valAxisLabelColor` - axis label colors.
- `valGridLine: { color, size }` and `catGridLine: { style: "none" }` - grid lines;
  `style: "none"` hides them.
- `showValue: true`, `dataLabelPosition`, and `dataLabelColor` - data labels.
- `showLegend: false` - hide the legend for a single series.
- `legendPos`: `"b"`, `"t"`, `"l"`, `"r"`, or `"tr"` (defaults to `"r"`).

Data-label position gotcha (measured): the valid tokens depend on the chart type -
`'b'`, `'bestFit'`, `'ctr'`, `'l'`, `'r'`, `'t'`, `'inEnd'`, `'outEnd'` - and an
invalid token is SILENTLY dropped. For a clustered BAR chart, the token that centers
the label is `"ctr"`, NOT `"center"`; passing `"center"` emits no position at all.
Stick to `"ctr"`, `"inEnd"`, or `"outEnd"`.

```js
// Bar
slide.addChart(pres.charts.BAR, [{ name: "Sales", labels: ["Q1", "Q2", "Q3"], values: [12, 18, 25] }], {
  x: 0.5, y: 1, w: 4, h: 3,
  barDir: "col",
  showTitle: true,
  title: "Quarterly sales",
});

// Line
slide.addChart(pres.charts.LINE, [{ name: "Signups", labels: ["Jan", "Feb", "Mar"], values: [40, 65, 90] }], {
  x: 5, y: 1, w: 4, h: 3,
  lineSize: 3,
  lineSmooth: true,
});

// Pie
slide.addChart(pres.charts.PIE, [{ name: "Share", labels: ["A", "B", "C"], values: [50, 30, 20] }], {
  x: 0.5, y: 4.2, w: 4, h: 3,
  showPercent: true,
});

// Heavily styled bar chart
slide.addChart(pres.charts.BAR, [{ name: "Revenue", labels: ["North", "South", "East"], values: [120, 90, 150] }], {
  x: 5, y: 4.2, w: 4, h: 3,
  barDir: "col",
  chartColors: ["1E2761", "028090", "F96167"],
  chartArea: { fill: { color: "FFFFFF" }, roundedCorners: true },
  catAxisLabelColor: "444444",
  valAxisLabelColor: "444444",
  valGridLine: { color: "EEEEEE", size: 1 },
  catGridLine: { style: "none" },
  showValue: true,
  dataLabelPosition: "outEnd",
  dataLabelColor: "222222",
  showLegend: false,
});
```

## Slide masters

Define a master with `pres.defineSlideMaster({ title, background, objects })`. The
`objects` array holds the master's content; a placeholder is written
`{ placeholder: { options: { name, type, x, y, w, h } } }` (for example
`type: 'title'`). Use the master when adding a slide with
`pres.addSlide({ masterName: "<title>" })`, and fill a placeholder on that slide with
`slide.addText("...", { placeholder: "<name>" })`.

```js
pres.defineSlideMaster({
  title: "SECTION_MASTER",
  background: { color: "1E2761" },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 2.2, w: 8.8, h: 1.2 } } },
  ],
});

const sectionSlide = pres.addSlide({ masterName: "SECTION_MASTER" });
sectionSlide.addText("Part two: results", { placeholder: "title" });
```

## Common pitfalls

1. Never put a `#` in a hex color - use `FF0000`, not `#FF0000`. The `#` is written
   straight into the XML (measured), producing an invalid color value and corrupting
   the file.
2. Never fold opacity into an 8-character hex color (such as `"00000020"`) - it
   corrupts the file. Use the `opacity` property instead.
3. Use `bullet: true`, never a unicode bullet character, or you get double bullets.
4. Put `breakLine: true` between array items and runs, or they render on one line.
5. Avoid `lineSpacing` on bulleted text (it opens excessive gaps); use
   `paraSpaceAfter` instead.
6. Give each presentation a FRESH `new pptxgen()` instance - do not reuse one across
   presentations.
7. Never reuse a single options or shadow OBJECT across calls. pptxgenjs mutates the
   object in place, converting its values to EMU, so the second call receives values
   that were already converted. Measured: a shared shadow object made the second
   `addShape` multiply `blur`/`offset`/`angle` a second time, producing a blur radius
   around 967,740,000 EMU instead of the correct 76,200, which fails schema
   validation. Build a fresh object per call - a factory function is the clean way.
8. Do not pair `ROUNDED_RECTANGLE` with a rectangular accent-bar overlay; the bar
   cannot cover the rounded corners. Use `RECTANGLE` instead.

WRONG vs CORRECT:

```js
// 1. Hex color
slide.addText("bad", { x: 1, y: 1, color: "#FF0000" });  // WRONG - corrupts the file
slide.addText("good", { x: 1, y: 1, color: "FF0000" });  // CORRECT

// 2. Opacity - never bake alpha into the color; use the opacity property
slide.addShape(pres.shapes.RECTANGLE, {
  x: 1, y: 1, w: 2, h: 1, fill: { color: "000000" },
  shadow: { type: "outer", color: "00000020", blur: 6, offset: 3, angle: 135 }, // WRONG - 8-char color
});
slide.addShape(pres.shapes.RECTANGLE, {
  x: 1, y: 1, w: 2, h: 1, fill: { color: "000000" },
  shadow: { type: "outer", color: "000000", blur: 6, offset: 3, angle: 135, opacity: 0.13 }, // CORRECT
});

// 7. Shared object (WRONG) vs a factory that returns a fresh object each call (CORRECT)
const shared = { type: "outer", color: "333333", blur: 8, offset: 4, angle: 135, opacity: 0.4 };
slide.addShape(pres.shapes.RECTANGLE, { x: 1, y: 1, w: 2, h: 1, shadow: shared }); // first call fine
slide.addShape(pres.shapes.RECTANGLE, { x: 4, y: 1, w: 2, h: 1, shadow: shared }); // WRONG - second call corrupted

const makeShadow = () => ({ type: "outer", color: "333333", blur: 8, offset: 4, angle: 135, opacity: 0.4 });
slide.addShape(pres.shapes.RECTANGLE, { x: 1, y: 1, w: 2, h: 1, shadow: makeShadow() }); // CORRECT
slide.addShape(pres.shapes.RECTANGLE, { x: 4, y: 1, w: 2, h: 1, shadow: makeShadow() }); // CORRECT

// 8. Rounded rectangle + accent bar
slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1, y: 1, w: 4, h: 2, fill: { color: "FFFFFF" } });
slide.addShape(pres.shapes.RECTANGLE, { x: 1, y: 1, w: 0.15, h: 2, fill: { color: "F96167" } }); // WRONG - corners poke out

slide.addShape(pres.shapes.RECTANGLE, { x: 6, y: 1, w: 4, h: 2, fill: { color: "FFFFFF" } });
slide.addShape(pres.shapes.RECTANGLE, { x: 6, y: 1, w: 0.15, h: 2, fill: { color: "F96167" } }); // CORRECT - clean edges
```

## Quick reference

- Shapes: `RECTANGLE`, `OVAL`, `LINE`, `ROUNDED_RECTANGLE`.
- Charts: `BAR`, `LINE`, `PIE`, `DOUGHNUT`, `SCATTER`, `BUBBLE`, `RADAR`.
- Layouts: `LAYOUT_16x9` (10" x 5.625"), `LAYOUT_16x10`, `LAYOUT_4x3`, `LAYOUT_WIDE`.
- Alignment: `"left"`, `"center"`, `"right"`.
- Chart data-label positions: `"outEnd"`, `"inEnd"`, `"ctr"` (note: not `"center"`).
