---
name: xlsx
description: "Create, edit, repair, or analyze spreadsheets whenever a spreadsheet file is the main input or the main output of a task. Covers opening and reworking existing .xlsx, .xlsm, .csv, and .tsv files (adding columns, computing formulas, formatting, charting, and turning malformed rows, misplaced headers, or junk rows into a clean sheet), building a brand-new workbook from scratch or from other data sources, and converting between tabular formats. Fires when the user names or points at a spreadsheet by name or path, even casually (for example a workbook in their downloads), and wants it acted on or something produced from it. The deliverable must be a spreadsheet file. Do not use when the main deliverable is a Word document, an HTML report, a standalone Python script, a database pipeline, or a Google Sheets API integration, even if tabular data is involved."
enabled: true
license: MIT-0
---

# Requirements for outputs

## All Excel files

### Font

Use one consistent, professional typeface across the entire deliverable (for
example Arial or Times New Roman), unless the user asks for something different.

### Formula errors

Every model you hand over must contain zero formula errors. The codes to watch
for are `#REF!`, `#DIV/0!`, `#VALUE!`, `#N/A`, and `#NAME?`.

### Updating an existing template

When you update a file that already has an established format, study its layout,
style, and conventions and match them exactly. Never force the standardized
formatting from this skill onto a file that already follows its own patterns:
the template's conventions take precedence over every guideline here.

## Financial models

These conventions follow the industry-standard practice and apply unless the
user or an existing template says otherwise.

### Color coding

| meaning | style | RGB | hex |
|---|---|---|---|
| hardcoded inputs; numbers users change for scenarios | blue text | 0,0,255 | `0000FF` |
| every formula and calculation | black text | 0,0,0 | `000000` |
| links pulling from other worksheets in the same workbook | green text | 0,128,0 | `008000` |
| external links to other files | red text | 255,0,0 | `FF0000` |
| key assumptions needing attention; cells that need updating | yellow background (fill) | 255,255,0 | `FFFF00` |

### Number formats

- Years: store them as text strings so `2024` never renders as `2,024`.
- Currency: `$#,##0`; always state the unit in the header, e.g. `Revenue ($mm)`.
- Zeros: display them as `-` through number formatting, percentages included;
  example format string `$#,##0;($#,##0);-`.
- Percentages: default to `0.0%` (one decimal place).
- Valuation multiples (EV/EBITDA, P/E): `0.0x`.
- Negatives: parentheses, so `(123)` rather than `-123`.

### Formula construction

Assumptions placement:

- Give every assumption (growth rates, margins, multiples, and the like) its own
  dedicated cell.
- Reference those cells from your formulas rather than embedding the constant
  directly.
- Right: `=B5*(1+$B$6)`. Wrong: `=B5*1.05`.

Error prevention:

- Verify every cell reference.
- Check ranges for off-by-one mistakes.
- Keep formulas consistent across all projection periods.
- Test edge cases such as zero values and negative numbers.
- Confirm there are no unintended circular references.

Documenting hardcoded values:

- Record the source in a cell comment, or in the adjacent cell when the value
  sits at the end of a table.
- Citation pattern: `Source: [System/Document], [Date], [Specific Reference], [URL if applicable]`
- Worked examples:
  - `Source: Northwind Industries 10-K, FY2023, p. 74, Note 9 (Segment Reporting), https://www.sec.gov/edgar/<accession>`
  - `Source: Northwind Industries 10-Q, Q3 2024, Exhibit 99.2, https://www.sec.gov/edgar/<accession>`
  - `Source: Bloomberg, 2024-08-06, NWND US Equity`
  - `Source: FactSet, 2024-08-06, Consensus Estimates screen`

# Working with xlsx files

## Overview

The task may be to create a new `.xlsx`, edit an existing one, or analyze its
contents. Each of those calls for a different tool and workflow, laid out below.

## Important requirements

**Use `officecli` for formula values, and for looking at the sheet.** It is a
single self-contained binary that evaluates Excel formulas itself (350+
functions) and renders the workbook - no LibreOffice, no Excel, no Office
install. Verify it is present before relying on it:

