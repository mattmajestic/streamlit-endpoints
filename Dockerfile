FROM python:3.11-slim

# Keeps Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Tell Streamlit not to open a browser
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY .streamlit/ /root/.streamlit/
COPY app/ ./app/

EXPOSE 8501

# Run via Streamlit — auto-detects the App instance in run.py
CMD ["streamlit", "run", "app/run.py"]
