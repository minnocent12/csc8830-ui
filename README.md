# csc8830-ui

Canonical design system for the **CSc 8830 Computer Vision** course application.

This repository is the single source of truth for the application's visual language. It
currently contains design tokens only (colors, typography, spacing, shape, borders,
elevation, breakpoints) plus WCAG contrast helpers. Shared CSS and Streamlit components
will be added in later phases.

## How the assignments use it

Each assignment (Module 2, 3, 4, 5-6) is its own independently submittable repository.
Those repositories never depend on this one at runtime:

- The kit is **vendored**: a copy of `src/csc8830_ui/` is placed in each assignment under
  `src/<module>/webapp/design/` and committed there.
- The kit uses only relative imports and the Python standard library, so the copy works under
  any parent package name without rewriting.
- A module cloned on its own runs without network access to this repository and without
  installing anything from it.

## Versioning

`csc8830_ui.version.KIT_VERSION` follows `MAJOR.MINOR.PATCH`. Every vendored copy carries
the version it was taken from, so a copy can be compared with the canonical source. All
copies (the four assignments and the shared dashboard) should be upgraded together to avoid
mixed versions on the public dashboard.

- Patch: a value retuned without changing any token name.
- Minor: tokens or helpers added.
- Major: tokens renamed or removed.

## Brand direction

The visible identity is **CSc 8830 Computer Vision**. The design language borrows from
functional enterprise and retail operations dashboards: one strong orange for interaction,
clear hierarchy, compact forms, practical cards, clean tables, and status chips. It has no
affiliation with any company and uses no third-party logo, wordmark, or trade dress.

- Brand orange `#F96302` is used for accents, selected states, and fills that carry dark
  text.
- Primary actions, focus rings, and active borders use the darker `#C2410C`, because white
  text on `#F96302` reaches only 3.08:1.

## Accessibility

Every foreground and background pairing the kit relies on is listed in
`tokens.CONTRAST_PAIRS` with its intended use, and the tests verify it against WCAG 2.2 AA:

| Use | Minimum ratio | Examples |
|---|---|---|
| Normal text | 4.5:1 | body text, captions, CTA labels, status chip text |
| Large text | 3.0:1 | 24px regular or 18.66px bold and larger |
| Non-text | 3.0:1 | focus rings, input outlines, active state indicators |
| Decorative | none | card separators, accents that carry no information |

Status is never communicated by color alone; later components pair color with a text label.

## Writing rule

No em dash or en dash characters anywhere in this repository, because the kit is vendored
into Module 3, which prohibits them. A test enforces this.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```
