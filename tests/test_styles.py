"""Tests for the global stylesheet and its injection helper."""
from __future__ import annotations

import re
import sys
import types

from csc8830_ui import COLORS, KIT_VERSION
from csc8830_ui.styles import (
    CSS_PREFIX,
    STYLE_ELEMENT_ID,
    build_css,
    css_variables,
    inject_global_styles,
    style_tag,
)


def test_css_is_deterministic_and_versioned() -> None:
    assert build_css() == build_css()
    assert build_css().startswith(f"/* csc8830-ui {KIT_VERSION} global styles */")


def test_custom_properties_are_namespaced_and_cover_every_color() -> None:
    variables = css_variables()
    assert all(name.startswith(f"--{CSS_PREFIX}-") for name in variables)
    assert variables["--csc8830-color-brand-orange"] == COLORS.brand_orange
    assert variables["--csc8830-color-action-primary-bg"] == COLORS.action_primary_bg
    assert variables["--csc8830-space-x4"] == "16px"


def test_metric_labels_are_not_case_transformed() -> None:
    css = build_css()
    label_rule = css[css.index('[data-testid="stMetricLabel"],') : css.index("}", css.index('[data-testid="stMetricLabel"],'))]
    assert "text-transform: none" in label_rule


def test_css_avoids_generated_class_names_and_positional_selectors() -> None:
    css = build_css()
    assert "st-emotion-cache" not in css
    assert "nth-child" not in css and "nth-of-type" not in css
    assert "display: none" not in css and "visibility: hidden" not in css


def test_css_only_targets_documented_streamlit_hooks() -> None:
    hooks = set(re.findall(r'data-testid="([A-Za-z]+)"', build_css()))
    assert hooks == {"stMainBlockContainer", "stCaptionContainer", "stMetricLabel", "stMetricValue"}


def test_custom_classes_use_the_namespace() -> None:
    for cls in re.findall(r"\.([a-zA-Z][\w-]*)", build_css()):
        assert cls == "stApp" or cls.startswith(f"{CSS_PREFIX}-"), cls


def test_style_tag_contains_no_script_or_event_handlers() -> None:
    tag = style_tag().lower()
    assert "<script" not in tag and "javascript:" not in tag
    assert not re.search(r"\son\w+=", tag)
    assert tag.startswith(f'<style id="{STYLE_ELEMENT_ID}">')
    assert tag.count("<style") == 1 and tag.endswith("</style>")


def test_inject_global_styles_emits_one_style_element(monkeypatch) -> None:
    calls: list[str] = []
    fake = types.ModuleType("streamlit")
    fake.html = calls.append  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    inject_global_styles()
    inject_global_styles()
    assert calls == [style_tag(), style_tag()]  # repeated calls are identical, hence harmless
