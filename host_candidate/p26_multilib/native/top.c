/* Synthetic transitive dependency: SONAME libp26top.so.2, DT_NEEDED core.so.1. */
extern int p26_core(void);
__attribute__((visibility("default"))) int p26_top(void){return p26_core()+2;}
