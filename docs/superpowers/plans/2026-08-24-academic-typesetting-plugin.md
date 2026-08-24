# Academic Typesetting Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create and install a global personal plugin for academic formatting, then integrate the same rules into `econ-paper-rigor`.

**Architecture:** A standalone marketplace plugin supplies a reusable `academic-typesetting` skill to all local Codex projects. `econ-paper-rigor` retains a compact local formatting reference so its writing and release modes do not depend on cross-plugin invocation.

**Tech Stack:** Codex personal marketplace, Markdown, LaTeX math, Pandoc 3.10.2, Python `unittest`, OOXML/DOCX, plugin and skill validators.

**Spec:** `docs/superpowers/specs/2026-08-24-academic-typesetting-plugin-design.md`

## Global Constraints

- The plugin must work across local projects without external accounts, APIs, or background services.
- Do not provide a graphical editor, alter prose merely to evade AI detection, install a TeX distribution, or introduce a new external service.
- Preserve existing document styles unless the user requests a restyle.
- Keep formulas editable in DOCX when the converter supports it; do not silently flatten equations.
- The econometric skill must remain usable if the personal plugin is unavailable.
- Installing or refreshing the plugin must not modify or restart other running projects.

---

### Task 1: Personal plugin contract

**Files:**
- Create: `C:\Users\Luka\plugins\academic-typesetting\.codex-plugin\plugin.json`
- Create: `C:\Users\Luka\plugins\academic-typesetting\skills\academic-typesetting\SKILL.md`
- Create: `C:\Users\Luka\plugins\academic-typesetting\skills\academic-typesetting\references\formatting-contract.md`
- Create: `C:\Users\Luka\plugins\academic-typesetting\tests\test_contract.py`
- Modify: `C:\Users\Luka\.agents\plugins\marketplace.json` through the scaffold helper only

**Interfaces:**
- Consumes: the personal marketplace convention and the local Pandoc executable.
- Produces: plugin id `academic-typesetting`, skill id `academic-typesetting`, and a validated personal marketplace entry.

- [ ] **Step 1: Scaffold the plugin and personal marketplace entry**

Run:

```powershell
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\plugin-creator\scripts\create_basic_plugin.py' `
  academic-typesetting --with-skills --with-marketplace
```

Expected: the plugin root and `C:\Users\Luka\.agents\plugins\marketplace.json` are created; the marketplace entry has installation `AVAILABLE`, authentication `ON_INSTALL`, and category `Productivity`.

- [ ] **Step 2: Write the failing contract test**

Create `tests/test_contract.py` with a `unittest.TestCase` that loads the manifest, marketplace, skill, and reference and asserts:

```python
self.assertEqual(manifest["name"], "academic-typesetting")
self.assertEqual(manifest["version"], "0.1.0")
self.assertEqual(manifest["skills"], "./skills/")
self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
self.assertIn("inline and display mathematics", skill.lower())
self.assertIn("**bold**", reference)
self.assertIn("$y_i = \\alpha + \\beta x_i + \\varepsilon_i$", reference)
self.assertNotIn("api key", (skill + reference).lower())
```

- [ ] **Step 3: Run the test to verify the incomplete scaffold fails**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s 'C:\Users\Luka\plugins\academic-typesetting\tests' -v
```

Expected: FAIL because the final skill, reference, and manifest metadata do not exist yet.

- [ ] **Step 4: Write the minimal manifest and skill**

Set the manifest to version `0.1.0`, author and developer `Luka Ilich (MGIMO)`, skills path `./skills/`, display name `Academic Typesetting`, category `Productivity`, capability `Write`, and a description limited to semantic academic formatting.

Write `SKILL.md` with frontmatter name `academic-typesetting`. Route requests by target format, load `references/formatting-contract.md`, preserve an existing style by default, use semantic emphasis, keep formulas editable, retain citations and cross-references, and report any conversion loss.

Write `formatting-contract.md` with exact examples for:

```markdown
**bold**
*italics*
$y_i = \alpha + \beta x_i + \varepsilon_i$
$$
\widehat{\beta}=(X'X)^{-1}X'y
$$
[^identification]: Identification requires the stated assumptions.
```

