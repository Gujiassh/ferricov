package select;

use strict;
use warnings;

sub new {
    my ($class, @args) = @_;
    return bless { args => \@args }, $class;
}

sub select {
    my ($self, $line_data, $annotate_data, $filename, $line_number) = @_;
    return defined($line_number) && $line_number == 5;
}

1;
