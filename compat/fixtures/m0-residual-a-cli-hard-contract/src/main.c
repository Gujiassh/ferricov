int fa(int);
int fb(int);
int fc(int);
int main(void) {
  int s = fa(1) + fb(2) + fc(3);
  return s > 0 ? 0 : 1;
}
