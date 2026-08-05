#!/usr/bin/env perl
# Deterministic LCOV 2.5 model inspector for M0 state-ownership fixtures.
# Loads the installed pinned lcovutil and emits canonical machine-readable JSON.
use strict;
use warnings;
use FindBin;
use lib '/usr/local/lib/lcov';
use lcovutil;
use JSON::PP ();

$| = 1;

my @raw = @ARGV;
my @inputs;
my @ignore;
my $excessive_threshold;

while (@raw) {
    my $arg = shift(@raw);
    if ($arg eq '--ignore' || $arg eq '--ignore-errors') {
        die("inspect_model.pl: $arg requires a value\n") unless @raw;
        push(@ignore, split(/,/, shift(@raw)));
        next;
    }
    if ($arg eq '--excessive-threshold') {
        die("inspect_model.pl: --excessive-threshold requires a value\n") unless @raw;
        $excessive_threshold = shift(@raw);
        next;
    }
    if ($arg eq '--') {
        push(@inputs, @raw);
        last;
    }
    if ($arg =~ /^-/) {
        die("inspect_model.pl: unknown option '$arg'\n");
    }
    push(@inputs, $arg);
}

die("usage: inspect_model.pl [--ignore CLASS[,CLASS...]] [--excessive-threshold N] <tracefile> [tracefile ...]\n")
    unless @inputs && !grep({ !-f $_ } @inputs);

# Match the feature surface used by the state-ownership Oracle cases.
$lcovutil::br_coverage   = 1;
$lcovutil::mcdc_coverage = 1;
$lcovutil::func_coverage = 1;
$lcovutil::verbose       = 0;
lcovutil::parse_ignore_errors(@ignore) if @ignore;
$lcovutil::excessive_count_threshold = $excessive_threshold
    if defined($excessive_threshold);

my @resolved_inputs = @inputs;
my $reader = ReadCurrentSource->new();
my $trace = TraceFile->load(shift(@inputs), $reader, 0);
foreach my $input (@inputs) {
    my $current = TraceFile->load($input, $reader, 0);
    $trace->merge_tracefile($current, TraceInfo::UNION);
}

sub json_number {
    my ($value) = @_;
    return undef unless defined($value);
    # Preserve the observable sign that numeric coercion would otherwise erase.
    return '-0' if "$value" eq '-0';
    # Historical finite simple decimals remain JSON numbers.
    if ($value =~ /^-?\d+(?:\.\d+)?$/) {
        return 0 + $value;
    }
    # Every nonfinite spelling/value must be a plain string before JSON::PP encode.
    {
        no warnings qw(numeric uninitialized);
        if ($value != $value) {
            return "$value";
        }
        my $inf = 9**9**9;
        if ($value == $inf || $value == -$inf) {
            return "$value";
        }
    }
    # Preserve other finite spellings as historical strings.
    return $value;
}

sub snapshot_count_data {
    my ($data) = @_;
    return undef unless defined($data);
    my %lines;
    foreach my $line (sort { $a <=> $b } $data->keylist()) {
        $lines{$line} = json_number($data->value($line));
    }
    return {
        found => json_number($data->found()),
        hit   => json_number($data->hit()),
        lines => \%lines,
    };
}

sub snapshot_function_map {
    my ($data) = @_;
    return undef unless defined($data);
    my %functions;
    foreach my $key (sort { $a <=> $b } $data->keylist()) {
        my $entry = $data->findKey($key);
        my %aliases;
        while (my ($alias, $count) = each(%{$entry->aliases()})) {
            $aliases{$alias} = json_number($count);
        }
        $functions{$key} = {
            name      => $entry->name(),
            start     => json_number($entry->line()),
            end       => defined($entry->end_line()) ? json_number($entry->end_line()) : undef,
            hit       => json_number($entry->hit()),
            aliases   => {%aliases},
        };
    }
    return {
        found     => json_number($data->numFunc(0)),
        hit       => json_number($data->numHit(0)),
        functions => \%functions,
    };
}

