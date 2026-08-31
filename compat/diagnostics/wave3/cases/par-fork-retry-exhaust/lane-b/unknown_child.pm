package unknown_child;
# Oracle harness injector (not product code).
# Spawn an unreaped helper at module load so the parent's wait() reaps a
# real unknown PID (positive), distinct from exhausted wait() returning -1.
BEGIN {
    my $pid = fork();
    if (defined $pid && $pid == 0) {
        select(undef, undef, undef, 0.3);
        exit 0;
    }
}
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub simplify { return $_[1]; }
sub start {
    # Keep the scheduled worker alive so wait() can reap the helper first.
    select(undef, undef, undef, 1.5);
}
sub save { return 'ok'; }
sub restore { }
sub finalize { }
1;
