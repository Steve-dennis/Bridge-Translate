FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --upgrade pip && \
    pip install --no-cache-dir discord.py argostranslate langdetect

COPY autoTranslate.py /app/autoTranslate.py

VOLUME ["/root/.local/share/argos-translate", "/app"]

CMD ["python", "autoTranslate.py"]
