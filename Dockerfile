FROM python:3.11-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends gcc && \
	pip install --no-cache-dir -r requirements.txt && \
	apt-get purge -y --auto-remove gcc && \
	rm -rf /var/lib/apt/lists/*

COPY . .

ENV FLASK_APP=run.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5001

CMD ["gunicorn", "--workers", "1", "--worker-class", "gevent", "--bind", "0.0.0:5001", "run:app"]