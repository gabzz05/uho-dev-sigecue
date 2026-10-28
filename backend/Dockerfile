# Imagen del backend: Django + gunicorn. La usan también el worker y beat de Celery.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# WeasyPrint (exportación a PDF) necesita Pango y HarfBuzz; las fuentes DejaVu
# son las del membrete. Así el PDF funciona sin instalar nada en el host.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 \
        fonts-dejavu-core shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements/ requirements/
RUN pip install -r requirements/prod.txt

COPY . .

# Usuario sin privilegios; carpetas de datos que se montan como volúmenes.
RUN useradd --system --uid 1000 --home /app sigecue \
    && mkdir -p /data/media /data/media_publica /app/staticfiles /app/logs \
    && chown -R sigecue:sigecue /data /app/staticfiles /app/logs \
    && chmod +x docker/entrypoint.sh
USER sigecue

EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
