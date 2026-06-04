FROM python:3.9-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc
RUN pip install --no-cache-dir fastapi uvicorn psycopg2-binary
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]