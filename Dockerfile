FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements/api-lock.txt ./requirements/api-lock.txt
RUN pip install --no-cache-dir -r requirements/api-lock.txt && useradd --create-home appuser
COPY backend/__init__.py ./backend/
COPY backend/api ./backend/api
COPY backend/core ./backend/core
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
