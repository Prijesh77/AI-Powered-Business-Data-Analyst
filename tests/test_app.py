"""Smoke tests: every page renders without errors, using Streamlit's AppTest runner."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import ui_state
from src.analytics.definitions import ONLINE_RETAIL_II_MAPPING, ONLINE_RETAIL_RULES

APP = str(Path(__file__).resolve().parent.parent / "app.py")
PAGES = ["pages/home.py", "pages/upload.py", "pages/data_quality.py", "pages/dashboard.py"]


def run(page: str, session: dict | None = None) -> AppTest:
    app = AppTest.from_file(APP, default_timeout=60)
    for key, value in (session or {}).items():
        app.session_state[key] = value
    app.run()
    if page != "pages/home.py":
        app.switch_page(page).run()
    return app


@pytest.mark.parametrize("page", PAGES)
def test_pages_render_without_data(page):
    app = run(page)
    assert not app.exception


@pytest.fixture
def loaded_session(raw_sample):
    return {
        ui_state.RAW: raw_sample, ui_state.FILE_NAME: "sample.csv", ui_state.LOAD_NOTES: [],
        ui_state.UPLOAD_ID: 1, ui_state.MAPPING: ONLINE_RETAIL_II_MAPPING,
        ui_state.RULES: ONLINE_RETAIL_RULES, ui_state.DAYFIRST: False, ui_state.CURRENCY: "GBP",
    }


def test_full_flow_builds_table_and_dashboard(loaded_session):
    app = run("pages/data_quality.py", loaded_session)
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert len(app.session_state[ui_state.TRANSACTIONS]) == 13

    app.switch_page("pages/dashboard.py").run()
    assert not app.exception
    net_sales_card = next(m for m in app.metric if m.label == "Net sales (revenue)")
    assert net_sales_card.value == "GBP 185.00"


def test_upload_page_prefills_mapping(loaded_session):
    del loaded_session[ui_state.MAPPING]
    app = run("pages/upload.py", loaded_session)
    assert not app.exception
    assert app.selectbox(key="map_unit_price_1").value == "Price"
