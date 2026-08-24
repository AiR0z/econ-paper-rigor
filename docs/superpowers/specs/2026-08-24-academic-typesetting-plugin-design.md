# Academic Typesetting Plugin Design

## Purpose

Add a reusable personal Codex plugin for academic typesetting and connect its
formatting rules to `econ-paper-rigor`. The plugin must work across local
projects without external accounts, APIs, or background services.

## Scope

The plugin will format academic text using semantic Markdown and LaTeX and
support conversion to DOCX through the existing Pandoc toolchain. It will
cover:

- headings, paragraphs, lists, quotations, bold, and italics;
- inline and display mathematics;
- tables, notes, citations, and cross-references;
- figure and table captions;
- formatting-preserving Markdown, LaTeX, and DOCX output;
- post-export checks for missing text, broken formulas, and lost structure.

It will not provide a graphical editor, alter prose merely to evade AI
detection, install a TeX distribution, or introduce a new external service.

## Structure

Create the personal marketplace plugin at
`C:\Users\Luka\plugins\academic-typesetting` and register it in
`C:\Users\Luka\.agents\plugins\marketplace.json`.

The plugin will contain one focused skill:

- `academic-typesetting`: applies semantic formatting conventions and selects
  the appropriate output path for Markdown, LaTeX, or DOCX.

Supporting references may define syntax and release checks. Scripts are added
only where deterministic validation is useful; the plugin will not duplicate
Pandoc.

## Integration

Add a concise formatting reference to `econ-paper-rigor`. Its `writing` and
`release` modes will use the same conventions for emphasis, equations,
tables, notes, citations, captions, and cross-references. The econometric skill
must remain usable if the personal plugin is unavailable; formatting rules
needed for article production therefore remain documented locally rather than
depending on cross-plugin invocation.

The standalone plugin provides the same capability to other projects.

## Output Rules

- Use formatting semantically, not decoratively.
- Preserve literal symbols and mathematical meaning during conversion.
- Prefer editable equations in DOCX when the converter supports them.
- Do not represent a formula as an image unless the user explicitly requests
  it or the target format makes editable mathematics impossible.
- Keep citations and references compatible with the manuscript's existing
  toolchain.
- Preserve an existing document's style unless the user requests a restyle.

## Failure Handling

If the requested output cannot preserve a feature, report the affected
elements and provide the closest editable representation. Do not silently
flatten equations, discard notes, or replace cross-references with fabricated
values.

## Verification

- Validate the plugin manifest and marketplace entry with the plugin-creator
  validators.
- Validate both skills with the skill validator.
- Use representative fixtures containing emphasis, inline and display math,
  a table, a note, a citation, and a cross-reference.
- Convert a fixture to DOCX and inspect document structure programmatically.
- Render the DOCX and inspect the result visually when the available local
  document toolchain permits it.
- Run the existing `econ-paper-rigor` test suite after integration.

## Distribution

The personal marketplace makes the plugin available across local Codex
projects. Installing or refreshing the plugin must not modify or restart other
running projects.
