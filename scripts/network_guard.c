// macOS behavior-session guard. Deny Internet egress before any packet leaves.
// This is test instrumentation, never linked into Core or a Mobile host.
#include <sys/socket.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

static void audit(const char *message) {
    const char *path = getenv("REFLEX_NETWORK_LOG");
    if (!path) _exit(78);
    int fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0) _exit(78);
    if (write(fd, message, strlen(message)) < 0) _exit(78);
    close(fd);
}
__attribute__((constructor)) static void ready(void) { audit("READY\n"); }
static int internet(const struct sockaddr *address) {
    return address && (address->sa_family == AF_INET || address->sa_family == AF_INET6);
}
static int guard_connect(int fd, const struct sockaddr *address, socklen_t length) {
    if (internet(address)) { audit("DENIED connect HTTP-capable Internet socket\n"); errno = EPERM; return -1; }
    static int (*original)(int, const struct sockaddr *, socklen_t);
    if (!original) original = dlsym(RTLD_NEXT, "connect");
    return original(fd, address, length);
}
static int guard_connectx(int fd, const sa_endpoints_t *endpoints, sae_associd_t association,
                          unsigned int flags, const struct iovec *iov, unsigned int count,
                          size_t *length, sae_connid_t *connection) {
    if (endpoints && internet(endpoints->sae_dstaddr)) {
        audit("DENIED connectx HTTP-capable Internet socket\n"); errno = EPERM; return -1;
    }
    static int (*original)(int, const sa_endpoints_t *, sae_associd_t, unsigned int,
                          const struct iovec *, unsigned int, size_t *, sae_connid_t *);
    if (!original) original = dlsym(RTLD_NEXT, "connectx");
    return original(fd, endpoints, association, flags, iov, count, length, connection);
}
static ssize_t guard_sendto(int fd, const void *data, size_t length, int flags,
                            const struct sockaddr *address, socklen_t addressLength) {
    if (internet(address)) { audit("DENIED sendto Internet datagram\n"); errno = EPERM; return -1; }
    static ssize_t (*original)(int, const void *, size_t, int, const struct sockaddr *, socklen_t);
    if (!original) original = dlsym(RTLD_NEXT, "sendto");
    return original(fd, data, length, flags, address, addressLength);
}
#define INTERPOSE(replacement, replacee) \
    __attribute__((used)) static struct { const void *replacement; const void *original; } \
    interpose_##replacee __attribute__((section("__DATA,__interpose"))) = { \
        (const void *)&replacement, (const void *)&replacee };
INTERPOSE(guard_connect, connect)
INTERPOSE(guard_connectx, connectx)
INTERPOSE(guard_sendto, sendto)
