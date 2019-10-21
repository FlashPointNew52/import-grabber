package Rplus::Class::Interface {

    use String::Urandom;
    use Rplus::Modern;
    use Rplus::Util::Config qw(get_config);
    use Data::Dumper;
    use utf8;

    use Cwd qw/abs_path/;
    use Mojo::Asset::File;
    my $instance;

    sub instance {
        $instance ||= (shift)->new();
    }

    sub new {
        my ($class) = @_;

        my $conf = get_config('endpoints');
        my $self = {
            endpoints => $conf->{endpoints},
        };

        bless $self, $class;

        return $self;
    }

    sub get_interface {
        my ($self) = @_;

        #if ($self->{pointer} >= @{$self->{endpoints}}) {
        #}

        my $obj = String::Urandom->new(
              LENGTH => 3,
              CHARS  => [ qw/ 1 2 3 4 5 6 7 8 9 0 / ]
            );

        my $sz = scalar @{$self->{endpoints}};
        my $idx = int(($obj->rand_string / 999) * ($sz));
        say 'rand idx: ' . $idx;

        return $self->{endpoints}->[$idx];
    }

    sub get_proxy {
        my ($self) = @_;

        #if ($self->{pointer} >= @{$self->{endpoints}}) {
        #}

        my $obj = String::Urandom->new(
            LENGTH => 3,
            CHARS  => [ qw/ 1 2 3 4 5 6 7 8 9 0 / ]
        );
        my $module = __PACKAGE__;

        $module =~s/::/\//g;
        my $path = $INC{$module . '.pm'};
        $path =~ s{^(.*/)[^/]*$}{$1};
        my $filename = abs_path($path . '/../../../' . 'python_server/proxy_list.txt');
        open(my $fh, '<:encoding(UTF-8)', $filename)
            or die "Could not open file '$filename' $!";
        my $i = 0;
        my $idx = int(($obj->rand_string / 999) * (130));

        while (my $row = <$fh>) {
            chomp $row;
            if($i == $idx){
                say 'rand proxy: ' . $row;
                return $row;
            }
            $i++;
        }
    }
}

1;