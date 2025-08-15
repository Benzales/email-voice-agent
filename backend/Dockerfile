FROM python:3.11-slim

# Install Node for MCP Gmail server via npx
RUN apt-get update && apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy entire project so local modules are importable (mcp_agent, etc.)
COPY . /app
RUN ls -la /app

ENV PYTHONPATH=/app
ENV MCP_CONFIG_PATH=/app/mcp_agent.config.yaml

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]


