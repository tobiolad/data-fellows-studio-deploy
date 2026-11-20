FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
USER 10001
ENV STUDIO_TEST_MODE=false
EXPOSE 8100
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8100"]
