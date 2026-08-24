# Econ Paper Rigor

Version: v0.1

`econ-paper-rigor` is a personal Codex skill for careful work on econometric
articles. It helps assess data feasibility, structure literature evidence,
review identification and inference, revise claims, prepare referee reports,
and produce versioned research artifacts.

v0.1 is the first iteration and will be refined through use on real projects.

Core capabilities:

- an early data-feasibility checkpoint before unsupported empirical drafting;
- literature discovery with claim-level evidence tracking;
- econometric design and referee-style review;
- bounded drafting that preserves the supported claim ceiling;
- guarded public-document retrieval and DOCX output;
- semantic academic formatting through the standalone `academic-typesetting`
  plugin when available, with a compact editable-document fallback.

Literature discovery is provider-neutral. A user-configured SerpApi MCP may be
used as an optional secondary Google Scholar discovery source; it is never a
required dependency or a substitute for reading the original work.

Invoke the skill explicitly as `$econ-paper-rigor`. Install or clone it at the
user-scope skill path, for example `~/.agents/skills/econ-paper-rigor`.

The skill does not infer that unavailable data or literature does not exist. It
reports what was checked, marks uninspected full text as `UNVERIFIED`, never
stores credentials, and does not overwrite research outputs silently.

## Scope choices

- **Lean:** omitted because theorem-prover projects have distinct dependencies,
  semantics, and verification workflows better handled by a dedicated skill.
- **Formal proofs:** omitted because model reasoning about equations is not a
  formal certificate and should not be presented as one.
- **Stata-specific processes:** omitted to keep the skill usable with Stata, R,
  Python, Julia, and project-specific toolchains on equal terms.
- **LLM experiments and human studies:** omitted because they require separate
  ethics, privacy, participant, reliability, and model-variance controls.
- **Automatic end-to-end pipeline:** omitted so each material transition in a
  research project remains visible and under the user's authority.
- **Zotero Management Bridge:** omitted in favor of narrow official interfaces,
  reducing mutation surface and avoiding an extra trusted component.
- **Heavy internal progress files:** omitted because they create maintenance
  overhead without adding scientific provenance; only research artifacts and
  compact receipts are retained when needed.

## Acknowledgements

Thanks to Luka Ilich (MGIMO) and to the authors and maintainers of
[analysis-methods](https://github.com/wendyzhao530/analysis-methods),
[research-literature](https://github.com/wendyzhao530/research-literature),
[econometrics-research](https://github.com/wendyzhao530/econometrics-research),
[econometrics-stata](https://github.com/wendyzhao530/econometrics-stata),
[EconAgentSkills](https://github.com/JonasWeinert/EconAgentSkills),
[Auto-Empirical-Research-Skills_harness](https://github.com/Theislandreserve/Auto-Empirical-Research-Skills_harness),
and [econometrics-skills](https://www.skills.sh/wentorai/research-plugins/econometrics-skills)
for useful public reference material. `econ-paper-rigor` is an independent
implementation.
