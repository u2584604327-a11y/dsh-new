#include <stdio.h>
#include <string.h>
#include <unistd.h>
extern int p26_top(void);
extern int p26_sqlite(void);
int main(int argc,char **argv){
  if(argc!=2||strcmp(argv[1],"--version")!=0)return 41;
  if(p26_top()+p26_sqlite()!=26042)return 42;
  printf("P26_MULTILIB_SONAME_OK_UID=%ld\n",(long)getuid());
  return 0;
}
