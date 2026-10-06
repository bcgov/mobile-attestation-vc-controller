ARG python_version=3.12
FROM python:${python_version}-slim-bookworm AS build

COPY requirements.txt /tmp/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl && \
    rm -rf /var/lib/apt/lists/*

# --require-hashes pins every resolved version; --only-binary avoids running setup
# scripts. cbor 1.0.0 publishes no wheels, so it is the one explicit exception.
RUN pip --disable-pip-version-check \
    --no-cache-dir install \
    --require-hashes \
    --only-binary :all: \
    --no-binary cbor \
    -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt

FROM build

RUN curl -ILv https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 \
    -o /usr/bin/jq && \
    chmod +x /usr/bin/jq

WORKDIR /opt/controller

COPY src /opt/controller/
COPY fixtures /opt/fixtures/

ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:5000", "controller:server"]
