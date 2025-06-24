FROM harbor.xz.com:8448/spiritx-platform/python:3.12-slim-bookworm


COPY ./requirements.in .
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.in
COPY download.py .
RUN python download.py download-files
COPY . .
