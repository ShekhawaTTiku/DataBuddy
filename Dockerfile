FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements-api-lock.txt ./
RUN pip install --no-cache-dir -r requirements-api-lock.txt && useradd --create-home appuser
COPY api ./api
COPY prompts ./prompts
COPY analyst.py config.py conversation_state.py databuddy.py dataset_profiler.py dataset_state.py execution_policy.py executor.py _runner.py llm_clients.py message_handler.py telemetry.py ./
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
