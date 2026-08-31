int may_throw(int x) {
  if (x > 0) throw 1;
  return x;
}
int main() {
  try { may_throw(0); may_throw(1); }
  catch (...) {}
  return 0;
}
