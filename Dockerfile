FROM rust:latest as rustbuild

COPY . .
RUN rustup component add rustfmt
RUN cargo build --release --package tierkreis-server
RUN apt-get update &&  apt-get install -y protobuf-compiler wget git
RUN GRPC_HEALTH_PROBE_VERSION=v0.3.1 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/v0.4.5/grpc_health_probe-linux-386 && \
    chmod +x /bin/grpc_health_probe

FROM debian:bookworm-slim

WORKDIR /usr/local
RUN apt update && apt install -y openssl
COPY --from=rustbuild target/release/tierkreis-server /usr/local/bin/tierkreis-server

EXPOSE 8080 9090
# ENV TIERKREIS_HTTP_PORT 9090
ENV TIERKREIS_GRPC_PORT 8080
ENV TIERKREIS_HOST 0.0.0.0

ENTRYPOINT ["./bin/tierkreis-server"]
