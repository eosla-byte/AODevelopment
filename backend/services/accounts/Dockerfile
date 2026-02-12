FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r backend/requirements.txt
ENV PORT=8080
CMD bash -lc "cd backend && python -m alembic upgrade head && python -m uvicorn services.accounts.main:app --host 0.0.0.0 --port ${PORT}"
