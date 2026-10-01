"""AppTest coverage for the shared shell: navigation, standalone context, URL sync."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

SRC = Path(__file__).resolve().parents[1] / "src"

SETUP = f"""
import sys
sys.path.insert(0, {str(SRC)!r})
import streamlit as st
from types import SimpleNamespace
from csc8830_ui.shell import HomeSpec, render_shell

def page(module, label, order, extra_radio=False):
    def render():
        st.markdown(f"BODY {{module}} / {{label}}")
        if extra_radio:
            st.radio("Page-level choice", ["a", "b"], key="inner_choice")
    return SimpleNamespace(module_label=module, page_label=label, order=order, render=render)

PAGES = [
    page("Module 2", "Calibration", 10),
    page("Module 2", "Theory", 40),
    page("Module 4", "RGB Human Boundary", 10),
    page("Module 4", "Comparison and Evaluation", 30, extra_radio=True),
    page("Module 5-6", "Motion Tracking", 20),
    page("Module 5-6", "Experiments & Results", 50),
]
M4 = [p for p in PAGES if p.module_label == "Module 4"]

def home_render(ctx):
    st.markdown("HOME " + " ".join(f"{{m.slug}}:{{len(m.pages)}}:{{ctx.first_page(m).label}}" for m in ctx.modules))
    for m in ctx.modules:
        st.button("Open Module", key="open_" + m.slug, on_click=ctx.open_module, args=(m.slug,))
