"""Tests for stable slugs and URL resolution (no Streamlit needed)."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from csc8830_ui.navigation import (
    RESERVED_MODULE_SLUGS,
    build_navigation,
    resolve,
    slugify,
)

# The registered course pages at the time of writing, in dashboard order.
COURSE_PAGES = {
    "Module 2": ["Calibration", "Dimension Estimation", "Validation Analysis", "Theory"],
    "Module 3": ["Image Blurring", "Spatial vs Fourier", "Experimental Validation", "Theory"],
    "Module 4": [
        "RGB Human Boundary", "Thermal Human Boundary", "Comparison and Evaluation",
        "Fourier Theory",
    ],
    "Module 5-6": [
        "Optical Flow", "Motion Tracking", "Bilinear Interpolation & Theory",
        "Structure From Motion", "Experiments & Results",
    ],
}


@dataclass(frozen=True)
class Page:
    module_label: str
    page_label: str
    order: int = 0

    def render(self) -> None:  # pragma: no cover - never called here
        pass


def course_pages() -> list[Page]:
    return [Page(m, p, i) for m, labels in COURSE_PAGES.items() for i, p in enumerate(labels)]


@pytest.mark.parametrize(
    "label, slug",
    [
        ("Module 2", "module-2"),
        ("Module 3", "module-3"),
        ("Module 4", "module-4"),
        ("Module 5-6", "module-5-6"),
        ("Motion Tracking", "motion-tracking"),
        ("Comparison and Evaluation", "comparison-and-evaluation"),
        ("Experiments & Results", "experiments-results"),
        ("Bilinear Interpolation & Theory", "bilinear-interpolation-theory"),
        ("Spatial vs Fourier", "spatial-vs-fourier"),
        ("  Café / Results!  ", "cafe-results"),
    ],
)
def test_slugify(label: str, slug: str) -> None:
    assert slugify(label) == slug


def test_slugify_rejects_labels_without_usable_characters() -> None:
    with pytest.raises(ValueError):
        slugify("&&&")


def test_every_course_page_has_a_unique_slug_within_its_module() -> None:
    modules = build_navigation(course_pages())
    assert [m.slug for m in modules] == ["module-2", "module-3", "module-4", "module-5-6"]
    for module in modules:
        slugs = [p.slug for p in module.pages]
        assert len(slugs) == len(set(slugs))
    assert sum(len(m.pages) for m in modules) == 17
    assert not {m.slug for m in modules} & RESERVED_MODULE_SLUGS


def test_same_page_slug_in_different_modules_is_allowed() -> None:
    modules = build_navigation(course_pages())
    theory = [m.label for m in modules if m.page_by_slug("theory")]
    assert theory == ["Module 2", "Module 3"]


def test_page_slug_collision_within_a_module_fails_clearly() -> None:
    with pytest.raises(ValueError, match="share the slug 'results-theory'"):
        build_navigation([Page("Module 9", "Results & Theory"), Page("Module 9", "Results / Theory")])


def test_module_slug_collision_fails_clearly() -> None:
    with pytest.raises(ValueError, match="share the slug 'module-5-6'"):
        build_navigation([Page("Module 5-6", "A"), Page("Module 5 6", "B")])


def test_reserved_home_slug_is_refused() -> None:
    with pytest.raises(ValueError, match="reserved"):
        build_navigation([Page("Home", "Overview")])


def test_build_navigation_preserves_registration_order() -> None:
    modules = build_navigation(course_pages())
    assert [p.label for p in modules[3].pages] == COURSE_PAGES["Module 5-6"]


@pytest.mark.parametrize(
    "module_slug, page_slug, expected",
    [
        ("module-5-6", "motion-tracking", ("Module 5-6", "Motion Tracking")),
        ("module-4", "comparison-and-evaluation", ("Module 4", "Comparison and Evaluation")),
        (None, None, ("Module 2", "Calibration")),
        ("module-99", "motion-tracking", ("Module 2", "Calibration")),
        ("module-4", "motion-tracking", ("Module 4", "RGB Human Boundary")),
        ("module-3", None, ("Module 3", "Image Blurring")),
        ("Module 4", "Fourier Theory", ("Module 2", "Calibration")),  # labels are not slugs
    ],
)
def test_resolve_with_fallbacks(module_slug, page_slug, expected) -> None:
    module, page = resolve(build_navigation(course_pages()), module_slug, page_slug)
    assert (module.label, page.label) == expected


def test_resolve_needs_pages() -> None:
    with pytest.raises(ValueError):
        resolve((), "module-2", "calibration")
