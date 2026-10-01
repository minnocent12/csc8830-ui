"""Tests for the generated native Streamlit theme."""
from __future__ import annotations

import tomllib

import pytest

from csc8830_ui import COLORS, HEADINGS, KIT_VERSION, RADII, TYPOGRAPHY, contrast_ratio
from csc8830_ui.accessibility import is_hex_color
from csc8830_ui.theme import STREAMLIT_REQUIREMENT, render_config_toml, streamlit_theme

# Every theme key registered by Streamlit 1.47.0 (read from that release's config module).
# Keys added later, such as redColor or metricValueFontSize, must not be emitted.
STREAMLIT_147_THEME_KEYS = {
    "base", "primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor",
    "linkColor", "linkUnderline", "borderColor", "showWidgetBorder", "showSidebarBorder",
    "baseRadius", "buttonRadius", "font", "headingFont", "codeFont", "fontFaces",
    "baseFontSize", "baseFontWeight", "headingFontSizes", "headingFontWeights",
    "codeFontSize", "codeFontWeight", "codeBackgroundColor", "dataframeBorderColor",
    "dataframeHeaderBackgroundColor", "chartCategoricalColors", "chartSequentialColors",
}
STREAMLIT_147_SIDEBAR_KEYS = {
    "backgroundColor", "baseRadius", "borderColor", "buttonRadius", "codeBackgroundColor",
    "codeFont", "codeFontSize", "dataframeBorderColor", "dataframeHeaderBackgroundColor",
    "font", "headingFont", "headingFontSizes", "headingFontWeights", "linkColor",
    "linkUnderline", "primaryColor", "secondaryBackgroundColor", "showWidgetBorder",
    "textColor",
}


@pytest.fixture(scope="module")
def parsed() -> dict:
    return tomllib.loads(render_config_toml())


def test_toml_round_trips_to_the_theme_dict(parsed: dict) -> None:
    theme = streamlit_theme()
    assert {k: v for k, v in parsed["theme"].items() if k != "sidebar"} == theme["theme"]
    assert parsed["theme"]["sidebar"] == theme["theme.sidebar"]


def test_only_streamlit_147_keys_are_emitted(parsed: dict) -> None:
    main = {k for k in parsed["theme"] if k != "sidebar"}
    assert main <= STREAMLIT_147_THEME_KEYS, main - STREAMLIT_147_THEME_KEYS
    sidebar = set(parsed["theme"]["sidebar"])
    assert sidebar <= STREAMLIT_147_SIDEBAR_KEYS, sidebar - STREAMLIT_147_SIDEBAR_KEYS
    assert set(parsed) == {"theme"}


def test_requested_properties_are_present(parsed: dict) -> None:
    requested = {
        "primaryColor", "backgroundColor", "secondaryBackgroundColor", "textColor", "font",
        "headingFont", "codeFont", "baseRadius", "buttonRadius", "borderColor",
        "dataframeBorderColor", "dataframeHeaderBackgroundColor", "headingFontSizes",
        "headingFontWeights", "baseFontWeight",
    }
    assert requested <= set(parsed["theme"])


def test_values_match_canonical_tokens(parsed: dict) -> None:
    t = parsed["theme"]
    assert t["base"] == "light"
    assert t["primaryColor"] == COLORS.action_primary_bg
    assert t["backgroundColor"] == COLORS.app_background
    assert t["secondaryBackgroundColor"] == COLORS.surface_primary
    assert t["textColor"] == COLORS.text_body
    assert t["linkColor"] == COLORS.brand_orange_strong
    assert t["borderColor"] == COLORS.border_strong
    assert t["dataframeBorderColor"] == COLORS.border
    assert t["dataframeHeaderBackgroundColor"] == COLORS.surface_secondary
    assert t["baseRadius"] == t["buttonRadius"] == f"{RADII.standard}px"
    assert t["baseFontSize"] == TYPOGRAPHY.body.size_px
    assert t["baseFontWeight"] == TYPOGRAPHY.body.weight
    assert t["headingFontSizes"] == [f"{s}px" for s in HEADINGS.sizes_px]
    assert t["headingFontWeights"] == list(HEADINGS.weights)
    assert t["codeFontSize"] == f"{TYPOGRAPHY.code.size_px}px"
    assert t["sidebar"]["headingFontSizes"] == [f"{s}px" for s in HEADINGS.sidebar_sizes_px]


def _colors(section: dict) -> dict[str, str]:
    return {k: v for k, v in section.items() if isinstance(v, str) and v.startswith("#")}


def test_every_color_value_is_valid_hex(parsed: dict) -> None:
    colors = {**_colors(parsed["theme"]), **_colors(parsed["theme"]["sidebar"])}
    assert colors
    for key, value in colors.items():
        assert is_hex_color(value), key


@pytest.mark.parametrize(
    "fg_key, bg_key, minimum",
    [
        ("textColor", "backgroundColor", 4.5),
        ("textColor", "secondaryBackgroundColor", 4.5),
        ("linkColor", "backgroundColor", 4.5),
        ("primaryColor", "backgroundColor", 3.0),  # focus and active indicators
        ("borderColor", "secondaryBackgroundColor", 3.0),  # input outlines
        ("borderColor", "backgroundColor", 3.0),
        ("textColor", "codeBackgroundColor", 4.5),
        ("textColor", "dataframeHeaderBackgroundColor", 4.5),
    ],
)
def test_theme_combinations_meet_wcag(parsed: dict, fg_key: str, bg_key: str, minimum: float) -> None:
    t = parsed["theme"]
    assert contrast_ratio(t[fg_key], t[bg_key]) >= minimum


def test_primary_button_label_is_accessible(parsed: dict) -> None:
    # Streamlit renders primary buttons as white text on primaryColor.
    assert contrast_ratio("#FFFFFF", parsed["theme"]["primaryColor"]) >= 4.5


def test_sidebar_text_is_accessible(parsed: dict) -> None:
    sidebar = parsed["theme"]["sidebar"]
    assert contrast_ratio(parsed["theme"]["textColor"], sidebar["backgroundColor"]) >= 4.5


def test_config_header_names_version_and_requirement() -> None:
    text = render_config_toml()
    assert text.startswith(f"# Generated by csc8830-ui {KIT_VERSION}.")
    assert STREAMLIT_REQUIREMENT in text
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_config_contains_no_secret_like_keys(parsed: dict) -> None:
    keys = [k.lower() for k in parsed["theme"]] + [k.lower() for k in parsed["theme"]["sidebar"]]
    for word in ("secret", "token", "password", "apikey", "api_key", "credential"):
        assert not any(word in key for key in keys)


def test_render_is_deterministic() -> None:
    assert render_config_toml() == render_config_toml()
