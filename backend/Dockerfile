FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# media/ exists in the image so the named volume inherits the app user's ownership
RUN mkdir -p /app/media && useradd -m app && chown -R app /app
USER app
EXPOSE 8000
# migrate, seed only if empty, then serve
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --workers 2"]
