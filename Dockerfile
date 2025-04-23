FROM python:3.10-slim

WORKDIR /app

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd --gid $GROUP_ID nonroot && \
    useradd --uid $USER_ID --gid nonroot --shell /bin/bash --create-home nonroot

RUN pip install poetry

COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false && poetry install --no-root

USER nonroot

COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
