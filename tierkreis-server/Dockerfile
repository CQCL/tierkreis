FROM rust:1.76.0-bookworm as rustbuild
COPY . .
RUN apt update && apt install -y openssl protobuf-compiler wget git
RUN rustup component add rustfmt
RUN cargo build --release --package tierkreis-server

FROM debian:bookworm-20240211-slim
RUN apt update && apt install -y openssl
COPY --from=rustbuild target/release/tierkreis-server /usr/local/bin/tierkreis-server
CMD ["tierkreis-server"]