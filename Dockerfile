FROM ubuntu:22.04
RUN apt-get update && apt-get install -y clang llvm libbpf-dev linux-tools-common linux-tools-generic make gcc iproute2 bpftool
WORKDIR /root
COPY . .
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["./loader", "eth0"]
