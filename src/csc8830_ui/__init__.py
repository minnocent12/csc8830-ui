"""CSc 8830 design kit: canonical design tokens for the Computer Vision application.

This package is the canonical source that assignment repositories vendor into their own
``src/<module>/webapp/design/`` package. Assignment code never imports it at runtime.
"""
from __future__ import annotations

from .accessibility import ContrastUse, contrast_ratio, relative_luminance
from .tokens import (
    BORDERS,
    BREAKPOINTS,
    COLORS,
    CONTRAST_PAIRS,
    ELEVATION,
    FONT_FAMILY_MONO,
    FONT_FAMILY_SANS,
    RADII,
    SPACING,
    TYPOGRAPHY,
    color_roles,
)
from .version import KIT_VERSION

__all__ = [
    "BORDERS",
    "BREAKPOINTS",
    "COLORS",
    "CONTRAST_PAIRS",
    "ELEVATION",
    "FONT_FAMILY_MONO",
    "FONT_FAMILY_SANS",
    "KIT_VERSION",
    "RADII",
    "SPACING",
    "TYPOGRAPHY",
    "ContrastUse",
    "color_roles",
    "contrast_ratio",
    "relative_luminance",
]
