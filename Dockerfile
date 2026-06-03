# Slim Python base keeps the image small. Matches the 3.14 used in development.
FROM python:3.14-slim

# Don't write .pyc files; stream stdout/stderr straight to the logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first, in their own layer. Docker caches this layer and
# only rebuilds it when requirements.txt changes — so editing app code doesn't
# trigger a full reinstall.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code.
COPY app ./app

EXPOSE 8000

# Start the ASGI server. 0.0.0.0 so it's reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
