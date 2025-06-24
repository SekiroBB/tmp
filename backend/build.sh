#!/bin/bash
docker build -t realtime-voice-backend:latest \
--build-arg "HTTP_PROXY=http://192.168.103.211:23333" \
--build-arg "HTTPS_PROXY=http://192.168.103.211:23333" \
.