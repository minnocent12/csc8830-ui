# csc8830-ui

Canonical design system for the **CSc 8830 Computer Vision** course application.

This repository is the single source of truth for the application's visual language:

| File | Contents | Imports Streamlit |
|---|---|---|
| `tokens.py` | colors, typography, heading scale, layout widths, spacing, radii, borders, elevation, breakpoints, declared contrast pairs | no |
| `accessibility.py` | WCAG 2.2 contrast helpers | no |
| `theme.py` | the native Streamlit `[theme]` derived from tokens, rendered as `config.toml` text | no |
| `styles.py` | the small global stylesheet for gaps the native theme cannot cover, and `inject_global_styles()` | only inside that function |
| `version.py` | `KIT_VERSION` | no |

Shared Streamlit components will be added in a later phase.

## Streamlit compatibility

Every assignment requires `streamlit>=1.49,<2` at runtime. The theme alone would work on
1.47, but the assignment pages use `width="stretch"` on `st.image` and `st.dataframe`,
which arrived in 1.49. The theme emits only keys that exist in Streamlit 1.49 (a test holds
the 1.49 key list). Alert colors and metric font sizes are not theme keys at 1.49, so alerts
keep Streamlit's default colors and metric typography is set in CSS.

Module 4's test suite additionally needs `streamlit>=1.56,<2` in its `dev` extra, because
`AppTest.file_uploader` first shipped in 1.56. That is a test-only floor
(`STREAMLIT_UPLOAD_TEST_REQUIREMENT`), not a runtime requirement.

## Global styles

The native theme does most of the work. `styles.py` adds only these rules, documented in its
docstring with selector, reason, and fragility:

| Desired behavior | Native theme at 1.49? | CSS | Why |
|---|---|---|---|
| Orange primary buttons, focus, active widgets | yes (`primaryColor`) | no | |
| App, widget, sidebar backgrounds, text, links, borders | yes | no | |
| Fonts, heading sizes and weights, radii | yes | no | |
| Dataframe borders and header background | yes | no | |
| Content max width on wide monitors | no | yes | layout is otherwise edge to edge |
| Heading color darker than body text | no (one text color) | yes | hierarchy |
| Captions readable | no | yes | Streamlit fades captions with 60 percent opacity, below AA |
| Metric label and value typography | no (not a key at 1.49) | yes | |
| Consistent keyboard focus ring on links, buttons, tabs | partial | yes | |
| Alert (info, warning, success, error) colors | no (not a key at 1.49) | no | left at Streamlit defaults for now |

Selectors use plain tags, the `.stApp` root class, or `data-testid` hooks. Generated
`st-emotion-cache-*` class names and positional selectors are never used, and no control is
hidden or replaced.

## How the assignments use it

Each assignment (Module 2, 3, 4, 5-6) is its own independently submittable repository.
Those repositories never depend on this one at runtime:

- The kit is **vendored**: a copy of `src/csc8830_ui/` is placed in each assignment under
  `src/<module>/webapp/design/` and committed there.
- The kit uses only relative imports and the Python standard library, so the copy works under
  any parent package name without rewriting.
- A module cloned on its own runs without network access to this repository and without
  installing anything from it.

`scripts/vendor.py` does the copying and the parity checks. It expects this repository to
sit inside the course workspace next to the module folders:

```bash
python scripts/vendor.py check          # exit 1 if any copy or config.toml drifted
python scripts/vendor.py sync           # write package copies and config.toml files
python scripts/vendor.py sync module3   # one target only
```

It writes only the design package files and each launch context's
`.streamlit/config.toml`. It refuses to downgrade a newer copy, to overwrite local edits
to a same-version copy (unless `--force`), to touch extra files in a design package, to
replace a `config.toml` it did not generate, or to vendor anything containing em or en
dashes. Streamlit reads `config.toml` from the current directory and then from the
script's own directory, so each module repository, the workspace root, and the deployment
dashboard each carry an identical generated copy.

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

Tests use only the standard library and pytest; Streamlit is not needed to run them.
