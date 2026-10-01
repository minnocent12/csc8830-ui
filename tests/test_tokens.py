"""Tests for the canonical CSc 8830 design tokens."""
from __future__ import annotations

import ast
import re
from dataclasses import fields
from pathlib import Path

import pytest

from csc8830_ui import (
    BORDERS,
    BREAKPOINTS,
    COLORS,
    CONTRAST_PAIRS,
    HEADINGS,
    KIT_VERSION,
    LAYOUT,
    RADII,
    SPACING,
    TYPOGRAPHY,
    ContrastUse,
    color_roles,
    contrast_ratio,
    relative_luminance,
)
from csc8830_ui.accessibility import MINIMUM_RATIO, is_hex_color
from csc8830_ui.tokens import BorderTokens, ColorTokens, TypographyTokens

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPO_ROOT / "src" / "csc8830_ui"
# Built from code points so this file itself stays free of the prohibited characters.
PROHIBITED_DASHES = {chr(0x2013): "en dash", chr(0x2014): "em dash"}

REQUIRED_COLOR_ROLES = {
    "brand_orange", "brand_orange_soft", "brand_orange_strong", "text_on_brand",
    "action_primary_bg", "action_primary_fg", "action_primary_hover",
    "app_background", "surface_primary", "surface_secondary", "border", "border_strong",
    "text_heading", "text_body", "text_muted", "text_disabled",
    "success", "success_soft", "warning", "warning_soft",
    "error", "error_soft", "info", "info_soft",
}
REQUIRED_TYPE_ROLES = {
    "app_title", "module_eyebrow", "page_title", "section_title", "subsection_title",
    "body", "body_small", "caption", "metric_label", "metric_value", "code",
}


# Version


def test_kit_version_is_semantic_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", KIT_VERSION)


# Colors


def test_required_color_roles_exist() -> None:
    assert REQUIRED_COLOR_ROLES <= set(color_roles())


def test_brand_orange_is_the_agreed_value() -> None:
    assert COLORS.brand_orange == "#F96302"
    assert COLORS.action_primary_bg == "#C2410C"


@pytest.mark.parametrize("role, value", sorted(color_roles().items()))
def test_every_color_is_opaque_hex(role: str, value: str) -> None:
    assert is_hex_color(value), role


@pytest.mark.parametrize("base", ["brand_orange", "success", "warning", "error", "info"])
def test_soft_variants_are_distinct_and_lighter(base: str) -> None:
    soft = getattr(COLORS, f"{base}_soft")
    assert soft != getattr(COLORS, base)
    assert relative_luminance(soft) > relative_luminance(getattr(COLORS, base))


def test_action_states_darken_progressively() -> None:
    steps = [COLORS.action_primary_bg, COLORS.action_primary_hover, COLORS.action_primary_pressed]
    luminances = [relative_luminance(c) for c in steps]
    assert luminances == sorted(luminances, reverse=True)
    assert len(set(steps)) == 3


def test_border_colors_reference_semantic_roles() -> None:
    roles = set(color_roles().values())
    for f in fields(BorderTokens):
        if f.name.startswith("color_") or f.name == "focus_ring_color":
            assert getattr(BORDERS, f.name) in roles, f.name


# Accessibility


