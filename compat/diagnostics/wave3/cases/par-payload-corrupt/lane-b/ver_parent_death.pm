package ver_parent_death;
# Oracle harness injector (not product code).
# Child asynchronously kills its geninfo parent during --parallel work so
# the run cannot produce a successful coverage payload.
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub extract_version {
    my $ppid = getppid();
    my $killer = fork();
    if (defined $killer && $killer == 0) {
        select(undef, undef, undef, 0.15);
        kill 'TERM', $ppid;
        select(undef, undef, undef, 0.3);
        kill 'KILL', $ppid if kill(0, $ppid);
        exit 0;
    }
    # Stay alive long enough for parent death to take effect.
    for (my $i = 0; $i < 40; $i++) {
        last if (getppid() == 1 || 1 != kill(0, $ppid));
        select(undef, undef, undef, 0.05);
    }
    return 'v1';
}
sub check_version { return 1; }
1;
