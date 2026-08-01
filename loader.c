#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <net/if.h>
#include <linux/if_link.h>
#include "xdp_prog.skel.h"

int main(int argc, char **argv) {
    struct xdp_prog *skel;
    int err;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <interface>\n", argv[0]);
        return 1;
    }

    int ifindex = if_nametoindex(argv[1]);
    if (!ifindex) {
        perror("if_nametoindex");
        return 1;
    }

    skel = xdp_prog__open_and_load();
    if (!skel) {
        fprintf(stderr, "Failed to open and load BPF skeleton\n");
        return 1;
    }

    err = xdp_prog__attach(skel);
    if (err) {
        fprintf(stderr, "Failed to attach BPF program\n");
        goto cleanup;
    }

    printf("Successfully loaded and attached XDP program to %s\n", argv[1]);
    printf("Press Ctrl+C to exit...\n");
    
    while (1) { sleep(1); }

cleanup:
    xdp_prog__destroy(skel);
    return 0;
}
