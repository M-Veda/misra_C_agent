FROM nginx:1.27-alpine

COPY infrastructure/nginx/nginx.conf /etc/nginx/nginx.conf
COPY infrastructure/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
