#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
__attribute__((constructor)) static void r(void){const char*p=getenv("REFLEX_NETWORK_LOG");int fd=open(p,O_WRONLY|O_CREAT|O_APPEND,0600);write(fd,"READY\n",6);close(fd);}
