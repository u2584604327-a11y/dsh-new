/* No I/O, secrets, network or DSH integration: test-only SONAME dependency. */
__attribute__((visibility("default"))) int p24_dependency_answer(void) { return 24035; }
