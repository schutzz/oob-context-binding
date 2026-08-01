TARGET = xdp_prog
all: loader vmlinux.h

vmlinux.h:
	bpftool btf dump file /sys/kernel/btf/vmlinux format c > vmlinux.h

$(TARGET).o: $(TARGET).bpf.c vmlinux.h
	clang -O2 -g -Wall -target bpf -c $<
	bpftool gen skeleton $@ > $(TARGET).skel.h

loader: loader.c $(TARGET).o
	gcc -O2 -Wall -I. loader.c -lbpf -o loader

clean:
	rm -f *.o *.skel.h vmlinux.h loader