```bash
officecli --version
```

If missing, install it (open a new shell if the binary still is not found):

```bash
# macOS / Linux
curl -fsSL https://d.officecli.ai/install.sh | bash
# Windows (PowerShell)
irm https://d.officecli.ai/install.ps1 | iex
```

Runs on macOS, Linux and Windows (x64 and arm64 on each, plus musl/Alpine
Linux) - the installer picks the right binary. **Write output next to the
workbook or into a directory you created, not `/tmp`**: the examples below use
`/tmp` for brevity, but it does not exist on Windows - use `$env:TEMP` there, or
a relative `out\` folder.

Supported formats are exactly `.docx`, `.xlsx`, `.pptx`. Legacy `.xls` is NOT
supported - ask for an `.xlsx`. `.csv`/`.tsv` are handled with pandas, or
imported with `officecli import`.

**Do NOT assume LibreOffice exists.** It is not installed on most machines this
skill runs on, and nothing here installs it.

## Reading and analyzing data

### Reading with officecli

Fastest way to see what is actually in a workbook, including COMPUTED formula
values:

```bash
# Structure: sheets, dimensions, formula counts
officecli view file.xlsx outline

# Cell values as text (A1=value, tab-separated; empty cells omitted)
officecli view file.xlsx text
officecli view file.xlsx text --cols A,B,C --max-lines 50
officecli view file.xlsx text --range "Sheet1!A1:C10"

# One cell, with formula AND cached/computed value
officecli get file.xlsx /Sheet1/B10 --json

# Find cells: CSS-like selectors, incl. row-by-column-name
officecli query file.xlsx 'cell:has(formula)'
officecli query file.xlsx 'Sheet1!row[Salary>5000]'

# Formula errors and other problems, mechanically
officecli view file.xlsx issues --json

# SEE the sheet (PNG needs a headless browser: Playwright/Chrome/Edge/Firefox)
officecli view file.xlsx screenshot -o /tmp/sheet.png
officecli view file.xlsx screenshot --range "Sheet1!A1:H40" -o /tmp/region.png
officecli view file.xlsx html -o /tmp/sheet.html
officecli watch file.xlsx        # live preview at http://localhost:26315
```

### pandas for analysis

pandas is the tool for data analysis, quick visualization, and everyday
operations - it has strong data-manipulation capabilities.

```python
import pandas as pd

df = pd.read_excel("sales.xlsx")                       # first sheet by default
sheets = pd.read_excel("sales.xlsx", sheet_name=None)  # dict of every sheet

df.head()        # preview the leading rows
df.info()        # column names, dtypes, non-null counts
df.describe()    # summary statistics for numeric columns

df.to_excel("sales_clean.xlsx", index=False)
```

## Excel file workflows

The rest of this document covers the concrete workflows for building and editing
workbooks.

## Always write formulas, never hardcoded values (CRITICAL)

Always write real Excel formulas. Never compute a number in Python and write the
result into the cell. Writing the formula keeps the workbook dynamic and
updateable, so it recalculates whenever its source data changes. This applies to
every calculation - totals, percentages, ratios, differences, and so on.

Wrong (the computed number is frozen into the cell):

```python
ws["B12"] = df["revenue"].sum()                                          # e.g. 48200 baked in
ws["C12"] = (df["revenue"].iloc[-1] - df["revenue"].iloc[0]) / df["revenue"].iloc[0]  # e.g. 0.32 baked in
ws["D12"] = sum(df["margin"]) / len(df["margin"])                        # e.g. 0.18 baked in
```

Right (assign formula strings so the sheet stays live):

```python
ws["B12"] = "=SUM(B2:B11)"
ws["C12"] = "=(B11-B2)/B2"
ws["D12"] = "=AVERAGE(D2:D11)"
```

## Common workflow

Two routes. Prefer the first when formulas matter.

### Route A - write formulas with officecli (evaluated as you write)

`officecli set` evaluates a formula at write time and caches the result, so
there is no separate recalculation pass:

```bash
officecli create output.xlsx
officecli set output.xlsx /Sheet1/A1 --prop value="Revenue" --prop bold=true
officecli set output.xlsx /Sheet1/B10 --prop formula="=SUM(B2:B9)"

