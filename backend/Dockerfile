FROM python:3.11-slim

WORKDIR /app

# Copiamos todo el backend
COPY . .

# Instalamos dependencias
RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080

CMD bash -lc "python -m alembic upgrade head && python -m uvicorn services.accounts.main:app --host 0.0.0.0 --port ${PORT}"
