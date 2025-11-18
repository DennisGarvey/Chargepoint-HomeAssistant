FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies from requirements and copy app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Entrypoint translates environment variables into CLI args
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command (will be overridden by entrypoint if env provided)
CMD ["--help"]