# read the computed value back
officecli get output.xlsx /Sheet1/B10 --json
```

Then verify (see Verifying formula values below).

### Route B - build with openpyxl/pandas, then fix up the values

openpyxl writes formulas as STRINGS with no cached values, so a reader that
does not recalculate sees blanks.

1. **Choose the tool**: pandas for data, openpyxl for formulas and formatting.
2. **Create or load**: make a new workbook or open the existing file.
3. **Modify**: add or edit data, formulas, and formatting.
4. **Save to disk**.
5. **Populate formula values (MANDATORY IF USING FORMULAS)**: re-write each
   formula cell through `officecli set`, which evaluates it:
   ```bash
   officecli set output.xlsx /Sheet1/B10 --prop formula="=SUM(B2:B9)"
   ```
   For many cells, do it in one pass with `batch`:
   ```bash
   officecli batch output.xlsx --commands '[
     {"op":"set","path":"/Sheet1/B10","props":{"formula":"=SUM(B2:B9)"}},
     {"op":"set","path":"/Sheet1/C10","props":{"formula":"=AVERAGE(C2:C9)"}}
   ]' --json
   ```
6. **Verify and fix any errors**: see Verifying formula values below. Common
   errors to fix:
   - `#REF!`: invalid cell reference
   - `#DIV/0!`: division by zero
   - `#VALUE!`: wrong data type in a formula
   - `#NAME?`: formula name not recognized

**Flush before a non-officecli program reads the file.** officecli keeps a
resident process, so openpyxl/pandas/an upload may otherwise read a stale file:

```bash
officecli save output.xlsx     # flush, keep resident warm
officecli close output.xlsx    # flush + release
```

Note: a workbook created by openpyxl names its first sheet `Sheet`, not
`Sheet1`, so officecli paths must use the real sheet name (`/Sheet/B10`). A wrong
name is answered with `Sheet not found ... Available sheets: [Sheet]`.

### Creating a new workbook with openpyxl

openpyxl is the choice when formulas and formatting matter.

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active
ws.title = "Model"

ws["A1"] = "Growth rate"
ws["B1"] = 0.08
ws["B1"].font = Font(bold=True, color="0000FF")             # blue hardcoded input
ws["B1"].fill = PatternFill("solid", start_color="FFFF00")  # yellow: assumption to review

ws.append(["Year", "Revenue ($mm)"])   # header row lands next
ws["A3"] = 2024
ws["B3"] = 100
ws["A4"] = 2025
ws["B4"] = "=B3*(1+$B$1)"               # formula string referencing the assumption cell

ws["A2"].alignment = Alignment(horizontal="center")
ws.column_dimensions["A"].width = 16

wb.save("model.xlsx")
```

### Editing an existing workbook with openpyxl

Loading with openpyxl preserves the existing formulas and formatting.

```python
from openpyxl import load_workbook

wb = load_workbook("model.xlsx")     # formulas and formatting preserved
ws = wb.active                        # or wb["Model"]

for name in wb.sheetnames:
    sheet = wb[name]
    print(name, sheet.max_row, sheet.max_column)

ws["C1"] = "Reviewed"
ws.insert_rows(2)                     # push existing rows down by one
ws.delete_cols(4)                     # drop column D

notes = wb.create_sheet("Notes")
notes["A1"] = "Change log"

wb.save("model_v2.xlsx")
```

## Verifying formula values

Excel files created or modified by openpyxl contain formulas as strings but no
calculated values. `officecli` evaluates a formula when you WRITE it (`set
... --prop formula=...`), and exposes three separate readback keys so you can
tell a real value from a stale one:

| key | meaning |
|---|---|
| `cachedValue` | the value stored in the file - what a non-recalculating reader sees |
| `computedValue` | what officecli's evaluator computes NOW |
| `uncalculated` | `true` if the formula cell has no cached value at all |

```bash
# one cell
officecli get output.xlsx /Sheet1/B10 --json

