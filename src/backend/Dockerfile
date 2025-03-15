# Use Python slim image to minimize container size
FROM python:3.11-slim

# Add metadata labels to the image
LABEL maintainer="Budget Management Team <njdifiore@gmail.com>" \
      description="Budget Management Application for automated financial tracking and analysis" \
      version="1.0.0"

# Set environment variables to optimize Python execution in container
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory for application code
WORKDIR /app

# Install system dependencies required for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends gcc && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code to container
COPY . .

# Ensure main script is executable
RUN chmod +x main.py

# Set default command to run the application
CMD ["python", "main.py"]