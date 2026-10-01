"""Render components through Streamlit's AppTest and check the native elements they produce.

These tests need ``streamlit>=1.56`` (the ``dev`` extra) for ``AppTest.file_uploader``.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src"
SFM_LABEL = "Mean reproj. error, inliers (px)"


def run(body: str) -> AppTest:
    header = (
        "import sys\n"
        f"sys.path.insert(0, {str(SRC)!r})\n"
        "import numpy as np\n"
        "import streamlit as st\n"
        "from csc8830_ui.components import *\n"
    )
    app = AppTest.from_string(header + textwrap.dedent(body), default_timeout=30).run()
    assert not app.exception, [e.value for e in app.exception]
    return app


# AppTest.file_uploader first shipped in Streamlit 1.56 (the dev floor). On the 1.49 runtime
# floor, upload checks are skipped: that is a missing test API, not a component failure.
HAS_UPLOAD_TEST_API = hasattr(AppTest, "file_uploader")
needs_upload_test_api = pytest.mark.skipif(
    not HAS_UPLOAD_TEST_API, reason="AppTest.file_uploader needs streamlit>=1.56"
)


def images(app: AppTest) -> list:
    # AppTest names image elements "imgs" in older releases and "image" in newer ones.
    return list(app.get("image")) + list(app.get("imgs"))


def html_bodies(app: AppTest) -> list[str]:
    return [element.proto.body for element in app.get("html")]


# Layout


def test_page_header_keeps_a_native_header_with_the_exact_title() -> None:
    app = run(
        """
        page_header("Question 1 - RGB Human Boundary", eyebrow="Module 4",
                    description="Classical OpenCV segmentation.", chips=[("Complete", "success")])
        """
    )
    assert [h.value for h in app.header] == ["Question 1 - RGB Human Boundary"]
    assert app.markdown[0].value == "Classical OpenCV segmentation."
    bodies = html_bodies(app)
    assert any("csc8830-eyebrow" in b and "Module 4" in b for b in bodies)
    assert any("csc8830-chip--success" in b and ">Complete<" in b for b in bodies)


def test_breadcrumbs_and_section_header() -> None:
    app = run(
        """
        breadcrumbs(["CSc 8830", "Module 5-6", "Motion Tracking"])
        section_header("Validation", description="Two consecutive frames.")
        """
    )
    assert any('aria-label="Breadcrumb"' in b for b in html_bodies(app))
    assert [s.value for s in app.subheader] == ["Validation"]
    assert [c.value for c in app.caption] == ["Two consecutive frames."]


def test_footer_is_a_caption() -> None:
    app = run('footer(["CSc 8830 Computer Vision", "Georgia State University"])')
    assert app.caption[0].value == "CSc 8830 Computer Vision · Georgia State University"


# Cards keep page-owned widgets


def test_configuration_card_preserves_widget_keys_defaults_and_run_gate() -> None:
    app = run(
        """
        with configuration_card(caption="Tracker settings"):
            with parameter_group("Window", help="Search window."):
                win = st.number_input("Window size", value=21, key="lk_win")
            run = st.button("Run tracking", type="primary", key="lk_run")
        st.write("ran" if run else "gated")
        """
    )
    assert app.number_input(key="lk_win").value == 21
    assert app.button(key="lk_run").label == "Run tracking"
    assert any(m.value == "gated" for m in app.markdown)
    assert any(m.value == "#### Configuration" for m in app.markdown)
    app.button(key="lk_run").click().run()
    assert any(m.value == "ran" for m in app.markdown)


# Metrics


def test_metric_row_uses_native_metrics_with_exact_labels_and_values() -> None:
    app = run(
        f"""
        metric_row([("MAE", "4.663e-14"), ("PSNR (dB)", "312.46"), ({SFM_LABEL!r}, "1.546"),
                    MetricSpec("Inlier ratio", "47.3%", delta="+1.0%")])
        """
    )
    assert [(m.label, m.value) for m in app.metric] == [
        ("MAE", "4.663e-14"), ("PSNR (dB)", "312.46"), (SFM_LABEL, "1.546"), ("Inlier ratio", "47.3%"),
    ]
    assert app.metric[3].delta == "+1.0%"
    assert len(app.columns) == 4


@pytest.mark.parametrize("count, columns", [(1, 1), (2, 2), (3, 3), (4, 4), (5, 6), (6, 6), (7, 8)])
def test_metric_row_chunks_at_four(count: int, columns: int) -> None:
    app = run(f'metric_row([("Metric " + str(i), str(i)) for i in range({count})])')
    assert len(app.metric) == count
    assert len(app.columns) == columns  # rows x shared column count, never more than 4 wide
    assert [m.label for m in app.metric] == [f"Metric {i}" for i in range(count)]


def test_metric_row_refuses_more_than_four_columns() -> None:
    from csc8830_ui.components import metric_row

    with pytest.raises(ValueError):
        metric_row([("a", 1)], max_columns=5)


# Status


def test_banners_are_native_alerts() -> None:
    app = run(
        """
        status_banner("info", "Bundled sample shown.")
        status_banner("success", "Validation passed.", title="Result")
        status_banner("warning", "PENDING USER EXPERIMENT.")
        status_banner("error", "Could not read the image.")
        pending_state("Upload a video to run tracking.")
        success_state("Experiment completed.")
        """
    )
    assert [a.value for a in app.info] == ["Bundled sample shown."]
    assert [a.value for a in app.success] == ["**Result**\n\nValidation passed.", "Experiment completed."]
    assert [a.value for a in app.warning] == ["PENDING USER EXPERIMENT.", "Upload a video to run tracking."]
    assert [a.value for a in app.error] == ["Could not read the image."]


def test_empty_state_is_quiet_not_an_alert() -> None:
    app = run('empty_state("No results yet", "Run the experiment to see metrics.")')
    assert not (app.info or app.warning or app.success or app.error)
    assert app.caption[0].value == "Run the experiment to see metrics."


def test_status_chips_escape_text() -> None:
    app = run('status_chips([("Passed", "success"), ("<img src=x>", "error")])')
    body = html_bodies(app)[0]
    assert ">Passed<" in body and "&lt;img src=x&gt;" in body and "<img" not in body


# Images, data, theory, results


def test_image_components_render_native_images_without_conversion() -> None:
    app = run(
        """
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        image_card(img, title="Frame 275", caption="Observed feature location", channels="BGR")
        image_comparison(ImageItem(img, title="Spatial"), ImageItem(img, title="Fourier"))
        image_gallery([ImageItem(img, caption=f"view_{i}") for i in range(5)])
        """
    )
    assert len(images(app)) == 1 + 2 + 5
    assert len(app.columns) == 2 + 6  # comparison, then a 3 + 2 gallery on 3 columns


def test_image_gallery_refuses_more_than_four_columns() -> None:
    from csc8830_ui.components import image_gallery

    with pytest.raises(ValueError):
        image_gallery([], max_columns=5)


def test_data_table_and_download_action_are_native() -> None:
    app = run(
        """
        data_table({"Experiment": ["Video 1"], "Error (px)": [4.628]}, hide_index=True, key="tbl")
        download_action("Download record", b"{}", file_name="record.json",
                        mime="application/json", key="dl_record")
        """
    )
    assert len(app.dataframe) == 1
    assert list(app.dataframe[0].value.columns) == ["Experiment", "Error (px)"]
    assert len(app.get("download_button")) == 1


def test_equation_block_passes_latex_unchanged() -> None:
    latex = r"I_x u + I_y v + I_t = 0"
    app = run(
        f"""
        section = theory_section("Optical flow constraint", number=1, body="Brightness constancy.")
        equation_block({latex!r}, title="Constraint", caption="Linearized.")
        """
    )
    assert [s.value for s in app.subheader] == ["01 · Optical flow constraint"]
    # st.latex itself wraps its body in display delimiters; the equation inside is untouched.
    assert [x.value for x in app.latex] == [f"$$\n{latex}\n$$"]


def test_experiment_summary_and_result_section() -> None:
    app = run(
        """
        experiment_summary(method="Pyramidal Lucas-Kanade", evidence="Frames 274 and 275",
                           status_label="Validated", status_kind="success",
                           result="Pixel error 4.628 px", interpretation="Within tolerance.")
        with result_section("Metrics", description="From the committed record."):
            st.write("inside")
        """
    )
    texts = [m.value for m in app.markdown]
    assert "**Method.** Pyramidal Lucas-Kanade" in texts
    assert "**Result.** Pixel error 4.628 px" in texts
    assert any(">Validated<" in b for b in html_bodies(app))
    assert [s.value for s in app.subheader] == ["Metrics"]


# Upload


@needs_upload_test_api
def test_upload_panel_keeps_the_native_uploader_and_its_key() -> None:
    app = run(
        """
        value = upload_panel("RGB image", type=["jpg", "png"], key="rgb_upload",
                             explanation="Upload a photo.", sample_notice="Showing bundled sample.")
        st.write("uploaded" if value else "none")
        """
    )
    uploader = app.file_uploader(key="rgb_upload")
    assert uploader.label == "RGB image"
    assert [a.value for a in app.info] == ["Showing bundled sample."]
    uploader.set_value(("a.png", b"\x89PNG", "image/png")).run()
    assert not app.info  # the bundled notice disappears once a file is uploaded
    assert any(m.value == "uploaded" for m in app.markdown)


# Showcase


SHOWCASE = SRC.parent / "showcase" / "app.py"


def test_showcase_renders_every_component_without_exceptions() -> None:
    app = AppTest.from_file(str(SHOWCASE), default_timeout=60).run()
    assert not app.exception, [e.value for e in app.exception]
    assert len(app.metric) == sum(range(1, 7))
    assert app.info and app.success and app.warning and app.error
    if HAS_UPLOAD_TEST_API:
        assert app.file_uploader(key="demo_upload").label == "Example upload"


def test_showcase_config_matches_the_kit_theme() -> None:
    from csc8830_ui import render_config_toml

    config = SHOWCASE.parent / ".streamlit" / "config.toml"
    assert config.read_text(encoding="utf-8") == render_config_toml()


def test_image_components_can_drop_the_card_border() -> None:
    from csc8830_ui.components import image_card, image_comparison

    import inspect
    for fn in (image_card, image_comparison):
        assert inspect.signature(fn).parameters["bordered"].default is True
    app = run(
        """
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        image_card(img, caption="a", bordered=False)
        image_comparison(ImageItem(img, caption="l"), ImageItem(img, caption="r"), bordered=False)
        """
    )
    assert len(images(app)) == 3
