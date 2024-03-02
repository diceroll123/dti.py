FROM python:3.12-alpine

RUN apk add --no-cache \
    curl \
    gcc \
    libressl-dev \
    musl-dev \
    libffi-dev \
    build-base \
    linux-headers \
    git

WORKDIR /app

COPY . .

RUN pip install uv

ENV PATH="$HOME/.cargo/bin:${PATH}"

RUN uv pip install --system -r requirements.txt && uv pip install --system -r dev-requirements.txt