"""

COMBINED = 'render_shell(PAGES, page_title="CSc 8830 Computer Vision", sync_query_params=True, notices=["Module 3 is not importable yet; skipping it."])'
STANDALONE = (
    'render_shell(M4, page_title="CSc 8830 - Module 4", standalone=True, '
    'page_context=lambda p: "Context for " + p.page_label)'
)


def make(call: str, **query: str) -> AppTest:
    app = AppTest.from_string(SETUP + textwrap.dedent(call), default_timeout=30)
    for key, value in query.items():
        app.query_params[key] = value
    return app


def run(target) -> AppTest:
    """Run an AppTest, or the AppTest behind a widget after ``set_value``."""
    app = target.run()
    assert not app.exception, [e.value for e in app.exception]
    return app


def body(app: AppTest) -> str:
    return next(m.value for m in app.markdown if m.value.startswith("BODY "))


def query(app: AppTest) -> dict[str, str]:
    return {k: (v[0] if isinstance(v, list) else v) for k, v in app.query_params.items()}


def html_bodies(app: AppTest) -> list[str]:
    return [e.proto.body for e in app.get("html")]


# Combined dashboard


def test_first_load_uses_defaults_and_normalizes_the_url() -> None:
    app = run(make(COMBINED))
    assert body(app) == "BODY Module 2 / Calibration"
    assert app.sidebar.selectbox[0].label == "Module"
    assert app.sidebar.selectbox[0].options == ["Module 2", "Module 4", "Module 5-6"]
    assert query(app) == {"module": "module-2", "page": "calibration"}


def test_page_radio_is_native_and_the_first_radio() -> None:
    # The page radio is the first (and only) sidebar radio. AppTest lists main-area widgets
    # before sidebar widgets, so on a page without radios it is also app.radio[0], exactly
    # as before this shell existed.
    app = run(make(COMBINED, module="module-4", page="rgb-human-boundary"))
    assert app.radio[0].label == "Page" and app.sidebar.radio[0].label == "Page"
    run(app.radio[0].set_value("Comparison and Evaluation"))
    assert [r.label for r in app.sidebar.radio] == ["Page"]
    assert app.sidebar.radio[0].options == ["RGB Human Boundary", "Comparison and Evaluation"]
    assert [r.label for r in app.main.radio] == ["Page-level choice"]


def test_direct_valid_deep_link() -> None:
    app = run(make(COMBINED, module="module-5-6", page="experiments-results"))
    assert body(app) == "BODY Module 5-6 / Experiments & Results"
    assert app.sidebar.selectbox[0].value == "Module 5-6"
    assert app.radio[0].value == "Experiments & Results"
    assert query(app) == {"module": "module-5-6", "page": "experiments-results"}


def test_valid_module_with_invalid_page_keeps_the_module() -> None:
    app = run(make(COMBINED, module="module-4", page="motion-tracking"))
    assert body(app) == "BODY Module 4 / RGB Human Boundary"
    assert query(app) == {"module": "module-4", "page": "rgb-human-boundary"}


def test_invalid_module_falls_back_to_the_default() -> None:
    app = run(make(COMBINED, module="module-99", page="motion-tracking"))
    assert body(app) == "BODY Module 2 / Calibration"
    assert query(app) == {"module": "module-2", "page": "calibration"}


def test_unrelated_query_parameters_are_preserved() -> None:
    app = run(make(COMBINED, module="module-4", page="nope", embed="true"))
    assert query(app) == {"module": "module-4", "page": "rgb-human-boundary", "embed": "true"}


def test_changing_page_updates_the_url() -> None:
    app = run(make(COMBINED))
    run(app.radio[0].set_value("Theory"))
    assert body(app) == "BODY Module 2 / Theory"
    assert query(app) == {"module": "module-2", "page": "theory"}


def test_changing_module_selects_that_modules_page_and_remembers_the_old_one() -> None:
    app = run(make(COMBINED))
    run(app.radio[0].set_value("Theory"))
    run(app.sidebar.selectbox[0].set_value("Module 5-6"))
    assert body(app) == "BODY Module 5-6 / Motion Tracking"
    assert app.radio[0].options == ["Motion Tracking", "Experiments & Results"]
    assert query(app) == {"module": "module-5-6", "page": "motion-tracking"}
    run(app.sidebar.selectbox[0].set_value("Module 2"))
    assert body(app) == "BODY Module 2 / Theory"
    assert query(app) == {"module": "module-2", "page": "theory"}


def test_refresh_and_copied_url_restore_the_page_in_a_new_session() -> None:
    first = run(make(COMBINED))
    run(first.sidebar.selectbox[0].set_value("Module 4"))
    run(first.radio[0].set_value("Comparison and Evaluation"))
    copied = query(first)
    second = run(make(COMBINED, **copied))
    assert body(second) == "BODY Module 4 / Comparison and Evaluation"
    assert query(second) == copied


def test_url_is_read_once_so_widgets_and_url_never_fight() -> None:
    app = run(make(COMBINED, module="module-4", page="rgb-human-boundary"))
    app.query_params["module"] = "module-2"  # stale outside change within the same session
    app.query_params["page"] = "theory"
    run(app)
    assert body(app) == "BODY Module 4 / RGB Human Boundary"
    assert query(app) == {"module": "module-4", "page": "rgb-human-boundary"}
    run(app)  # a further rerun changes nothing
    assert query(app) == {"module": "module-4", "page": "rgb-human-boundary"}


def test_every_registered_page_is_reachable() -> None:
    app = run(make(COMBINED))
    reached = []
    for module in list(app.sidebar.selectbox[0].options):
        run(app.sidebar.selectbox[0].set_value(module))
        for label in list(app.radio[0].options):
            run(app.radio[0].set_value(label))
            reached.append(body(app))
    assert len(reached) == 6 and len(set(reached)) == 6


def test_breadcrumbs_footer_and_notices() -> None:
    app = run(make(COMBINED, module="module-5-6", page="motion-tracking"))
    crumbs = next(b for b in html_bodies(app) if "Breadcrumb" in b)
    assert "CSc 8830" in crumbs and "Module 5-6" in crumbs
    assert '<li aria-current="page"><span class="csc8830-breadcrumbs-sep" aria-hidden="true">/</span>Motion Tracking</li>' in crumbs
    assert app.main.caption[-1].value == "CSc 8830 Computer Vision · Georgia State University"
    assert app.sidebar.expander[0].label == "Dashboard notices"


def test_identity_keeps_exact_capitalization_and_no_page_heading_is_added() -> None:
    app = run(make(COMBINED))
    identity = next(b for b in html_bodies(app) if "csc8830-identity" in b)
    assert ">CSc 8830</h1>" in identity and ">Computer Vision</p>" in identity
    assert not app.header and not app.title  # pages own their headers


# Standalone module app


def test_standalone_shows_module_as_text_without_a_selectbox() -> None:
    app = run(make(STANDALONE))
    assert not app.selectbox
    assert any(m.value == "**Module 4**" for m in app.sidebar.markdown)
    assert app.radio[0].label == "Page"
    assert app.radio[0].options == ["RGB Human Boundary", "Comparison and Evaluation"]
    labels = [b for b in html_bodies(app) if "csc8830-nav-label" in b]
    assert [">Module<" in labels[0], ">Pages<" in labels[1]] == [True, True]


def test_standalone_page_context_and_no_url_management() -> None:
    app = run(make(STANDALONE, unrelated="1"))
    assert app.sidebar.caption[-1].value == "Context for RGB Human Boundary"
    run(app.radio[0].set_value("Comparison and Evaluation"))
    assert app.sidebar.caption[-1].value == "Context for Comparison and Evaluation"
    assert query(app) == {"unrelated": "1"}
    crumbs = next(b for b in html_bodies(app) if "Breadcrumb" in b)
    assert "Module 4" in crumbs and "Comparison and Evaluation" in crumbs


def test_standalone_with_several_modules_fails_clearly() -> None:
    app = make('render_shell(PAGES, page_title="x", standalone=True)').run()
    assert app.exception and "exactly one module" in app.exception[0].value


def test_no_pages_shows_the_empty_message() -> None:
    app = run(make('render_shell([], page_title="x", empty_message="No module pages are registered.")'))
    assert [e.value for e in app.error] == ["No module pages are registered."]


# Home (combined dashboards)

HOMED = 'render_shell(PAGES, page_title="x", sync_query_params=True, home=HomeSpec(render=home_render))'


def home_body(app: AppTest) -> str | None:
    return next((m.value for m in app.markdown if m.value.startswith("HOME ")), None)


def crumbs(app: AppTest) -> str:
    return next(b for b in html_bodies(app) if "Breadcrumb" in b)


def test_no_owned_params_opens_home() -> None:
    app = run(make(HOMED))
    assert home_body(app) == (
        "HOME module-2:2:Calibration module-4:2:RGB Human Boundary module-5-6:2:Motion Tracking"
    )
    assert app.sidebar.selectbox[0].options == ["Home", "Module 2", "Module 4", "Module 5-6"]
    assert app.sidebar.selectbox[0].value == "Home"
    assert not app.sidebar.radio  # no fake page selection on Home
    assert not any(m.value.startswith("BODY ") for m in app.markdown)
    assert query(app) == {"module": "home"}


def test_home_breadcrumb_is_current_and_not_a_link() -> None:
    app = run(make(HOMED, module="home"))
    html = crumbs(app)
    assert '<li aria-current="page"><span class="csc8830-breadcrumbs-sep" aria-hidden="true">/</span>Home</li>' in html
    assert "<a " not in html
    assert app.main.caption[-1].value.startswith("CSc 8830 Computer Vision")  # footer stays


@pytest.mark.parametrize("params", [{"module": "nope"}, {"module": "nope", "page": "theory"}, {"page": "theory"}])
def test_unknown_or_missing_module_opens_home_and_drops_page(params) -> None:
    app = run(make(HOMED, **params))
    assert home_body(app) is not None
    assert query(app) == {"module": "home"}


def test_deep_links_bypass_home() -> None:
    app = run(make(HOMED, module="module-5-6", page="experiments-results", keep="1"))
    assert home_body(app) is None
    assert body(app) == "BODY Module 5-6 / Experiments & Results"
    assert query(app) == {"module": "module-5-6", "page": "experiments-results", "keep": "1"}
    assert "<a " not in crumbs(app)  # plain text: a link would desync the address bar on Cloud


def test_valid_module_with_invalid_page_still_opens_its_first_page() -> None:
    app = run(make(HOMED, module="module-4", page="nope"))
    assert body(app) == "BODY Module 4 / RGB Human Boundary"
    assert query(app) == {"module": "module-4", "page": "rgb-human-boundary"}


def test_open_module_selects_the_registry_first_page_and_syncs_the_url() -> None:
    app = run(make(HOMED, keep="1"))
    run(app.button(key="open_module-5-6").click())
    assert body(app) == "BODY Module 5-6 / Motion Tracking"
    assert app.sidebar.selectbox[0].value == "Module 5-6"
    assert app.sidebar.radio[0].value == "Motion Tracking"
    assert query(app) == {"keep": "1", "module": "module-5-6", "page": "motion-tracking"}


def test_choosing_home_in_the_selectbox_returns_home_and_removes_page() -> None:
    app = run(make(HOMED, module="module-4", page="rgb-human-boundary"))
    run(app.sidebar.selectbox[0].set_value("Home"))
    assert home_body(app) is not None
    assert query(app) == {"module": "home"}


def test_home_without_url_sync_still_defaults_to_home() -> None:
    app = run(make('render_shell(PAGES, page_title="x", home=HomeSpec(render=home_render))'))
    assert home_body(app) is not None
    assert query(app) == {}


def test_standalone_apps_cannot_have_home() -> None:
    app = make('render_shell(M4, page_title="x", standalone=True, home=HomeSpec(render=home_render))').run()
    assert app.exception and "combined dashboards" in app.exception[0].value


def test_top_nav_label_is_configurable() -> None:
    app = run(make('render_shell(PAGES, page_title="x", home=HomeSpec(render=home_render), top_nav_label="Explore")'))
    assert any(">Explore<" in b for b in html_bodies(app))
