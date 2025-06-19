FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p data

# Run the application
CMD ["python", "apartment_tracker.py"] 