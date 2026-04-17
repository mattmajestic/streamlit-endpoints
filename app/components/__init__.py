import os
import streamlit.components.v1 as st_components

_BASE = os.getenv("API_BASE_URL", "http://localhost:8501")

_vega_banner = st_components.declare_component("vega_banner", url=f"{_BASE}/components/vega_banner")
_vega_metrics = st_components.declare_component("vega_metrics", url=f"{_BASE}/components/vega_metrics")
_vega_buttons = st_components.declare_component("vega_buttons", url=f"{_BASE}/components/vega_buttons")
_vega_select = st_components.declare_component("vega_select", url=f"{_BASE}/components/vega_select")


def vega_banner(message: str, type: str = "info", key=None):
    return _vega_banner(message=message, type=type, key=key, default=None)


def vega_metrics(metrics: list[dict], key=None):
    """metrics: list of {"label": str, "value": str}"""
    return _vega_metrics(metrics=metrics, key=key, default=None)


def vega_buttons(buttons: list[dict], key=None):
    """buttons: list of {"label": str, "href": str (optional), "type": str (optional)}"""
    return _vega_buttons(buttons=buttons, key=key, default=None)


def vega_select(label: str, options: list, index: int = 0, key: str = None):
    """Returns the selected value (same type as the input options)."""
    default = options[index] if options else None
    str_opts = [str(o) for o in options]
    result = _vega_select(
        label=label,
        options=str_opts,
        value=str(default) if default is not None else None,
        key=key,
        default=str(default) if default is not None else None,
    )
    # Match result string back to original typed option
    for opt in options:
        if str(opt) == str(result):
            return opt
    return default
