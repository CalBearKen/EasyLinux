FROM python:3.9-slim

WORKDIR /app

# Install basic utilities that might be missing in slim image
RUN apt-get update && apt-get install -y \
    findutils \
    grep \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create some test files and directories
RUN mkdir -p /app/test/logs && \
    echo "This is a test file\nIt has multiple lines\nSome lines have errors\nERROR: test error" > /app/test/test.txt && \
    echo "Python test file" > /app/test/test.py && \
    echo "ERROR: Another error\nInfo: normal log" > /app/test/logs/app.log && \
    echo "Test data 1\nTest data 2\nTest data 1" > /app/test/data.txt

COPY docker/app.py .
COPY agent.py .
COPY .env .

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"] 