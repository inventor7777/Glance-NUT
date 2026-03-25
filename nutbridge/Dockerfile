FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nut-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app.py /app/app.py

EXPOSE 3494

CMD ["python", "/app/app.py"]
