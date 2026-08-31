package corrupt_store;
# Oracle harness injector (not product code).
# Child writes non-Storable bytes to dumper_* and exits 0; parent must
# reject the payload atomically (parallel failure, no successful merge).
BEGIN {
    require Storable;
    our $REAL_STORE = \&Storable::store;
    no warnings 'redefine';
    *Storable::store = sub {
        my ($ref, $file) = @_;
        if (defined $file && index($file, 'dumper_') >= 0) {
            open(my $fh, '>', $file) or die "open $file: $!";
            print {$fh} "CORRUPT_NOT_STORABLE_PAYLOAD\n";
            close $fh;
            return 1;
        }
        return $REAL_STORE->($ref, $file);
    };
}
sub new { my ($class, @args) = @_; return bless [@args], $class; }
sub simplify { return $_[1]; }
sub start { return; }
sub save { return 'ok'; }
sub restore { }
sub finalize { }
1;
