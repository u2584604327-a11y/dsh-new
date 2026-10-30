/* Test-only native shared library, no host data or network. */
__attribute__((visibility("default"))) int p22_versioned_answer(void) {
    return 22035;
}