Also specify headings, quotations, lists, tables, captions, citation keys, notes, literal symbols, Markdown-to-DOCX conversion, and post-export inspection.

- [ ] **Step 5: Run contract and schema validation**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s 'C:\Users\Luka\plugins\academic-typesetting\tests' -v
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\skill-creator\scripts\quick_validate.py' `
  'C:\Users\Luka\plugins\academic-typesetting\skills\academic-typesetting'
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py' `
  'C:\Users\Luka\plugins\academic-typesetting'
```

Expected: all commands exit 0.

- [ ] **Step 6: Create a local source commit**

Run inside `C:\Users\Luka\plugins\academic-typesetting`:

```powershell
git init
git add .codex-plugin skills tests
git commit -m "feat: add academic typesetting plugin"
```

Expected: one local commit containing only plugin source and tests; the personal marketplace file remains outside this repository.

---

### Task 2: Econometric-agent integration

**Files:**
- Create: `references/typesetting-and-formatting.md`
- Create: `tests/test_typesetting_contract.py`
- Modify: `SKILL.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the conventions documented by the standalone `academic-typesetting` skill.
- Produces: a dependency-free formatting route for `econ-paper-rigor` writing and release modes.

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_typesetting_contract.py` with assertions that:

```python
self.assertIn("references/typesetting-and-formatting.md", skill)
self.assertIn("writing", skill)
self.assertIn("release", skill)
self.assertIn("**bold**", reference)
self.assertIn("inline and display mathematics", reference.lower())
self.assertIn("editable equations", reference.lower())
self.assertIn("conversion loss", reference.lower())
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest tests.test_typesetting_contract -v
```

Expected: FAIL because the reference and routing entry are absent.

- [ ] **Step 3: Add the formatting reference and route**

Add `references/typesetting-and-formatting.md` with the same semantic emphasis, math, table, note, citation, caption, cross-reference, preservation, fallback, and release rules used by the plugin.

Update `SKILL.md` so `writing` and `release` work load this reference when formatting or exporting a manuscript. Add one README capability line for semantic academic formatting and editable equations; do not add a required plugin dependency.

- [ ] **Step 4: Run the integration test and full suite**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest tests.test_typesetting_contract -v
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s tests -v
```

Expected: the new test and all existing tests pass.

- [ ] **Step 5: Commit the integration**

Run:

```powershell
git add SKILL.md README.md references/typesetting-and-formatting.md tests/test_typesetting_contract.py
git commit -m "feat: add academic typesetting guidance"
```

---

### Task 3: DOCX preservation fixture

**Files:**
- Create: `C:\Users\Luka\plugins\academic-typesetting\tests\fixtures\academic-formatting.md`
- Create: `C:\Users\Luka\plugins\academic-typesetting\tests\fixtures\references.bib`
- Create: `C:\Users\Luka\plugins\academic-typesetting\tests\test_docx_conversion.py`
- Generate, do not commit: `C:\Users\Luka\plugins\academic-typesetting\.test-output\academic-formatting.docx`

**Interfaces:**
- Consumes: Pandoc at `C:\Users\Luka\AppData\Local\Pandoc\pandoc.exe`.
- Produces: evidence that emphasis, equations, tables, notes, and citations survive DOCX conversion as editable OOXML structures.

- [ ] **Step 1: Write the failing conversion test and fixture**

The Markdown fixture must contain a heading, `**bold**`, `*italics*`, inline and display math, a pipe table with caption, a footnote, and `[@smith2020]`. The bibliography must define `smith2020` as an article.

The test must run Pandoc with `--from markdown+tex_math_dollars`, `--citeproc`, and `--bibliography`; open the generated DOCX as ZIP; and assert that the OOXML contains `w:b`, `w:i`, `m:oMath`, `w:tbl`, a footnote part, and rendered Smith citation text.

