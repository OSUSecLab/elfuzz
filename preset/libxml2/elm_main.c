#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size);
int LLVMFuzzerInitialize(int *argc, char ***argv);

//$main_begin$
int main(int argc, char **argv) {
    LLVMFuzzerInitialize(0, 0);

    FILE *fp = fopen(argv[1], "rb");
    if (!fp) {
        return 1;
    }
    fseek(fp, 0, SEEK_END);
    size_t size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    unsigned char *data = (unsigned char *) malloc(size);
    fread(data, 1, size, fp);
    fclose(fp);
    LLVMFuzzerTestOneInput(data, size);
    return 0;
}
//$main_end$
