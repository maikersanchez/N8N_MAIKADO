FROM python:3.9-slim

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libnss3 \
       libnspr4 \
       libdbus-1-3 \
       libatk1.0-0 \
       libatk-bridge2.0-0 \
       libcups2 \
       libatspi2.0-0 \
       libxcomposite1 \
       libxdamage1 \
       libxfixes3 \
       libxrandr2 \
       libgbm1 \
       libpango-1.0-0 \
       libcairo2 \
       libasound2 \
    # Install browsers without the --with-deps flag
    && playwright install \
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# Copy all agent source code
COPY . .

# Expose the port the main app will run on
EXPOSE 8001

# Run the main orchestrator app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
