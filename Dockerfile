FROM python:3.12-slim


ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1



WORKDIR /app

RUN pip install poetry


COPY pyproject.toml poetry.lock* ./


RUN poetry install --no-root --only main


COPY src/ ./src/


CMD ["python", "-m", "src.main"]