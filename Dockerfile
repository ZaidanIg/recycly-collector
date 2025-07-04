FROM python:3.10-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends gcc && \
	pip install --no-cache-dir -r requirements.txt && \
	apt-get purge -y --auto-remove gcc && \
	rm -rf /var/lib/apt/lists/*

COPY . .

ENV FLASK_APP=wsgi.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 5001

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0:5001", "wsgi:app"]