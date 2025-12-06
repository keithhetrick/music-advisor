# MD → PDF Converter (ReportLab)

**Purpose:** Convert a single Markdown file into a clean, printable PDF with optional, controllable page breaks.

**What it does:** Reads your .md, lays out title (H1), section headers (H2), body text, bullets, and quotes; writes a .pdf with your chosen paper size and margins. No internet required.

**Page breaks:**

- Auto break before each H2 (after the first) with `--pagebreak h2`.
- Force breaks before specific headings with repeatable `--break-before "<regex>"` flags.
- Insert manual breaks anywhere by adding `[[PAGEBREAK]]` in your Markdown.

**Inputs/Outputs:**

- **Input:** path to the Markdown file (e.g., `docs/Input.md`).
- **Output:** path to the PDF file (e.g., `out/Output.pdf`).

**Requirements:** Python 3.x, `reportlab` (installed in a virtualenv is recommended). Runs fully local.

**Basic usage:** Activate your venv, then run the script with input, output, and any options (see commands below).

**What gets converted:** H1/H2 headings, paragraphs, bullets, and blockquotes are rendered; inline code/links are preserved as text. Inline images are not handled by this script; keep it for text-first reports.

---

## MD → PDF Converter — Commands Only

### macOS / Linux

**Create workspace:**

- `mkdir -p ~/cif_publishing && cd ~/cif_publishing`
- `python -m venv venv`
- `source venv/bin/activate`
- `pip install reportlab markdown`
- `mkdir -p docs out`

**Run converter (auto page break before each `##`):**

- `python md_to_pdf_reportlab.py docs/Input.md out/Output.pdf --pagesize LETTER --margin 0.9in --pagebreak h2`

**Run with custom paper size/margins:**

- `python md_to_pdf_reportlab.py docs/Input.md out/Output.pdf --pagesize A4 --margin 0.75in`

**Force breaks before specific sections (regex; repeat flag as needed):**

- `python md_to_pdf_reportlab.py docs/Input.md out/Output.pdf --break-before "^##\s+How to read HCI$" --break-before "^##\s+Typical workflows$"`

**(Optional) Make script executable + run directly:**

- `chmod +x md_to_pdf_reportlab.py`
- `./md_to_pdf_reportlab.py docs/Input.md out/Output.pdf --pagebreak h2`

**(Optional) Quick alias:**

- `echo "alias md2pdf='python ~/cif_publishing/md_to_pdf_reportlab.py'" >> ~/.zshrc && source ~/.zshrc`
- `md2pdf docs/Input.md out/Output.pdf --pagebreak h2`

**Deactivate venv:**

- `deactivate`

---

### Windows (PowerShell)

**Create workspace:**

- `mkdir $HOME\cif_publishing; cd $HOME\cif_publishing`
- `python -m venv venv`
- `.\venv\Scripts\Activate.ps1`
- `pip install reportlab markdown`
- `mkdir docs, out`

**Run converter (auto page break before each `##`):**

- `python .\md_to_pdf_reportlab.py .\docs\Input.md .\out\Output.pdf --pagesize LETTER --margin 0.9in --pagebreak h2`

**Run with custom paper size/margins:**

- `python .\md_to_pdf_reportlab.py .\docs\Input.md .\out\Output.pdf --pagesize A4 --margin 0.75in`

**Force breaks before specific sections (regex; repeat flag as needed):**

- `python .\md_to_pdf_reportlab.py .\docs\Input.md .\out\Output.pdf --break-before "^##\s+How to read HCI$" --break-before "^##\s+Typical workflows$"`

**Deactivate venv:**

- `deactivate`