# just the cached value
officecli get output.xlsx /Sheet1/B10 --json | jq '.data.results[0].format.cachedValue'

# every formula cell
officecli query output.xlsx 'cell:has(formula)' --json

# formulas shown inline with their resolved values
officecli view output.xlsx annotated

# error scan across the workbook (#REF!, #DIV/0!, #VALUE!, #NAME?, ...)
officecli view output.xlsx issues --json
```

**`cachedValue` != `computedValue` means the file on disk is lying.** That is a
stale cache, reported by `view issues` as `formula_cache_stale`. Fix it by
re-writing the formula (see below), not by ignoring it.

### The staleness trap - read this before shipping a multi-formula model

A formula is evaluated at the moment it is written, using whatever its
precedents had cached AT THAT MOMENT. So a downstream formula written before its
upstream was computed caches a wrong value - often `0` - and that wrong value
survives into every reader that does not recalculate.

After any multi-formula build - especially `SUMPRODUCT`, `SUMIFS` with dynamic
criteria, `INDEX`/`MATCH`, or cross-sheet chains - **re-touch every downstream
cell** by running the same `set` again so it recomputes from the now-correct
upstream:

```bash
# second pass: re-write the dependent formulas in dependency order
officecli set model.xlsx /Summary/B2 --prop formula="=SUMPRODUCT(Data!B2:B50,Data!C2:C50)"
```

Do the re-touch pass WITHOUT a resident open (`officecli close model.xlsx`
first) - re-touching cross-sheet chains through a resident is unreliable.

Two more limits worth knowing:
- A cell the evaluator could not compute carries the sentinel
  `#OCLI_NOTEVAL!`. Remedy: close residents, then `set` the cell again.
- **Dynamic arrays**: only the anchor (top-left) cell is evaluated; the spilled
  cells are produced by Excel when it opens the file.

One further limit, measured on officecli 1.0.152: a formula cell with no cached
value at all - which is every formula openpyxl writes, and also a dependent whose
precedent was changed afterwards - is not listed by `view issues` at all. That
command reports errors and stale caches, not missing ones. Confirm that
`cachedValue` is non-null, or simply re-`set` every formula cell.

## Full-workbook check with scripts/recalc.py

`scripts/recalc.py` is an optional one-pass checker. The primary error check is
officecli's `view issues` (see Checking for formula errors); reach for
`recalc.py` when you want a single pass that adds a full cached-value scan, or
when you want LibreOffice recalculation on a machine without officecli.

Usage:

```bash
# macOS / Linux
python scripts/recalc.py model.xlsx 60
```

```powershell
# Windows (PowerShell)
python scripts\recalc.py model.xlsx 60
```

- The argument is `python scripts/recalc.py <file.xlsx> [timeout_seconds]`.
- `timeout_seconds` is an integer (default `120`) applied to the engine
  subprocess. `-h` / `--help` prints usage and exits 0; running with no
  arguments, or a non-integer timeout, exits 2.
- Only `.xlsx` is accepted (so not `.xlsm`); a missing file or any other suffix
  is an error and exits 1.
- It is a CHECKER: it never modifies the input workbook and does not write cached
  values back. Populating cached values is still `officecli set` (see the
  workflow and Verifying formula values above).

Engine selection, in order:

1. If `officecli` is on PATH, it runs `officecli view <file> issues --json`.
   Issues with subtype `formula_eval_error` or `formula_ref_missing_sheet`, and
   any other `formula_*` issue whose message or context contains an Excel error
   string, count as errors. Any remaining `formula_*` issue (for example
   `formula_cache_stale`) is printed under Notes and is NOT counted. Non-formula
   issues are ignored.
2. Otherwise, if `soffice` is on PATH, LibreOffice runs headless to re-save the
   file (`soffice --headless --calc --convert-to xlsx --outdir <temp dir>
   <file>`), producing a recalculated COPY in a temp directory that the scan then
   reads. If no copy is produced, the original file is scanned instead.
