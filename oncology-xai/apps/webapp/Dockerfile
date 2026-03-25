FROM node:20-alpine AS builder

WORKDIR /app
COPY apps/webapp/package.json apps/webapp/package-lock.json* ./
RUN npm install

COPY apps/webapp/ .

ARG VITE_API_URL=https://lchai.gptfy.biz
ARG VITE_KEYCLOAK_URL=https://lchai.gptfy.biz
ARG VITE_KEYCLOAK_REALM=oncology
ARG VITE_KEYCLOAK_CLIENT_ID=oncology-webapp

RUN npx vite build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

RUN printf 'server {\n  listen 3000;\n  root /usr/share/nginx/html;\n  location / {\n    try_files $uri /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
