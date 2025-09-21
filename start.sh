#!/bin/sh
# Start the backend
echo "Starting backend..."
cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start the frontend
echo "Starting frontend..."
cd /app/next-maikado-app
npm start
