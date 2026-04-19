import os
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as st_components

_BASE = os.getenv("API_BASE_URL", "http://localhost:8501")
_COMPONENTS_DIR = Path(__file__).resolve().parent

_vega_metrics = st_components.declare_component("vega_metrics", url=f"{_BASE}/components/vega_metrics")
_vega_buttons = st_components.declare_component("vega_buttons", url=f"{_BASE}/components/vega_buttons")


def vega_metrics(data: list, key=None):
    return _vega_metrics(metrics=data, key=key, default=None)


def vega_buttons(data: list, key=None):
    return _vega_buttons(buttons=data, key=key, default=None)


def render_footer(height: int = 80):
    footer_html = (_COMPONENTS_DIR / "footer" / "index.html").read_text(encoding="utf-8")
    st.components.v1.html(footer_html, height=height)
