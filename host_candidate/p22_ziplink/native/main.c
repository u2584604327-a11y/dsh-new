/* Test-only executable. Must link against exactly libp22version.so.3. */
#include <stdio.h>
extern int p22_versioned_answer(void);
int main(int argc, char **argv) {
    if(argc!=2 || argv[1]==NULL || argv[1][0]!='-' || argv[1][1]!='-' ||
       argv[1][2]!='v' || argv[1][3]!='e' || argv[1][4]!='r' ||
       argv[1][5]!='s' || argv[1][6]!='i' || argv[1][7]!='o' ||
       argv[1][8]!='n' || argv[1][9]!=0) return 43;
    const int answer=p22_versioned_answer();
    if(answer!=22035) return 42;
    printf("P22_VERSIONED_ZIP_DEPENDENCY_OK:%d\n",answer);
    return 0;
}
