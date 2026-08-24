---
name: econ-paper-rigor
description: "Use only when explicitly invoked as $econ-paper-rigor for literature, empirical design, writing, review, or release work on an econometric article."
---

# Econ Paper Rigor

State the requested deliverable and choose one primary mode: `literature`,
`empirical`, `writing`, `review`, or `release`. Keep bounded requests bounded.
Preserve the project's existing canonical manuscript and toolchain.

For an empirical paper that starts from a title, topic, or proposed claim
without an established data basis, perform the data-feasibility checkpoint in
`references/econometric-review.md`. Report the dated assessment and pause for
the user's choice before detailed design, estimation, or results drafting.

Load only the references needed for the current deliverable:

- Evidence, literature discovery, claims, and identification:
  `references/evidence-and-identification.md`
- Data feasibility and econometric design or audit:
  `references/econometric-review.md`
- Drafting, revision, and referee reports:
  `references/writing-and-referee.md`
- Source acquisition, DOCX, and release checks:
  `references/production-and-references.md`

For manuscript formatting or editable export, use `$academic-typesetting` when
it is available. Otherwise preserve existing styles and use semantic headings,
emphasis, quotations, lists, tables and captions, citations, notes, editable
mathematics, citation keys, and target-specific cross-references. Keep complex
DOCX files Word-native; use Pandoc only for acceptable text-first conversions.
For editable LaTeX, preserve semantic `.tex` structure and compile only when
separately requested with an existing toolchain. Inspect exports for conversion
loss.

Before substantive drafting, state the strongest claim class supported by the
available evidence. Do not turn missing evidence into negative evidence, and
do not treat metadata, snippets, or retrieval as claim verification.

Keep Lean and formal proofs, Stata-specific workflows, LLM or human-subject
experiments, automatic end-to-end execution, Zotero management bridges, and
heavy internal progress systems outside this skill.

At handoff, report the artifact produced, checks actually performed, the
evidence ceiling, unresolved issues, and decisions still required from the
user. Do not call a manuscript scientifically true, formally verified, or
publication-ready merely because technical checks passed.
