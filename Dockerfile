FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY workflow_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY workflow_service/ ./workflow_service/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "workflow_service.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
