FROM python:3.9-slim

WORKDIR /app

COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY docker/app.py .
COPY agent.py .
COPY .env .

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"] 