# Econometric Review

Use this reference for feasibility assessments, empirical designs, result
audits, and interpretation.

## Mandatory data-feasibility checkpoint

Run this checkpoint when an empirical paper begins from a title, topic, or
proposed claim and its data basis has not already been established. Date the
assessment and inspect only sources currently available within the user's
authority: project files, lawful public sources, configured read-only
integrations, and data the user describes but has not supplied.

Report:

- the proposed question and implied unit of observation;
- required outcomes, exposures, controls, identifiers, and timing variables;
- population, geography, period, frequency, historical availability, and join
  keys;
- sources checked, access and licensing conditions, provenance, and whether the
  inputs can be reproduced;
- usable, inaccessible, unavailable, and unknown inputs;
- measurement, selection, merge, coverage, cost, or collection limitations;
- the strongest supportable claim class;
- one recommendation: continue, continue with explicit limitations, reframe
  the title/question/design, or request specific data or access.

Say `not located in checked sources` unless non-existence is independently
known. Never substitute synthetic, illustrative, or inferred values for
observed evidence. Present the assessment and stop for the user's decision
before detailed design, estimation, or results drafting. Do not create a
progress file unless the user explicitly requests an artifact.

## Empirical chain

Audit the work in this order:

1. research question and target estimand;
2. concept-to-variable measurement map;
3. sample construction and missingness;
4. estimator and functional form;
5. uncertainty and dependence structure;
6. identification assumptions;
7. diagnostics and falsification tests;
8. robustness tied to specific threats;
9. external validity and supported interpretation.

State the observation level, treatment or exposure timing, comparison group,
weights, clustering level, fixed effects, transformations, and estimand implied
by heterogeneous effects. Check whether standard errors reflect the assignment
or dependence process. Treat robustness as threat-specific evidence, not a
count of alternative regressions.

For descriptive or predictive work, replace causal language with the relevant
measurement, validation, leakage, drift, and generalization checks. For
structural work, separate calibration, estimation, fit, and identifying
restrictions. For accounting work, distinguish identities from behavioral
interpretations.

Conclude with what the design supports, what remains uncertain, and the smallest
change that would materially improve credibility.
