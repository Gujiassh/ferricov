package ExitStart;
use POSIX ();
sub new { my ($class) = @_; bless {}, $class }
sub start { POSIX::_exit(7) }
sub save { return undef }
sub restore { return }
sub extract_version { return "v" }
sub compare_version { return 1 }
1;
