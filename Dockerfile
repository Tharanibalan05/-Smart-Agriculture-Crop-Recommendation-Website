# Use an official Python slim base image compatible with scikit-learn and Streamlit
FROM python:3.11-slim

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for native library compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies manifest and install packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py auth_db.py utils.py config.py ./
COPY weather_service.py market_service.py soil_analysis.py risk_engine.py report_generator.py ./
COPY crop_model.pkl crop_economics.csv crop_recommendation_*.csv ./
COPY manifest.json service-worker.js icon-*.png ./

# Create runtime data directory and non-root user for container execution safety
RUN mkdir -p /app/data && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Default Streamlit port (Render dynamically overrides $PORT at runtime)
EXPOSE 8501

# Bind Streamlit to 0.0.0.0 and dynamic Render $PORT
CMD ["sh", "-c", "streamlit run app.py --server.address=0.0.0.0 --server.port=${PORT:-8501}"]
