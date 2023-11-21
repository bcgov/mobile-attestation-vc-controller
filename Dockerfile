ARG python_version=3.9.18
FROM python:${python_version}-slim-bullseye AS build

COPY requirements.txt /tmp/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip --disable-pip-version-check \
    --no-cache-dir install \
    -r /tmp/requirements.txt && \ 
    rm -rf /tmp/requirements.txt

FROM build

RUN curl -ILv https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 \
    -o /usr/bin/jq && \
    chmod +x /usr/bin/jq

WORKDIR /opt/controller

COPY src /opt/controller/

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:5000", "controller:server"]
