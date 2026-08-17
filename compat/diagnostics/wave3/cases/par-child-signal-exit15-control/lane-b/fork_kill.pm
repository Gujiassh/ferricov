package fork_kill;
# Oracle harness injector (not product code).
# Always SIGKILL the parallel worker so genhtml's fork-retry path observes
# finite retries under --ignore-errors fork and bounded max_fork_fails.
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub simplify { return $_[1]; }
sub start { kill 'KILL', $$; }
sub save { return 'ok'; }
sub restore { }
sub finalize { }
1;
