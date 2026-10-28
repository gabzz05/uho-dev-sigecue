# Compila el frontend y lo sirve con nginx, que además hace de proxy inverso hacia el backend.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
# openssl genera un certificado autofirmado si no se monta el de la UHO.
RUN apk add --no-cache openssl
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/certificado.sh /docker-entrypoint.d/40-certificado.sh
RUN chmod +x /docker-entrypoint.d/40-certificado.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80 443
