FROM ubuntu:22.04 AS build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    llvm \
    libbpf-dev \
    linux-headers-generic \
    make \
    zlib1g-dev \
    libelf-dev \
    libzstd-dev \
    gcc \
    linux-tools-common \
    linux-tools-generic \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY . .
RUN clang -O2 -g -target bpf -c xdp_prog.bpf.c -o xdp_prog.bpf.o
RUN bpftool gen skeleton xdp_prog.bpf.o > xdp_prog.skel.h
RUN clang -O2 -o loader loader.c -lbpf -lelf -lz -lzstd

FROM ubuntu:22.04
COPY --from=build /src/loader /loader
ENTRYPOINT ["/loader"]
