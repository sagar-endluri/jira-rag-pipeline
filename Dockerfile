# Use Python 3.12 slim base image
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the jira-rag-pipeline folder
COPY jira-rag-pipeline /app
COPY .env /app
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask port
EXPOSE 8800

# Run with Uvicorn for production
CMD ["uvicorn", "-b", "0.0.0.0:8800", "wsgi:app"]
