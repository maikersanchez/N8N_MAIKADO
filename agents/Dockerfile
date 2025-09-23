FROM python:3.9-slim

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all agent source code
COPY . .

# Expose the port the main app will run on
EXPOSE 8001

# Run the main orchestrator app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
