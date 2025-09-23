#!/bin/sh

# Set the script to exit immediately if a command exits with a non-zero status
set -e

# Start the backend server in the background
echo "Starting backend..."
(cd backend && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000) &

# Start the frontend server in the foreground
echo "Starting frontend..."
cd next-maikado-app
npm start