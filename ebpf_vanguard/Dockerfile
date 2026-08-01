FROM ubuntu:22.04 AS build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    llvm \
    libbpf-dev \
    linux-headers-generic \
    gcc-multilib \
    make \
    zlib1g-dev \
    libelf-dev \
    libzstd-dev \
    gcc \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install standalone bpftool
RUN wget -O /tmp/bpftool.tar.gz https://github.com/libbpf/bpftool/releases/download/v7.4.0/bpftool-v7.4.0-amd64.tar.gz \
    && tar -xzf /tmp/bpftool.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/bpftool \
    && rm /tmp/bpftool.tar.gz

WORKDIR /src
COPY . .
RUN clang -O2 -g -target bpf -c xdp_prog.bpf.c -o xdp_prog.bpf.o
RUN bpftool gen skeleton xdp_prog.bpf.o > xdp_prog.skel.h
RUN clang -O2 -o loader loader.c -lbpf -lelf -lz -lzstd

FROM ubuntu:22.04
RUN apt-get update && apt-get install -y --no-install-recommends libbpf0 libelf1 zlib1g libzstd1 && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/loader /loader
ENTRYPOINT ["/loader"]
