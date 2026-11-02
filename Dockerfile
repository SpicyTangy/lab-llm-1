FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY assistente/ assistente/

RUN useradd --create-home app
USER app

CMD ["python", "-m", "assistente"]
