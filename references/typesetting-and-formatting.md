# Typesetting and Formatting

Use this reference for semantic academic formatting in `writing` and `release`
work. It is self-contained guidance: do not require the standalone
`academic-typesetting` plugin or any other plugin.

Apply these conventions while preserving the document's existing style unless a
new style is requested.

## Structure and emphasis

Use headings hierarchically: `#` for the document title, `##` for major
sections, and `###` for subsections. Do not skip heading levels.

Use semantic emphasis rather than visual substitutions:

```markdown
**bold**
*italics*
```

Use block quotations for quoted material:

```markdown
> A quotation retains its source attribution in the surrounding text or citation.
```

Use ordered lists only for sequences and unordered lists for sets:

```markdown
1. First step
2. Second step

- Assumption one
- Assumption two
```

## Mathematics and literal symbols

Keep formulas in editable mathematics syntax. Use inline and display mathematics
for, respectively, short expressions and standalone derivations:

```markdown
$y_i = \alpha + \beta x_i + \varepsilon_i$
$$
\widehat{\beta}=(X'X)^{-1}X'y
$$
```

Do not replace editable equations with rendered images. Preserve literal
symbols exactly when they carry meaning; escape Markdown punctuation only when
it would otherwise be parsed as formatting.

## Tables, captions, citations, and notes

Use pipe tables with a header row and alignment only when it communicates
numeric or textual structure:

```markdown
| Variable | Estimate |
|:---------|---------:|
| Income   | 0.12     |
```

Place captions adjacent to their tables or figures. Retain labels used by
cross-references and do not replace labels with plain text. Preserve standard
citation keys exactly, for example `[@smith2024]`. Cross-reference syntax is
target-specific: detect the source syntax and retain it unchanged rather than
converting a cross-reference into citation syntax.

Use footnotes for explanatory notes rather than source citations that belong
in the bibliography:

```markdown
[^identification]: Identification requires the stated assumptions.
```

## LaTeX and editable `.tex` source

For a LaTeX target, write editable `.tex` source with semantic sectioning and
native commands. Use `\section{...}` and its hierarchy for structure,
`\textbf{...}` and `\emph{...}` for emphasis, `$...$` for inline math, and
`\[...\]` or the manuscript's existing equation environment for display math.
Use native tables and captions, preserve `\label{...}`/`\ref{...}` pairs, keep
citations compatible with the manuscript's bibliography toolchain, and use
`\footnote{...}` for explanatory notes.

Creating editable `.tex` source does not require installing a TeX distribution
or running compilation. Compile only when the requester separately asks for a
compiled artifact and an existing toolchain is available.

## Conversion, preservation, and fallback

Keep Markdown as the canonical source for new text-first manuscripts. For DOCX
output, convert with the local Pandoc executable. When an existing DOCX
supplies the requested styles, use it as Pandoc's reference document:

```powershell
pandoc manuscript.md --reference-doc existing-style.docx -o manuscript.docx
```

If an existing complex DOCX carries authoritative layout, tracked changes,
fields, or comments, keep it Word-native and avoid a lossy round trip. For
another editable target, retain the same semantic structure and state any
target-specific limitation before conversion. If the target cannot preserve an
element, retain the canonical source or the Word-native document as the
fallback; do not silently substitute a visually similar but non-editable form.

Never overwrite an existing output: create a versioned output name. Retain the
source alongside the export when the requester permits it.

## Release inspection

After export, inspect headings, emphasis, equations, quotations, lists, tables,
captions, citation keys, notes, and cross-references. Render the result and
inspect every page for clipping, broken tables, orphaned headings, spacing, and
cross-reference problems. Report any conversion loss, unsupported formatting,
changed references, or formulas requiring manual review.

For release, reconcile text references with tables and figures, citations with
the bibliography, and headline claims with the evidence ledger. State exactly
which mechanical and visual checks ran. Technical success does not certify
scientific truth or publication readiness.
