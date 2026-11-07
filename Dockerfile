# mock 服务镜像（Python 3.12 + FastAPI）
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY mock ./mock
EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/api/v1/health')"
CMD ["python", "-m", "uvicorn", "mock.app:app", "--host", "0.0.0.0", "--port", "8001"]
