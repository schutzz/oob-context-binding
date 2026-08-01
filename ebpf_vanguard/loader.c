#include <stdio.h>
#include <unistd.h>
#include <errno.h>
#include <net/if.h>
#include <sys/resource.h>
#include <bpf/libbpf.h>
#include "xdp_prog.skel.h"

int libbpf_print_fn(enum libbpf_print_level level, const char *format, va_list args) {
    return vfprintf(stderr, format, args);
}

struct event {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 dst_port;
    __u32 packet_len;
};

static int handle_event(void *ctx, void *data, size_t data_sz) {
    struct event *e = data;
    printf("[eBPF Vanguard] Kernel XDP Match -> Port %d, Len %d bytes passed at line rate!\n", 
           e->dst_port, e->packet_len);
    fflush(stdout);
    return 0;
}

int main(int argc, char **argv) {
    struct xdp_prog_bpf *skel;
    int err;
    int ifindex;
    
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <ifname>\n", argv[0]);
        return 1;
    }

    ifindex = if_nametoindex(argv[1]);
    if (!ifindex) {
        fprintf(stderr, "Invalid interface name %s\n", argv[1]);
        return 1;
    }

    libbpf_set_print(libbpf_print_fn);

    struct rlimit rlim = {
        .rlim_cur = RLIM_INFINITY,
        .rlim_max = RLIM_INFINITY,
    };
    if (setrlimit(RLIMIT_MEMLOCK, &rlim)) {
        fprintf(stderr, "Failed to increase RLIMIT_MEMLOCK\n");
    }

    DECLARE_LIBBPF_OPTS(bpf_object_open_opts, open_opts);
    char *custom_btf = getenv("CUSTOM_BTF_PATH");
    if (custom_btf && access(custom_btf, R_OK) == 0) {
        open_opts.btf_custom_path = custom_btf;
        printf("[eBPF Vanguard] Using custom BTF file: %s\n", custom_btf);
    } else {
        printf("[eBPF Vanguard] Using system default BTF from /sys/kernel/btf/vmlinux\n");
    }

    skel = xdp_prog_bpf__open_opts(&open_opts);
    if (!skel) {
        fprintf(stderr, "Failed to open BPF skeleton\n");
        return 1;
    }

    err = xdp_prog_bpf__load(skel);
    if (err) {
        fprintf(stderr, "Failed to load BPF skeleton\n");
        return 1;
    }

    skel->links.xdp_pass = bpf_program__attach_xdp(skel->progs.xdp_pass, ifindex);
    if (!skel->links.xdp_pass) {
        err = -errno;
        fprintf(stderr, "Failed to attach BPF program to ifindex %d\n", ifindex);
        goto cleanup;
    }

    printf("[eBPF Vanguard] Attached XDP program to %s (ifindex %d) - Line-rate Kernel Hook Active\n", argv[1], ifindex);

    struct ring_buffer *rb = NULL;
    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, NULL, NULL);
    if (!rb) {
        fprintf(stderr, "Failed to create ring buffer\n");
        err = -1;
        goto cleanup;
    }

    while (1) {
        err = ring_buffer__poll(rb, 100);
        if (err == -EINTR) {
            err = 0;
            break;
        }
        if (err < 0) {
            printf("Error polling ring buffer: %d\n", err);
            break;
        }
    }

cleanup:
    xdp_prog_bpf__destroy(skel);
    return err < 0 ? -err : 0;
}
