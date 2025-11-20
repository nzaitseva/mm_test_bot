#!/bin/bash

docker build -t telegram-bot . && \
docker run -d \
  --name telegram-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/exports:/app/exports \
  --env-file .env \
  telegram-bot