def test_contrast_ratio_matches_known_wcag_values() -> None:
    assert contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert contrast_ratio("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)
    assert contrast_ratio("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)


def test_contrast_ratio_rejects_malformed_colors() -> None:
    with pytest.raises(ValueError):
        contrast_ratio("F96302", "#FFFFFF")


@pytest.mark.parametrize(
    "pair", CONTRAST_PAIRS, ids=[f"{p.foreground}-on-{p.background}" for p in CONTRAST_PAIRS]
)
def test_contrast_pair_meets_its_wcag_minimum(pair) -> None:
    roles = color_roles()
    assert pair.foreground in roles and pair.background in roles
    ratio = contrast_ratio(roles[pair.foreground], roles[pair.background])
    assert ratio >= MINIMUM_RATIO[pair.use], f"{ratio:.2f} < {MINIMUM_RATIO[pair.use]}"


@pytest.mark.parametrize(
    "foreground, background",
    [
        ("action_primary_fg", "action_primary_bg"),
        ("text_body", "app_background"),
        ("text_muted", "app_background"),
        ("text_on_brand", "brand_orange"),
    ],
)
def test_required_pairs_are_declared_as_normal_text(foreground: str, background: str) -> None:
    declared = {(p.foreground, p.background): p.use for p in CONTRAST_PAIRS}
    assert declared.get((foreground, background)) is ContrastUse.NORMAL_TEXT


def test_white_text_on_brand_orange_is_rejected() -> None:
    """Documents why CTAs use the darker orange: white on brand orange fails AA."""
    assert contrast_ratio("#FFFFFF", COLORS.brand_orange) < MINIMUM_RATIO[ContrastUse.NORMAL_TEXT]
    assert ("action_primary_fg", "brand_orange") not in {
        (p.foreground, p.background) for p in CONTRAST_PAIRS
    }


def test_focus_ring_is_visible_on_every_neutral_surface() -> None:
    for surface in (COLORS.app_background, COLORS.surface_primary, COLORS.surface_secondary):
        assert contrast_ratio(BORDERS.focus_ring_color, surface) >= 3.0


# Typography


def test_required_type_roles_exist() -> None:
    assert REQUIRED_TYPE_ROLES <= {f.name for f in fields(TypographyTokens)}


def test_heading_hierarchy_descends() -> None:
    sizes = [
        TYPOGRAPHY.page_title.size_px,
        TYPOGRAPHY.section_title.size_px,
        TYPOGRAPHY.subsection_title.size_px,
        TYPOGRAPHY.body.size_px,
        TYPOGRAPHY.body_small.size_px,
        TYPOGRAPHY.caption.size_px,
    ]
    assert sizes == sorted(sizes, reverse=True)
    assert len(set(sizes)) == len(sizes)


@pytest.mark.parametrize("role", sorted(REQUIRED_TYPE_ROLES))
def test_type_roles_are_readable(role: str) -> None:
    spec = getattr(TYPOGRAPHY, role)
    assert spec.size_px >= 12
    assert 100 <= spec.weight <= 900
    assert 1.0 <= spec.line_height <= 1.8


def test_metric_labels_keep_their_case() -> None:
    """Metric labels contain units such as dB, px, and mm, where case carries meaning."""
    assert TYPOGRAPHY.metric_label.uppercase is False


def test_only_code_is_monospace() -> None:
    mono = {f.name for f in fields(TypographyTokens) if getattr(TYPOGRAPHY, f.name).monospace}
    assert mono == {"code"}


# Spacing, shape, elevation, breakpoints


def test_spacing_scale_is_expected_and_monotonic() -> None:
    values = [getattr(SPACING, f.name) for f in fields(SPACING)]
    assert values == [4, 8, 12, 16, 24, 32, 48, 64]
    assert all(a < b for a, b in zip(values, values[1:]))


def test_spacing_field_names_encode_base_units() -> None:
    for f in fields(SPACING):
        assert getattr(SPACING, f.name) == 4 * int(f.name[1:])


def test_radii_are_restrained_and_ordered() -> None:
    assert 0 < RADII.small < RADII.standard < RADII.card <= 8
    assert RADII.pill >= 999


def test_heading_scale_binds_typography_roles_to_tags() -> None:
    assert HEADINGS.sizes_px[0] == TYPOGRAPHY.page_title.size_px
    assert HEADINGS.sizes_px[2] == TYPOGRAPHY.section_title.size_px
    assert HEADINGS.sizes_px[3] == TYPOGRAPHY.subsection_title.size_px
    assert HEADINGS.sidebar_sizes_px[0] == TYPOGRAPHY.app_title.size_px


@pytest.mark.parametrize("scale", ["sizes_px", "sidebar_sizes_px"])
def test_heading_sizes_strictly_descend(scale: str) -> None:
    sizes = getattr(HEADINGS, scale)
    assert len(sizes) == 6
    assert all(a > b for a, b in zip(sizes, sizes[1:]))


@pytest.mark.parametrize("scale", ["weights", "sidebar_weights"])
def test_heading_weights_are_streamlit_compatible(scale: str) -> None:
    weights = getattr(HEADINGS, scale)
    assert len(weights) == 6
    assert all(w % 100 == 0 and 100 <= w <= 900 for w in weights)


def test_body_weight_is_a_valid_streamlit_base_weight() -> None:
    assert TYPOGRAPHY.body.weight % 100 == 0 and 100 <= TYPOGRAPHY.body.weight <= 600


def test_reading_width_is_narrower_than_content_width() -> None:
    assert 600 <= LAYOUT.reading_max_width < LAYOUT.content_max_width


def test_breakpoints_ascend() -> None:
    values = [getattr(BREAKPOINTS, f.name) for f in fields(BREAKPOINTS)]
    assert values == sorted(values) and len(set(values)) == len(values)


# Naming


_TOKEN_CLASSES = [ColorTokens, TypographyTokens, BorderTokens, type(SPACING), type(RADII),
                  type(BREAKPOINTS)]
_PAGE_SPECIFIC_WORDS = ("module", "page", "calibration", "sfm", "fourier", "sam2", "tracking",
                        "thermal", "optical")


@pytest.mark.parametrize("cls", _TOKEN_CLASSES, ids=lambda c: c.__name__)
def test_token_names_are_semantic_snake_case(cls) -> None:
    for f in fields(cls):
        assert re.fullmatch(r"[a-z][a-z0-9_]*", f.name), f.name
        if cls is not TypographyTokens:  # "page_title"/"module_eyebrow" are roles, not pages
            assert not any(word in f.name for word in _PAGE_SPECIFIC_WORDS), f.name


# Source hygiene: requirements for vendoring into the assignment repositories


def _repo_text_files() -> list[Path]:
    paths = list(PACKAGE_DIR.rglob("*.py")) + list((REPO_ROOT / "tests").rglob("*.py"))
    paths += list((REPO_ROOT / "scripts").rglob("*.py"))
    paths += list((REPO_ROOT / "showcase").rglob("*.py"))
    paths += list((REPO_ROOT / "showcase").rglob("*.toml"))
    paths += [REPO_ROOT / name for name in ("README.md", "pyproject.toml")]
    return [p for p in paths if p.is_file()]


@pytest.mark.parametrize("path", _repo_text_files(), ids=lambda p: p.name)
def test_no_em_or_en_dashes(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for char, name in PROHIBITED_DASHES.items():
        assert char not in text, f"{name} found in {path.relative_to(REPO_ROOT)}"


_STDLIB_ALLOWED = {
    "__future__", "collections", "contextlib", "dataclasses", "enum", "html", "math", "re",
    "typing", "unicodedata",
}


def _module_level_import(path: Path) -> bool:
    rel = path.relative_to(PACKAGE_DIR)
    return "components" in rel.parts or rel.as_posix() == "shell.py"


@pytest.mark.parametrize(
    "path", sorted(PACKAGE_DIR.rglob("*.py")), ids=lambda p: p.relative_to(PACKAGE_DIR).as_posix()
)
def test_package_uses_only_relative_and_stdlib_imports(path: Path) -> None:
    """Vendored copies live under another package name, so absolute self-imports would break.

    Streamlit may be imported at module level only inside ``components/``; elsewhere only as a
    function-level import in styles.py, so tokens, theme, and the package itself stay
    importable without Streamlit installed.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lazy = {
        id(inner)
        for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        for inner in ast.walk(fn)
    }

    def check(module: str, node: ast.AST) -> None:
        top = module.split(".")[0]
        if top == "streamlit":
            assert _module_level_import(path) or (path.name == "styles.py" and id(node) in lazy), path
        else:
            assert top in _STDLIB_ALLOWED, module

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            check(node.module or "", node)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                check(alias.name, node)


def test_importing_the_package_does_not_import_streamlit() -> None:
    import subprocess
    import sys

    code = "import csc8830_ui, sys; print('streamlit' in sys.modules)"
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, check=True, env={"PYTHONPATH": str(REPO_ROOT / "src")},
    )
    assert out.stdout.strip() == "False"
