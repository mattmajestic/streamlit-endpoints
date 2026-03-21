# Streamlit with Endpoints

A test bed for Streamlit's experimental Starlette server integration. Deployed on Render and Streamlit Cloud to validate custom API route mounting.

[![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://update-this.onrender.com)
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://update-this.streamlit.app)

---

## What this tests

- Running Streamlit with Starlette as the underlying server (`useStarlette = true`)
- Mounting custom HTTP routes alongside the Streamlit UI via `streamlit.starlette.App`

## Pages

**FastF1 Analytics** — Race and qualifying data from the FastF1 package. Select a season, grand prix, and session to see results, lap time charts, and tyre compound breakdowns.

**API Demo** — Documents the custom Starlette routes mounted alongside the app and provides curl examples to test them.

## Custom API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check (used by Docker and Render) |
| `/custom/info` | GET | App metadata |
| `/custom/echo` | POST | Echo a JSON payload |

## Running locally

```bash
docker compose up --build
```

App available at `http://localhost:8501`.

## Stack

- [Streamlit](https://streamlit.io) with experimental Starlette server
- [render.com](https://onrender.com) for Docker testing
- [FastF1](https://docs.fastf1.dev) for F1 session data
- [Starlette](https://www.starlette.io) for custom ASGI routes
