import os
import streamlit as st
from dotenv import load_dotenv
from app.components import render_footer, vega_buttons
from app.theme_utils import get_theme_class, get_vega_imports

load_dotenv(".env.local")

base_url = os.getenv("API_BASE_URL", "http://localhost:8501")

st.components.v1.html(f"""
{get_vega_imports()}

<div {get_theme_class()}>
<vega-font
  variant="font-h1"
  as="h1"
  style="font-weight: bold; font-size: 4rem;"
>
  🔌 Starlette API Demo
</vega-font>
</div>
""", height=120)

st.markdown("""
This app uses Streamlit's experimental **`App` class** from `streamlit.starlette`
to mount custom routes alongside the Streamlit UI.

Routes are registered in `app/endpoints.py` and wired up in `app/run.py`:

```python
from streamlit.starlette import App
from app.endpoints import routes

app = App("app/main.py", routes=routes)
```

| Endpoint | Method | Description |
|---|---|---|
| `/f1/schedule` | GET | F1 event schedule |
| `/health` | GET | Health check |
| `/custom/info` | GET | App metadata |
| `/custom/echo` | POST | Echo JSON payload |
""")

st.info("Run with streamlit run app/run.py or any ASGI server via uvicorn app.run:app")

with st.expander("Try the API endpoints", expanded=True):
    col_code, col_empty = st.columns([1, 1])

    with col_code:
        st.code(f"curl {base_url}/f1/schedule?year=2025", language="bash")

        st.code(f"curl {base_url}/health", language="bash")

        st.code(f"curl {base_url}/custom/info", language="bash")

        st.code(
            f'curl -X POST {base_url}/custom/echo \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -d \'{"message": "hello"}\'',
            language="bash",
        )

        vega_buttons([
            {"label": "Open /f1/schedule", "href": f"{base_url}/f1/schedule?year=2025", "icon": "fas fa-calendar-days", "variant": "secondary", "iconAlign": "left"},
            {"label": "Open /health", "href": f"{base_url}/health", "icon": "fas fa-heart-pulse", "variant": "secondary", "iconAlign": "left"},
            {"label": "Open /custom/info", "href": f"{base_url}/custom/info", "icon": "fas fa-info-circle", "variant": "secondary", "iconAlign": "right"},
        ])

# Footer with country flag
st.divider()
render_footer()
