package HistoryProbe;
use strict;
use warnings;

sub new {
    my ($class) = @_;
    open(my $handle, ">", "history.loaded") or die("history marker: $!");
    print {$handle} "loaded\n";
    close($handle) or die("history marker close: $!");
    return bless {}, $class;
}

sub history {
    my ($self, $item) = @_;
    return 90 if $item =~ /a\.gcda/;
    return 80 if $item =~ /b\.gcda/;
    return 70 if $item =~ /c\.gcda/;
    return 60 if $item =~ /main\.gcda/;
    return undef;
}

1;
