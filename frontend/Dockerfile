FROM nginx:1.27-alpine
COPY frontend/studio-nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/index.html frontend/app.js frontend/project-channel.js frontend/styles.css frontend/health.html /usr/share/nginx/html/
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD wget -q -O - http://127.0.0.1/health.html
