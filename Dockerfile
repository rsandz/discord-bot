# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy project files
COPY pyproject.toml poetry.lock* ./
COPY hangoutsscheduler/ ./hangoutsscheduler/
COPY README.md ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1