# Use official Python slim image
FROM python:3.11-slim

WORKDIR /app

# 1. Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps

# 2. Copy application code
COPY api_server.py ./

# 3. Expose port & run
EXPOSE 8000
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
