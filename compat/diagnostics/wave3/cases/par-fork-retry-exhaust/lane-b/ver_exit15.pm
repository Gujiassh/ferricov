package ver_exit15;
# Oracle harness control injector (not product code).
# Ordinary exit(15) contrast for SIGTERM: parent must report
# "returned non-zero exit status 15", not "died due to signal 15".
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub extract_version {
    require POSIX;
    POSIX::_exit(15);
}
sub check_version { return 1; }
1;
