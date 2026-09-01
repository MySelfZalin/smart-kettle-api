FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libffi-dev tzdata \
    && ln -snf /usr/share/zoneinfo/Europe/Moscow /etc/localtime \
    && echo Europe/Moscow > /etc/timezone \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY config.py .
COPY devices ./devices
COPY fast_api ./fast_api
COPY tg_bot ./tg_bot

EXPOSE 8000

CMD ["python", "-m", "fast_api.main"]
