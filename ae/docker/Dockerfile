ARG BASE_IMAGE=debian:12-slim
FROM ${BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 xvfb ca-certificates fonts-liberation fonts-noto-color-emoji \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libatspi2.0-0 libx11-6 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxrandr2 libxtst6 libgbm1 libexpat1 \
    libxcb1 libxkbcommon0 libpango-1.0-0 libcairo2 libasound2 libgtk-3-0 \
    libxss1 libvulkan1 xdg-utils \
    && rm -rf /var/lib/apt/lists/*
COPY runtime.py /opt/cookietrace/runtime.py
WORKDIR /tmp
ENTRYPOINT ["python3", "/opt/cookietrace/runtime.py"]
