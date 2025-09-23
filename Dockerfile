# ---- Source ----
# This stage clones the repository and its submodules
FROM node:18-alpine AS source
RUN apk add --no-cache git
WORKDIR /app
# Clone the main repository
RUN git clone https://github.com/maikersanchez/N8N_MAIKADO.git .
# Initialize and update submodules
RUN git submodule update --init --recursive

# ---- Base ----
FROM node:18-alpine AS base
WORKDIR /app

# ---- Backend Dependencies ----
FROM python:3.9-slim AS backend-deps
WORKDIR /app
COPY --from=source /app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Frontend Dependencies ----
FROM base AS frontend-deps
WORKDIR /app/next-maikado-app
COPY --from=source /app/next-maikado-app/package.json /app/next-maikado-app/package-lock.json* ./
RUN npm install

# ---- Frontend Builder ----
FROM base AS frontend-builder
WORKDIR /app/next-maikado-app
COPY --from=frontend-deps /app/next-maikado-app/node_modules ./node_modules
COPY --from=source /app/next-maikado-app/ .
RUN npm run build

# ---- Production ----
FROM node:18-alpine AS production
RUN apk add --no-cache python3 py3-pip
WORKDIR /app

# Copy backend
COPY --from=backend-deps /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=source /app/backend/ ./backend

# Copy frontend
COPY --from=frontend-builder /app/next-maikado-app/.next ./next-maikado-app/.next
COPY --from=frontend-builder /app/next-maikado-app/node_modules ./next-maikado-app/node_modules
COPY --from=frontend-builder /app/next-maikado-app/package.json ./next-maikado-app/package.json
COPY --from=source /app/next-maikado-app/public ./next-maikado-app/public

# Copy startup script
COPY --from=source /app/start.sh .
RUN chmod +x start.sh

EXPOSE 3000 8000

CMD ["./start.sh"]