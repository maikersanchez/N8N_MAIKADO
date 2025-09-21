# ---- Base ----
FROM node:18-alpine AS base
WORKDIR /app

# ---- Backend Dependencies ----
FROM python:3.9-slim AS backend-deps
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
FROM python:3.9-slim AS production
WORKDIR /app

# Copy backend
COPY --from=backend-deps /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY backend/ ./backend

# Copy frontend
COPY --from=frontend-builder /app/next-maikado-app/.next ./next-maikado-app/.next
COPY --from=frontend-builder /app/next-maikado-app/node_modules ./next-maikado-app/node_modules
COPY --from=frontend-builder /app/next-maikado-app/package.json ./next-maikado-app/package.json
COPY next-maikado-app/public ./next-maikado-app/public

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 3000 8000

CMD ["./start.sh"]
