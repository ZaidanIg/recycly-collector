FROM python:3.9-slim-bullseye

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends gcc && \
	pip install --no-cache-dir -r requirements.txt && \
	apt-get purge -y --auto-remove gcc && \
	rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 5001

CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0:5001", "run:app"]