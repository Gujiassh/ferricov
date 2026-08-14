package select_none;
use strict;
sub new {
  my ($class, $script, @args) = @_;
  return bless {}, $class;
}
sub select {
  return 0;
}
1;
