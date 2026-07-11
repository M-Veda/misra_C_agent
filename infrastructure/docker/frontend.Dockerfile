FROM node:22-alpine AS base

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./

FROM base AS development

RUN npm ci

COPY frontend ./

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM base AS production

RUN npm ci

COPY frontend ./

RUN npm run build

FROM nginx:1.27-alpine AS production-serve

COPY --from=production /app/frontend/dist /usr/share/nginx/html
COPY infrastructure/nginx/frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
