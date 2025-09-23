# This Dockerfile uses the local build context.

# ---- Base ----
FROM node:18-alpine AS base
WORKDIR /app

# ---- Frontend Dependencies ----
FROM base AS frontend-deps
WORKDIR /app/next-maikado-app
COPY next-maikado-app/package.json next-maikado-app/package-lock.json* ./
RUN npm install

# ---- Frontend Builder ----
FROM base AS frontend-builder
WORKDIR /app/next-maikado-app
COPY --from=frontend-deps /app/next-maikado-app/node_modules ./node_modules
COPY next-maikado-app/ .
RUN npm run build

# ---- Production ----
FROM node:18-alpine AS production
# Install Python and pip
RUN apk add --no-cache python3 py3-pip
WORKDIR /app

# Install backend dependencies directly on Alpine
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --break-system-packages -r backend/requirements.txt

# Copy backend source code
COPY backend/ ./backend

# Copy frontend build artifacts
COPY --from=frontend-builder /app/next-maikado-app/.next ./next-maikado-app/.next
COPY --from=frontend-builder /app/next-maikado-app/public ./next-maikado-app/public
COPY --from=frontend-builder /app/next-maikado-app/package.json ./next-maikado-app/package.json

# We need to install production dependencies for the frontend to run
WORKDIR /app/next-maikado-app
RUN npm install --omit=dev
WORKDIR /app

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 3000 8000

CMD ["./start.sh"]
