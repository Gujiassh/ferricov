package ver_sigkill;
# Oracle harness injector (not product code).
# Force geninfo parallel worker to die by SIGKILL; parent maps this to the
# fork/OOM path while retaining signal (not ordinary-status) meaning.
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub extract_version {
    kill 'KILL', $$;
    return 'v';
}
sub check_version { return 1; }
1;
