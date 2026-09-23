# V2HTML 服务端镜像：素材管线（yt-dlp/ffmpeg）+ HTTP 服务（FastAPI）
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U yt-dlp

WORKDIR /app
COPY requirements.txt server/requirements.txt ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY . .

ENV V2HTML_PORT=8400
EXPOSE 8400
CMD ["python3", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8400"]
