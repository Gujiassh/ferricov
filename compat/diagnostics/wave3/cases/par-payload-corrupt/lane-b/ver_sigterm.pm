package ver_sigterm;
# Oracle harness injector (not product code).
# Force geninfo parallel worker to die by SIGTERM mid-chunk so the parent
# reports signal identity, not a shifted ordinary exit status.
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub extract_version {
    kill 'TERM', $$;
    select(undef, undef, undef, 2);
    return 'v';
}
sub check_version { return 1; }
1;
