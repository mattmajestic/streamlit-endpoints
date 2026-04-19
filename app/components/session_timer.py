from __future__ import annotations

import streamlit as st


HTML_CONTENT = """
<div id="ws-output" style="
    padding: 1.1rem;
    background: rgba(240, 242, 246, 0.92);
    border-radius: 0.75rem;
    border: 1px solid rgba(128, 128, 128, 0.18);
    font-family: monospace;
    font-size: 1.1rem;
    color: #31333F;
    text-align: center;
">
    <div id="ws-clock" style="
        font-size: 2rem;
        color: #ff4b4b;
        line-height: 1;
        font-variant-numeric: tabular-nums;
        font-feature-settings: 'tnum' 1;
        min-width: 5ch;
    ">00:00</div>
</div>
"""


JS_CONTENT = """
export default function(component) {
    const { data, parentElement } = component;
    const label = data?.label || "Streamlit Session Timer";
    const duration = Number(data?.duration || 0);
    const outputEl = parentElement.querySelector("#ws-output");
    const clockEl = parentElement.querySelector("#ws-clock");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/session-timer?label=${encodeURIComponent(label)}&duration=${duration}`;

    let ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        if (!outputEl || !clockEl) return;
        try {
            const wsData = JSON.parse(event.data);
            clockEl.textContent = wsData.elapsed || "00:00";
        } catch (err) {
            outputEl.textContent = "Timer unavailable";
        }
    };

    ws.onclose = () => {
        // No extra status UI.
    };

    ws.onerror = () => {
        if (outputEl) outputEl.textContent = "Timer unavailable";
    };

    return () => {
        try {
            ws.close();
        } catch (err) {
            // Ignore cleanup failures.
        }
    };
}
"""


_SESSION_TIMER = st.components.v2.component(
    name="session_timer",
    html=HTML_CONTENT,
    js=JS_CONTENT,
    isolate_styles=False,
)


def render_session_timer(label: str, duration_seconds: int = 0, height: int = 170):
    return _SESSION_TIMER(
        data={"label": label, "duration": duration_seconds},
        height=height,
    )
