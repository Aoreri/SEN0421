# syntax=docker/dockerfile:1
FROM node:22-alpine AS build
WORKDIR /app
COPY . .
# Optional CA bundle for builds behind a TLS-inspecting development proxy.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca; fi; \
    npm ci && npm run build && rm -rf node_modules /root/.npm

FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
