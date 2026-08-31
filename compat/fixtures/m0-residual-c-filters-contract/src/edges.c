#include <stdio.h>

/* Multi-line call used for filter_lookahead edge (bogus branch on call). */
static void long_call(int a, int b, int c, int d, int e, int f) {
  printf("%d %d %d %d %d %d\n", a, b, c, d, e, f);
}

/* Bitwise-only expression used for filter_bitwise_conditional edge. */
static unsigned bitwise_edge(unsigned a, unsigned b) {
  unsigned v = (a & 0xF0u) | ((b << 1) & 0x0Fu) | (~a & 0x01u);
  return v;
}

int main(void) {
  long_call(1,
            2,
            3,
            4,
            5,
            6);
  /* comment-only line (blank after removeComments) with crafted hit */
  unsigned m = bitwise_edge(0xA5u, 0x3Cu);
  printf("%u\n", m);
  return 0;
}
