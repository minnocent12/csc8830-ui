"""Streamlit-free tests for component helpers: layout arithmetic, escaping, markup."""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

pytest.importorskip("streamlit")  # importing the components subpackage imports Streamlit

from csc8830_ui import components  # noqa: E402
from csc8830_ui.components._grid import balanced_row_sizes, grid_rows  # noqa: E402
from csc8830_ui.components._text import html_text, markdown_text  # noqa: E402
from csc8830_ui.components.layout import breadcrumbs_html, eyebrow_html  # noqa: E402
from csc8830_ui.components.status import StatusKind, chip_html, chips_html  # noqa: E402
from csc8830_ui.components.theory import section_label  # noqa: E402
from csc8830_ui.components.uploads import supported_formats_text  # noqa: E402
from csc8830_ui.styles import CHIP_COLORS, build_css  # noqa: E402
from csc8830_ui.tokens import CONTRAST_PAIRS, ContrastUse  # noqa: E402

COMPONENTS_DIR = Path(__file__).resolve().parents[1] / "src" / "csc8830_ui" / "components"

EXPECTED_API = {
    "page_header", "breadcrumbs", "section_header", "footer",
    "card", "configuration_card", "parameter_group",
    "metric_card", "metric_row", "MetricSpec", "MAX_METRIC_COLUMNS",
    "status_chip", "status_chips", "status_banner", "StatusKind",
    "empty_state", "pending_state", "success_state",
    "image_card", "image_comparison", "image_gallery", "ImageItem",
    "data_table", "download_action",
    "theory_section", "equation_block",
    "experiment_summary", "result_section", "RESULT_SECTION_ORDER",
    "upload_panel", "balanced_row_sizes",
}


def test_public_exports() -> None:
    assert set(components.__all__) == EXPECTED_API
    for name in components.__all__:
        assert getattr(components, name) is not None


# Layout arithmetic


@pytest.mark.parametrize(
    "count, expected",
    [(0, []), (1, [1]), (2, [2]), (3, [3]), (4, [4]), (5, [3, 2]), (6, [3, 3]),
     (7, [4, 3]), (8, [4, 4]), (9, [3, 3, 3]), (10, [4, 3, 3]), (12, [4, 4, 4])],
)
def test_metric_rows_never_exceed_four_and_stay_balanced(count: int, expected: list[int]) -> None:
    sizes = balanced_row_sizes(count, 4)
    assert sizes == expected
    assert all(size <= 4 for size in sizes) and sum(sizes) == count
    assert not sizes or max(sizes) - min(sizes) <= 1


def test_grid_rows_keeps_order_and_uses_one_column_count() -> None:
    columns, rows = grid_rows(list("abcde"), 4)
    assert columns == 3 and rows == [["a", "b", "c"], ["d", "e"]]


def test_grid_rejects_zero_columns() -> None:
    with pytest.raises(ValueError):
        balanced_row_sizes(3, 0)


# Escaping


def test_html_text_escapes_markup_and_quotes() -> None:
    assert html_text('<script>alert("x")</script>&') == (
        "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;&amp;"
    )


def test_markdown_text_keeps_identifiers_and_dollar_literal() -> None:
    assert markdown_text("view_2 -> view_1") == r"view\_2 -\> view\_1"
    assert markdown_text("cost $5") == r"cost \$5"
    assert markdown_text("PSNR (dB)") == r"PSNR \(dB\)"


@pytest.mark.parametrize("label", ["<b>Passed</b>", "a\"b", "x' onmouseover='y"])
def test_chip_html_escapes_labels(label: str) -> None:
    out = chip_html(label, "success")
    assert "<b>" not in out and "onmouseover='" not in out
    assert html_text(label) in out


def test_chip_requires_visible_text_and_known_kind() -> None:
    with pytest.raises(ValueError):
        chip_html("   ", "success")
    with pytest.raises(ValueError):
        chip_html("Passed", "green")


def test_chip_markup_carries_text_and_namespaced_classes() -> None:
    out = chips_html([("Passed", "success"), ("Pending", StatusKind.WARNING)])
    assert re.findall(r">([^<]+)</span>", out) == ["Passed", "Pending"]
    assert all(c.startswith("csc8830-") for c in re.findall(r'class="([^"]+)"', out)[0].split())


def test_breadcrumbs_are_accessible_plain_text() -> None:
    out = breadcrumbs_html(["CSc 8830", "Module 5-6", "<Motion> Tracking"])
    assert out.startswith('<nav class="csc8830-breadcrumbs" aria-label="Breadcrumb">')
    assert out.count('aria-current="page"') == 1
    assert "&lt;Motion&gt; Tracking" in out and "<a " not in out
    assert out.count('aria-hidden="true">/</span>') == 2


def test_eyebrow_is_escaped() -> None:
    assert eyebrow_html("<Module 4>") == '<p class="csc8830-eyebrow">&lt;Module 4&gt;</p>'


def test_section_label_formats_numbers_without_dashes() -> None:
    assert section_label("Projection model", 1) == "01 · Projection model"
    assert section_label("Derivation", "2.1") == "2.1 · Derivation"
    assert section_label("Overview") == "Overview"


def test_supported_formats_text_dedupes_in_caller_order() -> None:
    assert supported_formats_text(["jpg", "jpeg", ".png", "JPG"]) == "Supported formats: JPG, JPEG, PNG"


# Contracts that later page migrations rely on


def test_experiment_summary_requires_an_explicit_status() -> None:
    params = inspect.signature(components.experiment_summary).parameters
    for name in ("status_label", "status_kind", "method", "evidence"):
        assert params[name].default is inspect.Parameter.empty


def test_components_never_invent_widget_keys() -> None:
    for fn in (components.upload_panel, components.data_table, components.download_action):
        assert inspect.signature(fn).parameters["key"].default is None


def test_every_chip_color_pair_is_a_checked_contrast_pair() -> None:
    declared = {(p.foreground, p.background) for p in CONTRAST_PAIRS if p.use is ContrastUse.NORMAL_TEXT}
    for kind, pair in CHIP_COLORS.items():
        assert pair in declared, kind
    assert set(CHIP_COLORS) == {k.value for k in StatusKind}


def test_component_css_classes_are_namespaced() -> None:
    css = build_css()
    for kind in CHIP_COLORS:
        assert f".csc8830-chip--{kind}" in css


@pytest.mark.parametrize("path", sorted(COMPONENTS_DIR.glob("*.py")), ids=lambda p: p.name)
def test_components_use_no_unsafe_html_or_scripts(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for banned in ("unsafe_allow_html", "unsafe_allow_javascript", "components.v1", "<script", "iframe"):
        assert banned not in text, banned


@pytest.mark.parametrize("path", sorted(COMPONENTS_DIR.glob("*.py")), ids=lambda p: p.name)
def test_components_do_no_image_processing(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for banned in ("import cv2", "cvtColor", "import numpy", "astype("):
        assert banned not in text, banned
