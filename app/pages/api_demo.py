import streamlit as st

st.title("🔌 Starlette API Demo")

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
| `/health` | GET | Health check |
| `/custom/info` | GET | App metadata |
| `/custom/echo` | POST | Echo JSON payload |
""")

st.info(
    "Run with `streamlit run app/run.py` or any ASGI server via `uvicorn app.run:app`.",
    icon="ℹ️",
)

with st.expander("Try the API endpoints"):
    st.code("curl http://localhost:8501/health", language="bash")
    st.code("curl http://localhost:8501/custom/info", language="bash")
    st.code(
        'curl -X POST http://localhost:8501/custom/echo \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"message": "hello"}\'',
        language="bash",
    )
