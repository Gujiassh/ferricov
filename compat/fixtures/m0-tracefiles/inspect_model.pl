#!/usr/bin/env perl
# Deterministic LCOV 2.5 model inspector for M0 state-ownership fixtures.
# Loads the installed pinned lcovutil and emits canonical machine-readable JSON.
use strict;
use warnings;
use FindBin;
use lib '/usr/local/lib/lcov';
use lcovutil;
use Scalar::Util qw(looks_like_number);
use B;
use JSON::PP ();
use File::Basename ();

$| = 1;

my @raw = @ARGV;
my @inputs;
my @ignore;
my $excessive_threshold;
my $numeric_plan_path;

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
    if ($arg eq '--numeric-plan') {
        die("inspect_model.pl: --numeric-plan requires a value\n") unless @raw;
        $numeric_plan_path = shift(@raw);
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

die("usage: inspect_model.pl [--ignore CLASS[,CLASS...]] [--excessive-threshold N] [--numeric-plan PATH] <tracefile> [tracefile ...]\n")
    unless @inputs && !grep({ !-f $_ } @inputs);

# Fail closed on the numeric plan before any fixture load so plan identity
# errors are not masked by later tracefile diagnostics.
my ($early_numeric_plan, $early_numeric_plan_raw);
if (defined($numeric_plan_path)) {
    die("inspect_model.pl: numeric plan not found: $numeric_plan_path\n")
        unless -f $numeric_plan_path;
    ($early_numeric_plan, $early_numeric_plan_raw) =
      load_strict_ascii_json_object($numeric_plan_path);
}

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

sub load_strict_ascii_json_object {
    my ($path) = @_;
    open(my $fh, '<:raw', $path) or die("inspect_model.pl: cannot read numeric plan $path: $!\n");
    local $/;
    my $raw = <$fh>;
    close($fh);
    die("inspect_model.pl: numeric plan $path is empty\n") unless defined($raw) && length($raw);
    die("inspect_model.pl: numeric plan $path contains non-ASCII bytes\n") if $raw =~ /[^\x00-\x7F]/;
    # Fail closed on bare non-RFC constants outside JSON strings.
    reject_bare_non_rfc_json_constants($raw, $path);
    my $json = JSON::PP->new->ascii(1)->allow_nonref(0)->relaxed(0)->loose(0);
    my $document;
    eval {
        $document = $json->decode($raw);
        1;
    } or do {
        my $error = $@ || 'decode failed';
        die("inspect_model.pl: numeric plan $path is not strict ASCII JSON: $error");
    };
    die("inspect_model.pl: numeric plan $path root must be an object\n")
        unless ref($document) eq 'HASH';
    # Reject trailing data: re-encode canonical form and ensure full consumption via incr parser.
    my $incr = JSON::PP->new->ascii(1)->allow_nonref(0)->relaxed(0)->loose(0);
    my $again;
    eval {
        $again = $incr->incr_parse($raw);
        my $trailing = $incr->incr_text;
        $trailing =~ s/^\s+//;
        die("trailing data after JSON value") if defined($trailing) && length($trailing);
        1;
    } or do {
        my $error = $@ || 'trailing check failed';
        die("inspect_model.pl: numeric plan $path trailing/incomplete JSON: $error");
    };
    die("inspect_model.pl: numeric plan $path root must be an object\n")
        unless ref($again) eq 'HASH';
    # Reject duplicate object keys with a second-pass scanner over object scopes.
    reject_duplicate_json_keys($raw, $path);
    return ($document, $raw);
}


sub reject_bare_non_rfc_json_constants {
    my ($raw, $path) = @_;
    my $in_string = 0;
    my $escape = 0;
    my $i = 0;
    my $len = length($raw);
    while ($i < $len) {
        my $ch = substr($raw, $i, 1);
        if ($in_string) {
            if ($escape) { $escape = 0; $i++; next; }
            if ($ch eq "\\") { $escape = 1; $i++; next; }
            if ($ch eq '"') { $in_string = 0; }
            $i++;
            next;
        }
        if ($ch eq '"') { $in_string = 1; $i++; next; }
        my $rest = substr($raw, $i);
        if ($rest =~ /^(?:-?Infinity|-?Inf|NaN)\b/i) {
            my $before = $i > 0 ? substr($raw, $i - 1, 1) : '';
            if ($before !~ /[A-Za-z0-9_]/) {
                die("inspect_model.pl: numeric plan $path contains non-RFC JSON constant\n");
            }
        }
        $i++;
    }
}

sub reject_duplicate_json_keys {
    my ($raw, $path) = @_;
    # Lightweight structural scan: within each {...} object depth, track keys seen
    # at that depth while ignoring strings/escapes. Nested objects reset their key set.
    my @stack_keys;
    my $in_string = 0;
    my $escape = 0;
    my $expect_key = 0;
    my $i = 0;
    my $len = length($raw);
    while ($i < $len) {
        my $ch = substr($raw, $i, 1);
        if ($in_string) {
            if ($escape) { $escape = 0; $i++; next; }
            if ($ch eq "\\") { $escape = 1; $i++; next; }
            if ($ch eq '"') {
                $in_string = 0;
                if ($expect_key && @stack_keys) {
                    # key just closed; next non-space should be ':'
                    my $j = $i + 1;
                    while ($j < $len && substr($raw, $j, 1) =~ /\s/) { $j++; }
                    if ($j < $len && substr($raw, $j, 1) eq ':') {
                        my $key = $stack_keys[-1]{_pending};
                        delete $stack_keys[-1]{_pending};
                        if (defined $key) {
                            die("inspect_model.pl: numeric plan $path has duplicate object key '$key'\n")
                                if exists $stack_keys[-1]{keys}{$key};
                            $stack_keys[-1]{keys}{$key} = 1;
                        }
                        $expect_key = 0;
                    }
                }
            }
            $i++;
            next;
        }
        if ($ch eq '"') {
            $in_string = 1;
            if (@stack_keys && $stack_keys[-1]{expecting_key}) {
                # Decode the complete JSON string so escaped spellings share the
                # same identity as their decoded key.
                my $j = $i + 1;
                my $encoded = '"';
                my $esc = 0;
                while ($j < $len) {
                    my $c = substr($raw, $j, 1);
                    $encoded .= $c;
                    if ($esc) { $esc = 0; $j++; next; }
                    if ($c eq "\\") { $esc = 1; $j++; next; }
                    last if $c eq '"';
                    $j++;
                }
                my $key;
                eval {
                    $key = JSON::PP->new->ascii(1)->decode($encoded);
                    1;
                } or do {
                    my $error = $@ || 'key decode failed';
                    die("inspect_model.pl: numeric plan $path has invalid object key: $error");
                };
                die("inspect_model.pl: numeric plan $path object key is not a string\n")
                    if ref($key);
                $stack_keys[-1]{_pending} = $key;
                $expect_key = 1;
            }
            $i++;
            next;
        }
        if ($ch eq '{') {
            push @stack_keys, { keys => {}, expecting_key => 1 };
            $i++;
            next;
        }
        if ($ch eq '}') {
            pop @stack_keys if @stack_keys;
            $i++;
            next;
        }
        if ($ch eq '[') {
            # arrays do not introduce object keys
            push @stack_keys, { keys => {}, expecting_key => 0, array => 1 } if 0; # no-op marker
            $i++;
            next;
        }
        if ($ch eq ']') { $i++; next; }
        if ($ch eq ',' && @stack_keys && !$stack_keys[-1]{array}) {
            $stack_keys[-1]{expecting_key} = 1;
            $i++;
            next;
        }
        if ($ch eq ':' && @stack_keys) {
            $stack_keys[-1]{expecting_key} = 0;
            $i++;
            next;
        }
        $i++;
    }
}

sub project_sv {
    my ($sv) = @_;
    my $b     = B::svref_2object(\$sv);
    my $flags = $b->FLAGS;
    return {
        class => ref($b),
        iok   => (($flags & B::SVf_IOK) ? JSON::PP::true : JSON::PP::false),
        nok   => (($flags & B::SVf_NOK) ? JSON::PP::true : JSON::PP::false),
        pok   => (($flags & B::SVf_POK) ? JSON::PP::true : JSON::PP::false),
        is_uv => (($flags & B::SVf_IVisUV) ? JSON::PP::true : JSON::PP::false),
    };
}

sub tagged_model_value {
    my ($value) = @_;
    if (!defined($value)) {
        return undef;
    }
    if (ref($value) eq 'HASH' && exists $value->{state} && $value->{state} eq 'never_evaluated') {
        return { state => 'never_evaluated' };
    }
    my $text;
    my $signed_zero = JSON::PP::false;
    {
        no warnings qw(numeric uninitialized);
        if ("$value" eq '-0' || (0 + $value == 0 && "$value" =~ /^-/)) {
            $text        = '-0';
            $signed_zero = JSON::PP::true;
        }
        elsif ($value != $value) {
            $text = "$value";
        }
        else {
            my $inf = 9**9**9;
            if ($value == $inf || $value == -$inf) {
                $text = "$value";
            }
            else {
                $text = "$value";
            }
        }
    }
    my $projection = project_sv($value);
    return {
        text        => $text,
        signed_zero => $signed_zero,
        scalar      => $projection,
    };
}

sub classify_lexeme {
    my ($lexeme, $threshold_enabled, $threshold_text) = @_;
    # Controlled pinned-Perl probe on a fresh scalar from the plan lexeme.
    my $sv = "$lexeme";
    my $sv_before = project_sv($sv);
    my $never = ($lexeme eq '-');
    if ($never) {
        return {
            looks_like_number            => undef,
            sv_before                    => $sv_before,
            sv_after_looks_like_number   => undef,
            sv_after_negative_compare    => undef,
            sv_after_threshold_compare   => undef,
            value_class                  => 'not_evaluated',
            negative                     => JSON::PP::false,
            threshold_enabled            => $threshold_enabled ? JSON::PP::true : JSON::PP::false,
            threshold_text               => $threshold_enabled ? "$threshold_text" : undef,
            greater_than_threshold       => undef,
            category                     => undef,
            recovery                     => 'never evaluated',
        };
    }

    my $lln = looks_like_number($sv) ? 1 : 0;
    my $sv_after_lln = project_sv($sv);
    my ($sv_after_neg, $sv_after_thr) = (undef, undef);
    my $negative = JSON::PP::false;
    my $greater  = undef;
    my $category = undef;
    my $recovery = undef;
    my $value_class = 'nonnumeric';

    if (!$lln) {
        $category = 'format';
        $recovery = 'zero';
    }
    else {
        {
            no warnings qw(numeric uninitialized);
            if ($sv != $sv) {
                $value_class = 'nan';
            }
            else {
                my $inf = 9**9**9;
                if ($sv == $inf) {
                    $value_class = 'positive_infinity';
                }
                elsif ($sv == -$inf) {
                    $value_class = 'negative_infinity';
                }
                else {
                    $value_class = 'finite';
                }
            }
            my $is_negative = ($sv < 0) ? 1 : 0;
            $sv_after_neg = project_sv($sv);
            if ($is_negative) {
                $negative = JSON::PP::true;
                $category = 'negative';
                $recovery = 'zero';
            }
            else {
                if ($threshold_enabled) {
                    my $thr = 0 + $threshold_text;
                    my $is_gt = ($sv > $thr) ? 1 : 0;
                    $sv_after_thr = project_sv($sv);
                    $greater = $is_gt ? JSON::PP::true : JSON::PP::false;
                    if ($is_gt) {
                        $category = 'excessive';
                        $recovery = 'retain value';
                    }
                    else {
                        $category = undef;
                        $recovery = ($lexeme eq '-0') ? 'retain signed zero' : 'retain value';
                    }
                }
                else {
                    $category = undef;
                    $recovery = ($lexeme eq '-0') ? 'retain signed zero' : 'retain value';
                }
            }
        }
    }

    return {
        looks_like_number            => $lln ? JSON::PP::true : JSON::PP::false,
        sv_before                    => $sv_before,
        sv_after_looks_like_number   => $sv_after_lln,
        sv_after_negative_compare    => $sv_after_neg,
        sv_after_threshold_compare   => $sv_after_thr,
        value_class                  => $value_class,
        negative                     => $negative,
        threshold_enabled            => $threshold_enabled ? JSON::PP::true : JSON::PP::false,
        threshold_text               => $threshold_enabled ? "$threshold_text" : undef,
        greater_than_threshold       => $greater,
        category                     => $category,
        recovery                     => $recovery,
    };
}

sub locator_key {
    my ($family, $locator) = @_;
    if ($family eq 'DA') {
        return "DA:" . $locator->{line};
    }
    if ($family eq 'FNDA') {
        return "FNDA:" . $locator->{function_name} . "\0" . $locator->{alias};
    }
    if ($family eq 'FNA') {
        return "FNA:" . $locator->{function_index} . "\0" . $locator->{alias};
    }
    if ($family eq 'BRDA') {
        my $expr = exists $locator->{expression} ? (defined $locator->{expression} ? $locator->{expression} : "\x00") : die("missing expression");
        return join("\0", 'BRDA', $locator->{line}, $locator->{block}, $locator->{branch}, $expr);
    }
    die("unknown family $family");
}


sub brda_fixture_block_map {
    # Rebuild the fixture-block -> renumbered-idx map by replaying BRDA grouping
    # rules from the original input files. Model block indices are renumbered
    # per source line, starting at zero in order of first appearance.
    my (@inputs) = @_;
    my %map;       # "$source\0$line\0$fixture_block" => renumbered_idx
    my %next_idx;  # "$source\0$line" => next renumbered idx
    my $source;
    for my $path (@inputs) {
        open(my $fh, '<', $path) or die("cannot read $path: $!");
        my ($current_line, $current_block);
        while (my $line = <$fh>) {
            chomp($line);
            if ($line =~ /^SF:(.*)$/) {
                $source = $1;
                $current_line  = undef;
                $current_block = undef;
                next;
            }
            if ($line =~ /^end_of_record/) {
                $source = undef;
                $current_line  = undef;
                $current_block = undef;
                next;
            }
            next unless defined($source);
            if ($line =~ /^BRDA:(\d+),([ef]?)(U?)(\d+),(.+)$/) {
                my ($ln, $block) = ($1, $4);
                if (!defined($current_line) ||
                    $ln != $current_line ||
                    !defined($current_block) ||
                    $block != $current_block)
                {
                    $current_line  = $ln;
                    $current_block = $block;
                    my $key = join("\0", $source, $ln, $block);
                    if (!exists $map{$key}) {
                        my $line_key = join("\0", $source, $ln);
                        my $idx = exists $next_idx{$line_key} ? $next_idx{$line_key} : 0;
                        $map{$key} = $idx;
                        $next_idx{$line_key} = $idx + 1;
                    }
                }
            }
        }
        close($fh);
    }
    return \%map;
}

sub extract_model_value {
    my ($info, $family, $locator, $view, $block_map, $source) = @_;
    # $view is 'aggregate' or 'testcase'
    if ($family eq 'DA') {
        my $map;
        if ($view eq 'aggregate') {
            $map = $info->sum();
        }
        else {
            my @names = $info->test()->keylist();
            die("missing testcase line map") unless @names;
            # Independent read from the actual test map for the sole testcase.
            # Empty TN yields the empty-string testcase name, which is still valid.
            $map = $info->test()->value($names[0]);
        }
        die("missing DA map in $view") unless defined($map);
        my $line = 0 + $locator->{line};
        my %keys = map { $_ => 1 } $map->keylist();
        die("missing DA line $line in $view") unless $keys{$line};
        # Zero is a valid retained count; never treat a defined zero as missing.
        return tagged_model_value($map->value($line));
    }
    if ($family eq 'FNDA' || $family eq 'FNA') {
        my $alias = $locator->{alias};
        die("missing function alias in locator") unless defined($alias);
        if ($family eq 'FNDA') {
            die("FNDA locator missing function_name") unless defined($locator->{function_name});
        }
        if ($family eq 'FNA') {
            die("FNA locator missing function_index") unless defined($locator->{function_index});
        }
        my $func_map;
        if ($view eq 'aggregate') {
            $func_map = $info->func();
        }
        else {
            my @names = $info->testfnc()->keylist();
            die("missing testcase function map") unless @names;
            $func_map = $info->testfnc()->value($names[0]);
        }
        die("missing function map in $view") unless defined($func_map);
        my $found;
        foreach my $key ($func_map->keylist()) {
            my $entry = $func_map->findKey($key);
            my $aliases = $entry->aliases();
            next unless exists $aliases->{$alias};
            if (defined $found) {
                die("ambiguous function match for alias $alias in $view");
            }
            $found = tagged_model_value($aliases->{$alias});
        }
        die("missing function alias $alias in $view") unless defined($found);
        return $found;
    }
    if ($family eq 'BRDA') {
        my $line   = 0 + $locator->{line};
        my $fixture_block = 0 + $locator->{block};
        my $branch_token  = $locator->{branch};
        my $expr   = $locator->{expression};
        my $br_map;
        if ($view eq 'aggregate') {
            $br_map = $info->sumbr();
        }
        else {
            my @names = $info->testbr()->keylist();
            die("missing testcase branch map") unless @names;
            $br_map = $info->testbr()->value($names[0]);
        }
        die("missing branch map in $view") unless defined($br_map);
        my %keys = map { $_ => 1 } $br_map->keylist();
        die("missing BRDA line $line in $view") unless $keys{$line};
        my $location = $br_map->value($line);
        my $map_key = join("\0", $source, $line, $fixture_block);
        die("missing BRDA fixture block map for $source:$line block=$fixture_block")
            unless defined($block_map) && exists $block_map->{$map_key};
        my $model_block_idx = 0 + $block_map->{$map_key};
        my $target;
        foreach my $blk ($location->blocks()) {
            next unless 0 + $blk->idx() == $model_block_idx;
            $target = $blk;
            last;
        }
        die("missing BRDA model block idx=$model_block_idx on line $line in $view")
            unless defined($target);
        # Within a fixture block group the reader assigns sequential element ids
        # starting at zero. When the fixture branch token is a pure integer and
        # expression is null, that integer equals the sequential element id for
        # ordinary numeric branch indices. Expression-bearing rows match by expr.
        foreach my $element (@{ $target->elements() }) {
            my $element_expr = defined($element->expr()) ? $element->expr() : undef;
            my $matched = 0;
            if (defined($expr)) {
                $matched = (defined($element_expr) && $element_expr eq $expr) ? 1 : 0;
                # Also require branch token equality when the plan branch is numeric.
                if ($matched && defined($branch_token) && "$branch_token" =~ /^-?\d+$/) {
                    $matched = (0 + $element->id() == 0 + $branch_token) ? 1 : 0;
                }
            }
            else {
                # expression null: match sequential id to integer branch token.
                if (defined($branch_token) && "$branch_token" =~ /^-?\d+$/) {
                    $matched = (0 + $element->id() == 0 + $branch_token) ? 1 : 0;
                }
                else {
                    $matched = (defined($element_expr) && $element_expr eq "$branch_token") ? 1 : 0;
                }
            }
            next unless $matched;
            if (!$element->isTaken()) {
                return { state => 'never_evaluated' };
            }
            return tagged_model_value($element->data());
        }
        die("missing BRDA element line=$line block=$fixture_block branch=$branch_token in $view");
    }
    die("unknown family $family");
}

sub scan_numeric_records_from_fixture {
    my ($path) = @_;
    open(my $fh, '<:raw', $path) or die("inspect_model.pl: cannot read fixture $path: $!\n");
    local $/;
    my $raw = <$fh>;
    close($fh);
    die("inspect_model.pl: fixture $path is empty\n") unless defined($raw) && length($raw);
    my @records;
    my $source;
    my $ordinal = 0;
    for my $line (split(/\n/, $raw, -1)) {
        $line =~ s/\r$//;
        if ($line =~ /^SF:(.*)$/) {
            $source = $1;
            $ordinal = 0;
            next;
        }
        if ($line =~ /^end_of_record/) {
            $source = undef;
            $ordinal = 0;
            next;
        }
        next unless defined($source);
        if ($line =~ /^(DA|FNDA|FNA|BRDA):(.*)$/) {
            my ($family, $rest) = ($1, $2);
            $ordinal += 1;
            my ($lexeme, $locator, $raw_record);
            $raw_record = "$family:$rest";
            if ($family eq 'DA') {
                my ($ln, $count) = split(/,/, $rest, 2);
                die("inspect_model.pl: malformed DA in $path: $line\n") unless defined($count);
                $lexeme = $count;
                $locator = { line => 0 + $ln };
            }
            elsif ($family eq 'FNDA') {
                my ($count, $name) = split(/,/, $rest, 2);
                die("inspect_model.pl: malformed FNDA in $path: $line\n") unless defined($name);
                $lexeme = $count;
                $locator = { function_name => $name, alias => $name };
            }
            elsif ($family eq 'FNA') {
                my ($idx, $count, $alias) = split(/,/, $rest, 3);
                die("inspect_model.pl: malformed FNA in $path: $line\n") unless defined($alias);
                $lexeme = $count;
                $locator = { function_index => 0 + $idx, alias => $alias };
            }
            else {
                # BRDA: line, block-prefix?, branch, count/expression tail
                # Keep fixture-block as the numeric block index from the record.
                if ($rest =~ /^(\d+),([ef]?)(U?)(\d+),(.+)$/) {
                    my ($ln, $block, $branch_and_count) = ($1, $4, $5);
                    # branch_and_count is "branch,count" or "branch,expr,count"?
                    # Standard form: BRDA:line,block,branch,count
                    # After block, remaining is branch,count where branch may be non-numeric.
                    my ($branch_token, $count) = split(/,/, $branch_and_count, 2);
                    die("inspect_model.pl: malformed BRDA in $path: $line\n") unless defined($count);
                    my $branch_value = ($branch_token =~ /^-?\d+$/) ? 0 + $branch_token : $branch_token;
                    $lexeme = $count;
                    $locator = {
                        line => 0 + $ln,
                        block => 0 + $block,
                        branch => $branch_value,
                        expression => undef,
                    };
                }
                else {
                    die("inspect_model.pl: unparsed BRDA in $path: $line\n");
                }
            }
            push @records, {
                family => $family,
                lexeme => $lexeme,
                raw_record => $raw_record,
                record_ordinal => $ordinal,
                locator => $locator,
                source => $source,
            };
        }
    }
    return \@records;
}

sub locator_equal {
    my ($family, $a, $b) = @_;
    return 0 unless ref($a) eq 'HASH' && ref($b) eq 'HASH';
    if ($family eq 'DA') {
        return ((0 + ($a->{line} // -1)) == (0 + ($b->{line} // -2))) ? 1 : 0;
    }
    if ($family eq 'FNDA') {
        return (
            defined($a->{function_name}) && defined($b->{function_name})
            && defined($a->{alias}) && defined($b->{alias})
            && $a->{function_name} eq $b->{function_name}
            && $a->{alias} eq $b->{alias}
        ) ? 1 : 0;
    }
    if ($family eq 'FNA') {
        return (
            defined($a->{function_index}) && defined($b->{function_index})
            && defined($a->{alias}) && defined($b->{alias})
            && (0 + $a->{function_index}) == (0 + $b->{function_index})
            && $a->{alias} eq $b->{alias}
        ) ? 1 : 0;
    }
    if ($family eq 'BRDA') {
        my $ae = $a->{expression};
        my $be = $b->{expression};
        my $expr_ok = (!defined($ae) && !defined($be)) || (defined($ae) && defined($be) && $ae eq $be);
        return 0 unless $expr_ok;
        return (
            (0 + ($a->{line} // -1)) == (0 + ($b->{line} // -2))
            && (0 + ($a->{block} // -1)) == (0 + ($b->{block} // -2))
            && ("$a->{branch}" eq "$b->{branch}")
        ) ? 1 : 0;
    }
    return 0;
}

sub match_plan_row_to_fixture_record {
    my ($plan_row, $records) = @_;
    my $family = $plan_row->{family};
    my $found;
    for my $rec (@$records) {
        next unless $rec->{family} eq $family;
        next unless $rec->{source} eq $plan_row->{source};
        next unless $rec->{lexeme} eq $plan_row->{lexeme};
        next unless $rec->{raw_record} eq $plan_row->{raw_record};
        next unless locator_equal($family, $rec->{locator}, $plan_row->{locator});
        if (defined $found) {
            die("inspect_model.pl: ambiguous fixture match for $plan_row->{id}\n");
        }
        $found = $rec;
    }
    return $found;
}

sub build_numeric_rows {
    my ($plan, $trace, $threshold_enabled, $threshold_text, $block_map) = @_;
    die("inspect_model.pl: numeric plan missing rows array\n")
        unless exists $plan->{rows} && ref($plan->{rows}) eq 'ARRAY';
    my @plan_rows = @{$plan->{rows}};
    my %seen_ids;
    my %seen_locators;
    my @rows;
    my %source_info = map { $_ => $trace->data($_) } $trace->files();
    my %fixture_scan_cache;

    for my $index (0 .. $#plan_rows) {
        my $plan_row = $plan_rows[$index];
        die("inspect_model.pl: numeric plan row $index must be an object\n")
            unless ref($plan_row) eq 'HASH';
        for my $key (qw(id family lexeme fixture source testcase reader_match_kind raw_record record_ordinal locator)) {
            die("inspect_model.pl: numeric plan row missing $key\n") unless exists $plan_row->{$key};
        }
        my $id = $plan_row->{id};
        die("inspect_model.pl: duplicate plan id $id\n") if $seen_ids{$id}++;
        my $family = $plan_row->{family};
        die("inspect_model.pl: unknown family $family\n")
            unless $family eq 'DA' || $family eq 'FNDA' || $family eq 'FNA' || $family eq 'BRDA';
        die("inspect_model.pl: MC/DC is out of scope for TF-030\n") if $family eq 'MCDC';
        my $locator = $plan_row->{locator};
        die("inspect_model.pl: locator must be an object\n") unless ref($locator) eq 'HASH';
        if ($family eq 'DA') {
            die("inspect_model.pl: DA locator requires line\n") unless exists $locator->{line};
        }
        elsif ($family eq 'FNDA') {
            die("inspect_model.pl: FNDA locator requires function_name and alias\n")
                unless exists $locator->{function_name} && exists $locator->{alias};
        }
        elsif ($family eq 'FNA') {
            die("inspect_model.pl: FNA locator requires function_index and alias\n")
                unless exists $locator->{function_index} && exists $locator->{alias};
        }
        elsif ($family eq 'BRDA') {
            for my $key (qw(line block branch expression)) {
                die("inspect_model.pl: BRDA locator requires $key\n") unless exists $locator->{$key};
            }
        }
        my $lkey = locator_key($family, $locator);
        die("inspect_model.pl: duplicate locator for $id\n") if $seen_locators{$lkey}++;

        my $source = $plan_row->{source};
        die("inspect_model.pl: missing source $source for $id\n") unless exists $source_info{$source};
        my $info = $source_info{$source};

        # Bind plan row against actual fixture bytes before model extract.
        my $fixture_rel = $plan_row->{fixture};
        die("inspect_model.pl: $id fixture path missing\n") unless defined($fixture_rel) && length($fixture_rel);
        my $fixture_path;
        for my $candidate (
            $fixture_rel,
            File::Basename::basename($fixture_rel),
            # Capture workdirs mount the case fixture as input.info.
            'input.info',
        )
        {
            if (defined($candidate) && length($candidate) && -f $candidate) {
                $fixture_path = $candidate;
                last;
            }
        }
        die("inspect_model.pl: $id cannot locate fixture bytes for $fixture_rel\n")
            unless defined($fixture_path);
        if (!exists $fixture_scan_cache{$fixture_path}) {
            $fixture_scan_cache{$fixture_path} = scan_numeric_records_from_fixture($fixture_path);
        }
        my $fixture_records = $fixture_scan_cache{$fixture_path};
        my $matched_rec = match_plan_row_to_fixture_record($plan_row, $fixture_records);
        die("inspect_model.pl: $id plan row not found in fixture bytes\n") unless defined($matched_rec);
        die("inspect_model.pl: $id record_ordinal drift plan="
            . (0 + $plan_row->{record_ordinal})
            . " fixture="
            . (0 + $matched_rec->{record_ordinal})
            . "\n")
            unless (0 + $plan_row->{record_ordinal}) == (0 + $matched_rec->{record_ordinal});
        # Prove identity fields from fixture scan, not plan literals alone.
        die("inspect_model.pl: $id family mismatch against fixture\n")
            unless $matched_rec->{family} eq $family;
        die("inspect_model.pl: $id lexeme mismatch against fixture\n")
            unless $matched_rec->{lexeme} eq $plan_row->{lexeme};
        die("inspect_model.pl: $id raw_record mismatch against fixture\n")
            unless $matched_rec->{raw_record} eq $plan_row->{raw_record};

        my $classification = classify_lexeme(
            $plan_row->{lexeme},
            $threshold_enabled,
            $threshold_text,
        );

        # record_matched is true only when fixture scan identity closed.
        my $record_matched = JSON::PP::true;
        my $retained       = JSON::PP::true;
        my $skipped        = JSON::PP::false;
        my ($stored_aggregate, $stored_testcase);
        eval {
            $stored_aggregate = extract_model_value($info, $family, $locator, 'aggregate', $block_map, $source);
            $stored_testcase  = extract_model_value($info, $family, $locator, 'testcase', $block_map, $source);
            1;
        } or do {
            my $error = $@ || 'extract failed';
            die("inspect_model.pl: $id model extract failed: $error");
        };

        # BRDA never-evaluated is retained without looks_like_number.
        if ($plan_row->{reader_match_kind} eq 'brda_never_evaluated') {
            die("inspect_model.pl: $id never-evaluated requires BRDA '-'\n")
                unless $family eq 'BRDA' && $plan_row->{lexeme} eq '-';
            $classification = classify_lexeme('-', $threshold_enabled, $threshold_text);
            $stored_aggregate = { state => 'never_evaluated' };
            $stored_testcase  = { state => 'never_evaluated' };
        }

        # retained/skipped derived from category recovery path for ignored diagnostics.
        # For successful semantic snapshot capture paths, ignored diagnostics still retain
        # the coerced or original model value; skipped remains false when extract succeeded.
        if (!defined($stored_aggregate)) {
            $retained = JSON::PP::false;
            $skipped  = JSON::PP::true;
            $record_matched = JSON::PP::false;
        }

        push(
            @rows,
            {
                id                           => $id,
                family                       => $family,
                lexeme                       => $plan_row->{lexeme},
                fixture                      => $plan_row->{fixture},
                source                       => $source,
                testcase                     => $plan_row->{testcase},
                reader_match_kind            => $plan_row->{reader_match_kind},
                raw_record                   => $matched_rec->{raw_record},
                record_ordinal               => 0 + $matched_rec->{record_ordinal},
                locator                      => $locator,
                record_matched               => $record_matched,
                retained                     => $retained,
                skipped                      => $skipped,
                looks_like_number            => $classification->{looks_like_number},
                sv_before                    => $classification->{sv_before},
                sv_after_looks_like_number   => $classification->{sv_after_looks_like_number},
                sv_after_negative_compare    => $classification->{sv_after_negative_compare},
                sv_after_threshold_compare   => $classification->{sv_after_threshold_compare},
                value_class                  => $classification->{value_class},
                negative                     => $classification->{negative},
                threshold_enabled            => $classification->{threshold_enabled},
                threshold_text               => $classification->{threshold_text},
                greater_than_threshold       => $classification->{greater_than_threshold},
                category                     => $classification->{category},
                recovery                     => $classification->{recovery},
                stored_aggregate             => $stored_aggregate,
                stored_testcase              => $stored_testcase,
            }
        );
    }
    return \@rows;
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

if (defined($numeric_plan_path)) {
    my ($plan, $plan_raw) = ($early_numeric_plan, $early_numeric_plan_raw);
    my $threshold_enabled = defined($excessive_threshold) ? 1 : 0;
    my $block_map = brda_fixture_block_map(@resolved_inputs);
    $document->{numeric_rows} = build_numeric_rows(
        $plan,
        $trace,
        $threshold_enabled,
        $excessive_threshold,
        $block_map,
    );
}

my $json = JSON::PP->new->canonical(1)->ascii(1)->pretty(1)->encode($document);
print $json;