- [ ] **Step 2: Run the conversion test**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s 'C:\Users\Luka\plugins\academic-typesetting\tests' -p 'test_docx_conversion.py' -v
```

Expected on the first run: FAIL if any expected structure or fixture detail is missing.

- [ ] **Step 3: Correct only the conversion syntax needed for editable output**

Use this argument list in the test so math produces Word OMML, emphasis
produces run properties, the table remains a Word table, the note remains a
Word footnote, and citeproc renders the citation:

```python
command = [
    r"C:\Users\Luka\AppData\Local\Pandoc\pandoc.exe",
    str(fixture),
    "--from", "markdown+tex_math_dollars+footnotes+pipe_tables",
    "--to", "docx",
    "--citeproc",
    "--bibliography", str(bibliography),
    "--output", str(output),
]
subprocess.run(command, check=True, capture_output=True, text=True)
```

Do not replace formulas with images.

- [ ] **Step 4: Re-run the conversion test and render the DOCX**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s 'C:\Users\Luka\plugins\academic-typesetting\tests' -p 'test_docx_conversion.py' -v
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  'C:\Users\Luka\.codex\plugins\cache\openai-primary-runtime\documents\26.819.11345\skills\documents\render_docx.py' `
  'C:\Users\Luka\plugins\academic-typesetting\.test-output\academic-formatting.docx' `
  --output_dir 'C:\Users\Luka\plugins\academic-typesetting\.test-output\rendered'
```

Expected: PASS and one or more PNG pages. Inspect every page for visible bold and italics, legible equations, an intact table, footnote placement, citation rendering, clipping, and overflow.

- [ ] **Step 5: Commit the fixture and test, excluding generated output**

Add `.test-output/` to the plugin `.gitignore`, then run:

```powershell
git add .gitignore tests
git commit -m "test: verify DOCX formatting preservation"
```

---

### Task 4: Installation and final verification

**Files:**
- Modify mechanically: `C:\Users\Luka\plugins\academic-typesetting\.codex-plugin\plugin.json` cachebuster suffix
- Verify: `C:\Users\Luka\.agents\plugins\marketplace.json`

**Interfaces:**
- Consumes: validated plugin source and marketplace name `personal`.
- Produces: an installed personal plugin discoverable by Codex in new tasks.

- [ ] **Step 1: Validate the marketplace name and add a cachebuster**

Run:

```powershell
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\plugin-creator\scripts\read_marketplace_name.py'
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\plugin-creator\scripts\update_plugin_cachebuster.py' `
  'C:\Users\Luka\plugins\academic-typesetting'
```

Expected: marketplace name `personal`; the manifest version matches
`^0\.1\.0\+codex\.local-\d{8}-\d{6}$` and contains exactly one cachebuster
suffix.

- [ ] **Step 2: Install from the personal marketplace**

Run:

```powershell
codex plugin add academic-typesetting@personal
```

Expected: exit 0 without modifying or restarting any other project.

- [ ] **Step 3: Run all validators and tests again**

Run:

```powershell
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s 'C:\Users\Luka\plugins\academic-typesetting\tests' -v
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\skill-creator\scripts\quick_validate.py' `
  'C:\Users\Luka\plugins\academic-typesetting\skills\academic-typesetting'
& 'C:\Users\Luka\.agents\skills\econ-paper-rigor\.venv\Scripts\python.exe' `
  'C:\Users\Luka\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py' `
  'C:\Users\Luka\plugins\academic-typesetting'
Push-Location 'C:\Users\Luka\.agents\skills\econ-paper-rigor'
& 'C:\Users\Luka\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
  -m unittest discover -s tests -v
Pop-Location
```

Expected: every command exits 0; generated artifacts remain excluded from Git.

- [ ] **Step 4: Verify Git state and commit the cachebuster**

Run:

```powershell
git -C 'C:\Users\Luka\plugins\academic-typesetting' status --short
git -C 'C:\Users\Luka\.agents\skills\econ-paper-rigor' status --short
git -C 'C:\Users\Luka\plugins\academic-typesetting' add .codex-plugin/plugin.json
git -C 'C:\Users\Luka\plugins\academic-typesetting' commit -m "chore: refresh Codex plugin cache"
```

Expected: the plugin cachebuster is committed locally and the econometric repository is clean.

- [ ] **Step 5: Verify pickup boundary**

Run `codex plugin list` and confirm `academic-typesetting@personal` is present. Record that a newly opened Codex task is the safe boundary for testing skill discovery; do not restart the current task or other applications.
