"""Development-only showcase of every csc8830-ui component.

Run from the csc8830-ui repository root:

    streamlit run showcase/app.py

This file lives outside ``src/`` and is never vendored into the assignment repositories.
Every image, number, and table row below is a synthetic placeholder for layout review only;
none of it is experimental data from any module.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from csc8830_ui import KIT_VERSION, inject_global_styles  # noqa: E402
from csc8830_ui.components import (  # noqa: E402
    ImageItem,
    MetricSpec,
    breadcrumbs,
    card,
    configuration_card,
    data_table,
    download_action,
    empty_state,
    equation_block,
    experiment_summary,
    footer,
    image_card,
    image_comparison,
    image_gallery,
    metric_row,
    page_header,
    parameter_group,
    pending_state,
    result_section,
    section_header,
    status_banner,
    status_chips,
    success_state,
    theory_section,
    upload_panel,
)

PLACEHOLDER = "Synthetic placeholder for layout review, not experimental data."


def placeholder_image(seed: int, height: int = 120, width: int = 180) -> np.ndarray:
    """Deterministic RGB gradient with a block, so images are distinguishable."""
    y, x = np.mgrid[0:height, 0:width]
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[..., 0] = (x * 255 // max(width - 1, 1)).astype(np.uint8)
    image[..., 1] = (y * 255 // max(height - 1, 1)).astype(np.uint8)
    image[..., 2] = (seed * 47) % 256
    image[20 + seed * 5 : 60 + seed * 5, 30:80] = 240
    return image


st.set_page_config(page_title="csc8830-ui showcase", layout="wide")
inject_global_styles()

breadcrumbs(["CSc 8830", "Design system", "Component showcase"])
page_header(
    "Component showcase",
    eyebrow=f"csc8830-ui {KIT_VERSION}",
    description="Every shared component with placeholder content. " + PLACEHOLDER,
    chips=[("Development only", "brand"), ("Not vendored", "neutral")],
)

section_header("Cards and configuration", description="The page owns every control and key.")
left, right = st.columns(2)
with left:
    with configuration_card(caption="Controls stay native Streamlit widgets."):
        with parameter_group("Window", help="Search window around each feature."):
            st.number_input("Window size", value=21, key="demo_window")
            st.slider("Pyramid levels", 0, 5, 3, key="demo_levels")
        with st.expander("Advanced settings"):
            st.number_input("Max iterations", value=30, key="demo_iterations")
        st.button("Run experiment", type="primary", key="demo_run")
with right:
    with card("Plain card", caption="A bordered container for grouped content."):
        st.write("Cards rely on borders and spacing, not shadows.")
    empty_state("No results yet", "Run the experiment to see metrics.")

section_header("Metric rows", description="At most four per row; long labels wrap; case is preserved.")
labels = ["MAE", "PSNR (dB)", "Mean reproj. error, inliers (px)", "Inlier ratio", "RMSE", "Max error"]
for count in range(1, 7):
    st.caption(f"{count} metric{'s' if count > 1 else ''}")
    metric_row([MetricSpec(labels[i], f"{(i + 1) * 1.234:.3f}") for i in range(count)])

section_header("Status")
status_chips([
    ("Passed", "success"), ("Complete", "success"), ("Pending", "warning"),
    ("Reference", "info"), ("Bundled sample", "neutral"), ("Failed", "error"), ("Active", "brand"),
])
status_banner("info", "Informational banner. Prefer chips for routine state.")
status_banner("success", "Use for confirmed outcomes.", title="Success banner")
status_banner("warning", "Use when the reader must act or data is pending.")
status_banner("error", "Use for failures the reader needs to see.")
pending_state("Pending state: the caller supplies the exact wording.")
success_state("Success state: the caller supplies the exact wording.")

section_header("Images", description=PLACEHOLDER)
image_card(placeholder_image(1), title="Image card", caption="Native caption", note="Optional note")
image_comparison(
    ImageItem(placeholder_image(2), title="Left", caption="Left caption"),
    ImageItem(placeholder_image(3), title="Right", caption="Right caption"),
)
image_gallery([ImageItem(placeholder_image(i), caption=f"Gallery item {i}") for i in range(5)])

with result_section("Data", description=PLACEHOLDER):
    data_table(
        {"Example": ["Row A", "Row B"], "Placeholder value": [1.0, 2.0], "Status": ["Pending", "Pending"]},
        hide_index=True,
    )
    download_action("Download placeholder JSON", b"{}", file_name="placeholder.json",
                    mime="application/json", key="demo_download")

theory_section("Optical flow constraint", number=1,
               body="Theory sections are a heading and ordinary content, not cards.")
equation_block(r"I_x u + I_y v + I_t = 0", title="Brightness constancy, linearized",
               caption="Equations are passed to st.latex unchanged.")

section_header("Experiment summary")
experiment_summary(
    method="Placeholder method",
    evidence="Placeholder evidence",
    status_label="Pending",
    status_kind="warning",
    result="Placeholder result",
    interpretation="The caller states the status explicitly; it is never inferred.",
)

section_header("Upload panel")
upload_panel("Example upload", type=["jpg", "png"], key="demo_upload",
             explanation="Explanation text above the native uploader.",
             sample_notice="No upload: a bundled sample would be shown here.", show_formats=True)

footer(["CSc 8830 Computer Vision", "Georgia State University", f"csc8830-ui {KIT_VERSION}"])
