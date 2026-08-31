package HistoryProbe;
use strict;
use warnings;

sub new {
    my ($class) = @_;
    open(my $handle, '>', 'history.loaded') or die("history marker: $!");
    print($handle "loaded\n");
    close($handle) or die("history marker close: $!");
    return bless({}, $class);
}

1;
