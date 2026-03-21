"""
ASGI entry-point using Streamlit's experimental App class.

Run with Streamlit (preferred):
    streamlit run app/run.py

Or with any ASGI server directly:
    uvicorn app.run:app --host 0.0.0.0 --port 8501
"""

import sys
import os

# Ensure the project root is on sys.path regardless of how this module is
# loaded (streamlit run, uvicorn import, or direct python execution).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.starlette import App
from app.endpoints import routes

app = App("main.py", routes=routes)
