ARG HOST=0.0.0.0
ARG PORT=8050

FROM python:3.13-slim

ARG HOST
ARG PORT

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml uv.lock ./
COPY src/ ./src/

RUN uv sync --no-dev --frozen

EXPOSE ${PORT}

ENV SERVER_HOST=${HOST}
ENV SERVER_PORT=${PORT}
ENV SERVER_TRANSPORT=sse

CMD ["uv", "run", "--no-dev", "src/server/main.py"]