3. If neither is present, it prints that officecli is not on PATH and LibreOffice
   was not found, then still scans the file's existing cached values (no crash).

In every case an openpyxl pass follows. It opens the file with
`load_workbook(..., data_only=True, read_only=True)` and scans every cell of
every sheet for the seven error strings `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`,
`#N/A`, `#NULL!`, `#NUM!`. This catches errors that a real engine (LibreOffice,
or a file last saved by Excel) has cached, as well as error text typed literally
into a cell. The results from both mechanisms are merged and de-duplicated per
(sheet, cell).

Exit code: `0` when no Excel error cells are found; `1` when at least one is
found (or on the input/scan errors above).

Two gotchas:
- Exit 0 does not mean the caches are fresh - stale caches appear only as Notes.
- With no engine present, errors inside formulas that have no cached value (fresh
  openpyxl output) cannot be seen, because the scan only reads cached values.

It works on macOS, Linux, and Windows, and needs no LibreOffice guard in front
of it.

## Formula verification checklist

Essential checks:

- [ ] **Spot-check references**: verify 2-3 sample references return the correct
  values before building the full model.
- [ ] **Column mapping**: confirm the column letters. 1-based column 64 is `BL`,
  not `BK` (`openpyxl.utils.get_column_letter(64) == 'BL'`, measured).
- [ ] **Row offset**: Excel rows are 1-based and pandas positions are 0-based.
  With one header row in Excel row 1, DataFrame position `i` sits on Excel row
  `i + 2` (measured: position 5 -> row 7). Without a header (`header=None`) it is
  `i + 1`.

Common pitfalls:

- [ ] **NaN**: test for nulls with `pd.notna()`.
- [ ] **Far-right columns**: fiscal-year data often lives in columns 50+.
- [ ] **Multiple matches**: search every occurrence, not just the first.
- [ ] **Division by zero**: check denominators before using `/` in a formula
  (`#DIV/0!`).
- [ ] **Wrong references**: confirm each reference hits the intended cell
  (`#REF!`).
- [ ] **Cross-sheet references**: use the `Sheet1!A1` form when linking sheets.

Testing strategy:

- [ ] **Start small**: try formulas on 2-3 cells before applying them broadly.
- [ ] **Verify dependencies**: every referenced cell exists.
- [ ] **Edge cases**: zero, negative, and very large values.

### Checking for formula errors

Primary check - no LibreOffice needed:

```bash
officecli view output.xlsx issues --json
```

It reports `#REF!` / `#VALUE!` / `#NAME?` / `#DIV/0!` and the
`formula_cache_stale` subtype (a `cachedValue` that disagrees with the
evaluator). Fix what it lists, re-write the affected formulas, re-check.

## Reading scripts/recalc.py output

The script prints plain text, not JSON. Its shape is:

- The first line is one of `Recalc engine: officecli`,
  `Recalc engine: LibreOffice (officecli not on PATH)`, or `Recalc engine: none`.
- On the officecli branch it then prints the command it ran
  (`  $ officecli view <path> issues --json`) and
  `  officecli evaluated formulas: <n> error(s), <m> note(s)`.
- The scan line is `openpyxl scan (<filename>): <n> cell(s) with an error
  string`, followed by one `  <Sheet>!<Cell>  <token>` line per hit.
- The verdict is either `FOUND <n> Excel error cell(s):` with one
  `  <Sheet>!<Cell>  <token>  [<source>]` line per cell (source is `officecli` or
  `openpyxl`), or `No Excel errors found.`.
- An optional trailer is `Notes (not counted as errors):` followed by
  `  <Sheet>!<Cell>: <subtype> - <message>` lines.

A run that finds an error (officecli 1.0.152; `Data!B1` held `=A1/A2` with
`A2 = 0`) exits 1 and prints:

```text
Recalc engine: officecli
  $ officecli view t.xlsx issues --json
  officecli evaluated formulas: 1 error(s), 0 note(s)
openpyxl scan (t.xlsx): 0 cell(s) with an error string

FOUND 1 Excel error cell(s):
  Data!B1  #DIV/0!  [officecli]
```

