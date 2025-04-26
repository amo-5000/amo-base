FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories
RUN mkdir -p logs assets

# Environment variables
ENV PORT=8501

# Expose the port
EXPOSE $PORT

# Set streamlit config
RUN mkdir -p /root/.streamlit
RUN echo "[server]" > /root/.streamlit/config.toml
RUN echo "headless = true" >> /root/.streamlit/config.toml
RUN echo "enableCORS = false" >> /root/.streamlit/config.toml
RUN echo "port = $PORT" >> /root/.streamlit/config.toml

# Set healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start the application
CMD streamlit run streamlit_app.py 