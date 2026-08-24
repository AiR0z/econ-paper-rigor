# Production and References

Use this reference for lawful source acquisition, bibliographic records, DOCX
production, and release checks.

## Full text

Automatic retrieval is limited to lawful, unauthenticated public HTTPS files.
Validate the network target, redirects, size, media type, PDF signature,
destination containment, and no-overwrite behavior. Record provenance and a
hash. A successful download establishes access only.

Search lawful open-access routes, repositories, preprints, accepted
manuscripts, and author or institutional pages. If a promising paper still has
no inspectable full text, show a `Full text requested` list containing:

- best available citation and DOI or canonical landing page;
- version sought and lawful routes checked;
- one metadata-calibrated sentence on potential relevance;
- evidence state `UNVERIFIED` and a statement that it was not used as
  substantive support;
- a request for a legitimately accessible full text in any readable format the
  user can provide, including PDF, HTML, DOCX, Markdown, plain text, or page
  images.

After inspection, record the exact version and a reproducible locator: page for
paginated files or scans, and stable heading, section, paragraph, or anchor for
web and text formats. If reliable extraction or location is impossible, keep
that limitation explicit. Do not create a separate progress artifact unless
the user asks to save the list.

## Zotero

Use official Zotero interfaces only. Read-only status and search do not need
per-call confirmation. A write in v0.1 may create exactly one bibliographic
item and requires a dry-run payload, deterministic digest, exact duplicate
check, current library version, and explicit confirmation of that plan.

Do not upload attachments or expose update, delete, trash, purge, bulk,
arbitrary bridge, or direct database operations. Recheck the digest,
duplicates, and library version immediately before creation. Keep credentials
in process or user environment variables and headers, never URLs, files,
receipts, or output.

## Manuscripts and DOCX

Use Markdown as the canonical source for new text-first manuscripts. If an
existing complex DOCX carries authoritative layout, tracked changes, fields,
or comments, keep it Word-native and avoid lossy round trips.

Generate DOCX through an argument-list subprocess, cite processing, optional
bibliography and CSL inputs, and the supplied reference DOCX. Never overwrite
an existing output; select a versioned name. Validate the OOXML structure,
record input and output hashes in a redacted adjacent receipt, render the result,
and inspect every page for clipping, broken tables, orphaned headings, and
spacing or cross-reference problems.

## Release check

Reconcile headline claims with the evidence ledger, citations with the
bibliography, and text references with tables and figures. Report exactly which
mechanical and visual checks ran. Technical success does not certify scientific
truth or publication readiness.
