FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN --mount=type=secret,id=package_ca \
    if [ -f /run/secrets/package_ca ]; then export PIP_CERT=/run/secrets/package_ca; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY migrations ./migrations
RUN chmod -R a+rX /app/backend /app/migrations
USER 10001
ENV STUDIO_TEST_MODE=false
EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8100/health', timeout=3)"
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8100"]
