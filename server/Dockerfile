FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Runs as a non-root user for defense in depth (this process handles
# caller-supplied Cognigy API keys on every request).
RUN useradd --no-create-home --shell /usr/sbin/nologin mcp
USER mcp

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
