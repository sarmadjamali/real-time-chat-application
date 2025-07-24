# Use official Python base image
FROM python:3.10.12

# Set working directory
WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Run the FastAPI app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
