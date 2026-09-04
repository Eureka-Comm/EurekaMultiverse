# ============================================================
# EUREKA MULTIVERSE — Frontend image (multi-stage)
# Stage 1: Node -> npm ci + build (produces dist/)
# Stage 2: nginx serves dist/ and reverse-proxies /api -> backend
#          (same-origin routing: the browser never needs the backend
#           URL and never sees any API key).
# ============================================================

# ---- Stage 1: build ----
FROM node:22-alpine AS build
WORKDIR /app

# Public origin the BROWSER uses to reach the frontend+API (same-origin).
# For local docker-compose this is e.g. http://localhost:5173; in prod set it
# to the real public domain. It is baked into the bundle ONLY as the API base,
# never as a secret.
ARG VITE_EUREKA_API_URL=http://localhost:5173
ENV VITE_EUREKA_API_URL=$VITE_EUREKA_API_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Stage 2: production static server + /api proxy ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
# No DEEPSEEK_API_KEY is present anywhere in this image (it lives only on the backend).
CMD ["nginx", "-g", "daemon off;"]
