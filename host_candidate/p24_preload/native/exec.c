/* Native PIE with DT_NEEDED libp24version.so.3; packaged file is libp24version.so. */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
extern int p24_dependency_answer(void);
int main(int argc, char **argv){
  if(argc!=2 || strcmp(argv[1],"--version")!=0)return 41;
  if(p24_dependency_answer()!=24035)return 42;
  printf("P24_REAL_SONAME_DEPENDENCY_UID=%ld\n",(long)getuid());
  return 0;
}
