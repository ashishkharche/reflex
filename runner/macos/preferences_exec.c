// Apply the kernel boundary before exec, even when a target drops DYLD variables.
#include <sandbox.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>

extern int sandbox_check(pid_t pid, const char *operation, int filter_type, ...);

static void audit(const char *message) {
    const char *path = getenv("REFLEX_NETWORK_LOG");
    int fd = path ? open(path, O_WRONLY | O_APPEND) : -1;
    if (fd < 0 || write(fd, message, strlen(message)) < 0) _exit(78);
    close(fd);
}

#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
int main(int argc, char **argv) {
    const char *profile = getenv("REFLEX_STORAGE_PROFILE");
    const char *guard = getenv("REFLEX_NATIVE_GUARD");
    char *error = NULL;
    if (argc < 2 || !profile || !guard || sandbox_init(profile, 0, &error) != 0) {
        audit("BLOCKED preferences sandbox unavailable\n");
        if (error) { fprintf(stderr, "%s\n", error); sandbox_free_error(error); }
        return 78;
    }
    if (sandbox_check(getpid(), "user-preference-write", 0) != 1) {
        audit("BLOCKED preferences sandbox policy did not deny writes\n");
        return 78;
    }
    audit("STORAGE launcher\n");
    if (setenv("DYLD_INSERT_LIBRARIES", guard, 1) != 0) return 78;
    execvp(argv[1], argv + 1);
    perror("BLOCKED preferences launcher exec");
    return 78;
}
#pragma clang diagnostic pop