sub snapshot_branch_data {
    my ($data) = @_;
    return undef unless defined($data);
    my %lines;
    foreach my $line (sort { $a <=> $b } $data->keylist()) {
        my $location = $data->value($line);
        my @blocks;
        foreach my $block ($location->blocks()) {
            my @elements;
            foreach my $element (@{$block->elements()}) {
                push(
                    @elements,
                    {
                        id       => json_number($element->id()),
                        taken    => $element->isTaken() ? json_number($element->data()) : '-',
                        count    => json_number($element->count()),
                        expr     => defined($element->expr()) ? $element->expr() : undef,
                        type     => $element->type_name(),
                        excluded => $element->is_excluded() ? JSON::PP::true : JSON::PP::false,
                    }
                );
            }
            push(
                @blocks,
                {
                    idx       => json_number($block->idx()),
                    signature => $block->signature(),
                    elements  => \@elements,
                }
            );
        }
        $lines{$line} = { blocks => \@blocks };
    }
    return {
        found => json_number($data->found()),
        hit   => json_number($data->hit()),
        lines => \%lines,
    };
}

sub snapshot_mcdc_data {
    my ($data) = @_;
    return undef unless defined($data);
    my %lines;
    foreach my $line (sort { $a <=> $b } $data->keylist()) {
        my $block  = $data->value($line);
        my %groups;
        foreach my $size (sort { $a <=> $b } keys %{$block->groups()}) {
            my @exprs;
            foreach my $expr (@{$block->expressions($size)}) {
                push(
                    @exprs,
                    {
                        index      => json_number($expr->index()),
                        expression => $expr->expression(),
                        true_count => json_number($expr->count(1)),
                        false_count => json_number($expr->count(0)),
                        true_excluded =>
                            $expr->is_excluded(1) ? JSON::PP::true : JSON::PP::false,
                        false_excluded =>
                            $expr->is_excluded(0) ? JSON::PP::true : JSON::PP::false,
                    }
                );
            }
            $groups{$size} = \@exprs;
        }
        my ($found, $hit) = $block->totals();
        $lines{$line} = {
            line   => json_number($block->line()),
            found  => json_number($found),
            hit    => json_number($hit),
            groups => \%groups,
        };
    }
    return {
        found => json_number($data->found()),
        hit   => json_number($data->hit()),
        lines => \%lines,
    };
}

sub snapshot_testcase_map {
    my ($map, $kind) = @_;
    my %result;
    foreach my $name (sort $map->keylist()) {
        my $value = $map->value($name);
        if ($kind eq 'line') {
            $result{$name} = snapshot_count_data($value);
        } elsif ($kind eq 'function') {
            $result{$name} = snapshot_function_map($value);
        } elsif ($kind eq 'branch') {
            $result{$name} = snapshot_branch_data($value);
        } elsif ($kind eq 'mcdc') {
            $result{$name} = snapshot_mcdc_data($value);
        } else {
            die("unknown testcase family: $kind");
        }
    }
    return \%result;
}

my @sources;
foreach my $filename (sort $trace->files()) {
    my $info = $trace->data($filename);
    push(
        @sources,
        {
            filename => $filename,
            version  => defined($info->version()) ? $info->version() : undef,
            aggregate => {
                line     => snapshot_count_data($info->sum()),
                function => snapshot_function_map($info->func()),
                branch   => snapshot_branch_data($info->sumbr()),
                mcdc     => snapshot_mcdc_data($info->mcdc()),
            },
            testcases => {
                line     => snapshot_testcase_map($info->test(), 'line'),
                function => snapshot_testcase_map($info->testfnc(), 'function'),
                branch   => snapshot_testcase_map($info->testbr(), 'branch'),
                mcdc     => snapshot_testcase_map($info->testcase_mcdc(), 'mcdc'),
            },
        }
    );
}

my $document = {
    schema_version => 1,
    kind           => 'semantic_model_snapshot',
    oracle         => {
        program => '/usr/local/bin/lcov',
        module  => '/usr/local/lib/lcov/lcovutil.pm',
    },
    sources => \@sources,
};
# Bind only resolved tracefile paths so option argv does not leak into identity fields.
if (@resolved_inputs == 1) {
    $document->{input} = $resolved_inputs[0];
}
else {
    $document->{inputs} = [@resolved_inputs];
}

my $json = JSON::PP->new->canonical(1)->ascii(1)->pretty(1)->encode($document);
print $json;
