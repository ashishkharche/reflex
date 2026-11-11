// Behavior-session network guard. Deny Internet egress before any packet leaves.
// macOS and the iOS simulator load it with DYLD_INSERT_LIBRARIES (interpose). Linux loads it with LD_PRELOAD.
// This is test instrumentation, never linked into Core or a Mobile host.
#include <sys/socket.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#ifdef __APPLE__
#include <TargetConditionals.h>
#endif
#ifndef RTLD_NEXT
#define RTLD_NEXT ((void *) -1l)
#endif

static void audit(const char *message) {
    const char *path = getenv("REFLEX_NETWORK_LOG");
    if (!path) _exit(78);
    int fd = open(path, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0) _exit(78);
    if (write(fd, message, strlen(message)) < 0) _exit(78);
    close(fd);
}
#if defined(__APPLE__) && TARGET_OS_SIMULATOR
// A simulator host runs in a throwaway device. The runner points HOME and CFFIXED_USER_HOME at a private
// folder, so preferences and files land there and nowhere else.
static void isolate_preferences(void) {
    const char *home = getenv("HOME");
    const char *fixed = getenv("CFFIXED_USER_HOME");
    if (!home || !fixed || strcmp(home, fixed) != 0) {
        audit("BLOCKED simulator home not private\n");
        _exit(78);
    }
    audit("STORAGE simulator-home\n");
}
#elif defined(__APPLE__)
// This read-only query proves the launcher installed a kernel policy before exec.
extern int sandbox_check(pid_t pid, const char *operation, int filter_type, ...);
static void isolate_preferences(void) {
    if (!getenv("REFLEX_STORAGE_PROFILE") || sandbox_check(getpid(), "user-preference-write", 0) != 1) {
        audit("BLOCKED preferences sandbox unavailable\n");
        _exit(78);
    }
    audit("STORAGE seatbelt\n");
}
#endif
__attribute__((constructor)) static void ready(void) {
#ifdef __APPLE__
    isolate_preferences();
#endif
    audit("READY\n");
}
static int internet(const struct sockaddr *address) {
    return address && (address->sa_family == AF_INET || address->sa_family == AF_INET6);
}

#ifdef __APPLE__
#define GUARD(name) guard_##name
#else
#define GUARD(name) name
#endif
// On macOS, calls made from this library are not interposed, so it calls the real function by name.
// dlsym(RTLD_NEXT) can hand back the replacement there, which loops forever on a Unix socket connect.
#ifdef __APPLE__
#define ORIGINAL(name) __typeof__(&name) original = &name
#else
#define ORIGINAL(name) static __typeof__(&name) original; if (!original) original = (__typeof__(&name))dlsym(RTLD_NEXT, #name)
#endif

int GUARD(connect)(int fd, const struct sockaddr *address, socklen_t length) {
    if (internet(address)) { audit("DENIED connect HTTP-capable Internet socket\n"); errno = EPERM; return -1; }
    ORIGINAL(connect);
    return original(fd, address, length);
}
ssize_t GUARD(sendto)(int fd, const void *data, size_t length, int flags,
                      const struct sockaddr *address, socklen_t addressLength) {
    if (internet(address)) { audit("DENIED sendto Internet datagram\n"); errno = EPERM; return -1; }
    ORIGINAL(sendto);
    return original(fd, data, length, flags, address, addressLength);
}

#ifdef __APPLE__
static int guard_connectx(int fd, const sa_endpoints_t *endpoints, sae_associd_t association,
                          unsigned int flags, const struct iovec *iov, unsigned int count,
                          size_t *length, sae_connid_t *connection) {
    if (endpoints && internet(endpoints->sae_dstaddr)) {
        audit("DENIED connectx HTTP-capable Internet socket\n"); errno = EPERM; return -1;
    }
    return connectx(fd, endpoints, association, flags, iov, count, length, connection);
}
#define INTERPOSE(replacement, replacee) \
    __attribute__((used)) static struct { const void *replacement; const void *original; } \
    interpose_##replacee __attribute__((section("__DATA,__interpose"))) = { \
        (const void *)&replacement, (const void *)&replacee };
INTERPOSE(guard_connect, connect)
INTERPOSE(guard_connectx, connectx)
INTERPOSE(guard_sendto, sendto)
#endif
