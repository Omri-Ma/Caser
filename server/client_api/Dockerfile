FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY client_api ./client_api

CMD ["python", "-m", "uvicorn", "client_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
