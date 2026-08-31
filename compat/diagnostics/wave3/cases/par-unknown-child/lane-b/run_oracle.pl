#!/usr/bin/env perl
# Oracle harness launcher (not product code).
# Docker places the container entrypoint as PID 1; geninfo's
# check_parent_process treats getppid()==1 as parent death. Re-launch the
# requested LCOV tool as a child of this perl process so ambient PID-1 is
# not misread as a real parent-death event.
use strict;
use warnings;

if (@ARGV < 1) {
    die "usage: run_oracle.pl TOOL [args...]\n";
}

my $rc = system { $ARGV[0] } @ARGV;
if ($rc == -1) {
    die "failed to execute $ARGV[0]: $!\n";
}
if ($rc & 127) {
    # Preserve signal death of the tool as 128+signal for docker exit.
    exit(128 + ($rc & 127));
}
exit($rc >> 8);
