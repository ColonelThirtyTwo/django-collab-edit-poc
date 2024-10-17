# Build pycrdt
# Won't need it once my branch is merged
FROM rust:1-alpine3.20 AS pycrdtbuild

RUN apk add --update-cache musl-dev python3=~3.12 py3-pip && rm -rf /var/cache/apk/*
RUN pip install --break-system-packages maturin[patchelf]

COPY pycrdt /pycrdt/
RUN cd /pycrdt/ && maturin build --release --out dist && ls -alh dist

FROM python:3.12-alpine3.20

ENV PIP_ROOT_USER_ACTION=ignore
RUN mkdir /app /install
COPY requirements.txt /install/
COPY --from=pycrdtbuild /pycrdt/dist/pycrdt-0.9.11-cp312-cp312-musllinux_1_2_x86_64.whl /install/pycrdt/dist/
RUN cd /install/ && \
    pip install /install/pycrdt/dist/pycrdt-0.9.11-cp312-cp312-musllinux_1_2_x86_64.whl && \
    pip install --requirement requirements.txt

VOLUME ["/app"]
WORKDIR /app
ENTRYPOINT [ "python" ]