A file whose only problem is a stale cache exits 0 and ends:

```text
No Excel errors found.

Notes (not counted as errors):
  Sheet!B10: formula_cache_stale - Cached value disagrees with re-evaluation (cachedValue="0", computedValue="5"). Open in Excel to refresh, or call set to overwrite the formula.
```

## Raw XML editing with the shared office scripts

Reach for this only for changes that officecli and openpyxl cannot express;
prefer officecli. The scripts live in `scripts/office/`. Work in this order:
unpack -> edit the XML by hand -> pack -> validate the packed file -> then
`officecli view <file> issues --json`.

- `python scripts/office/unpack.py <office_file> <output_dir> [--no-merge-runs] [--no-simplify-redlines]`
  Accepts `.docx`, `.pptx`, or `.xlsx`. It extracts the ZIP and pretty-prints
  every `.xml`/`.rels` part. The two flags are DOCX-only and do nothing for a
  workbook.
- `python scripts/office/pack.py <input_dir> <output_file> [--no-repair]`
  The output suffix must be `.docx`, `.pptx`, or `.xlsx`; it writes a deflated
  ZIP. The default repairs are Word-specific (w14/w15/w16 `paraId`/`textId`/
  `durableId` clamped to `0x7FFFFFFF`, and `xml:space="preserve"` set on `<w:t>`
  runs with edge whitespace), so on a workbook they are a no-op; `--no-repair`
  skips them.
- `python scripts/office/validate.py <path> [-v]`
  `<path>` is an unpacked directory or a packed `.docx`/`.pptx`/`.xlsx`. Layer 1
  checks lxml well-formedness of every `.xml`/`.rels` part (`-v` lists each part
  that parses). Layer 2 runs `officecli validate <file>` for the OpenXML schema
  check, but only for a PACKED file and only when officecli is on PATH; a
  directory reports `skipped (pack first to run the schema check)`. Exit is 0
  only if every layer that ran passed; a schema failure exits 1.

All three scripts exit 1 on error.

OOXML detail: a formula cell stores its formula in `<f>` and its cached value in
`<v>`. Editing an input cell by hand does not update the `<v>` of the formulas
that depend on it, so re-`set` the affected formula cells afterwards.

## Best practices

### Library selection

- **pandas**: data analysis, bulk operations, and simple data export.
- **openpyxl**: complex formatting, formulas, and Excel-specific features.

### Working with openpyxl

- Cell indices are 1-based: `row=1, column=1` is `A1`.
- Read cached calculated values with `load_workbook(path, data_only=True)`.
- Warning: saving a workbook that was opened with `data_only=True` replaces its
  formulas with values - the formulas are lost for good.
- For large files, `read_only=True` to read and `write_only=True` to write.
- Measured: `data_only=True` returns `None` for a formula cell that openpyxl
  itself wrote (no cached value exists).
- Formulas are preserved but not evaluated - re-write each formula cell through
  `officecli set ... --prop formula="..."` to populate its cached value (see
  Verifying formula values)

### Working with pandas

- Pin dtypes to avoid inference problems: `pd.read_excel(path, dtype={'id': str})`.
- To read selected columns from large files: `pd.read_excel(path, usecols="A,C,E")`.
  For Excel column LETTERS use the comma-separated STRING form (ranges like
  `"A:E"` work too). A LIST such as `['A', 'C', 'E']` means column NAMES and
  raises `ValueError: Usecols do not match columns` unless the headers really are
  A/C/E (measured, pandas 3.0.6).
- Parse dates on read: `pd.read_excel(path, parse_dates=['order_date'])`.

## Code style

**Python you generate for workbook tasks (important):**

- Keep the code minimal and concise, with no unnecessary comments.
- No verbose variable names and no redundant operations.
- No unnecessary print statements.

**Inside the workbook itself:**

- Add cell comments on complex formulas and important assumptions.
- Document the source of every hardcoded value.
- Leave notes for key calculations and model sections.
