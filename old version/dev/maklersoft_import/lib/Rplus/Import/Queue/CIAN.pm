package Rplus::Import::Queue::CIAN;

use DateTime::Format::Strptime;

use Rplus::Modern;
use Rplus::Class::Media;
use Rplus::Class::Interface;
use Rplus::Class::UserAgent;
use Rplus::Util::Task qw(add_task);
use File::Basename;
use Rplus::Model::History::Manager;
use LWP::UserAgent;
use JSON;
use Data::Dumper;

no warnings 'experimental';

my $media_name = 'cian';
my $media_data;
my $parser = DateTime::Format::Strptime->new(pattern => '%Y-%m-%d %H:%M:%S');
my $ua;

sub enqueue_tasks {
    my ($location, $category) = @_;

    say 'loading ' . $media_name . ' - ' . $location . ' - ' . $category;

    my $list = _get_category($location,  $category);

    foreach (@{$list}) {

        my $eid = _make_eid($_->{id}, $_->{ts});

        unless (Rplus::Model::History::Manager->get_objects_count(query => [media => $media_name, location => $location, eid => $eid])) {
            say 'added' . $_->{url};
            Rplus::Model::History->new(media => $media_name, location => $location, eid => $eid)->save;
            add_task(
                'load_item',
                {media => $media_name, location => $location, url => $_->{url}},
                $media_name
            );
            #Rplus::Model::Task->new(url => $_->{url}, media => $media_name, location => $location)->save;
        }
    }
    say 'done';
}

sub _get_category {
    my ($location, $category) = @_;

    $media_data = Rplus::Class::Media->instance()->get_media($media_name, $location);
    # $ua = Rplus::Class::UserAgent->new(Rplus::Class::Interface->instance()->get_interface());

    my @url_list;
    say Dumper @url_list;
    my $t = _get_url_list($media_data->{site_url} . $category, $media_data->{page_count}, $media_data->{pause});
    push @url_list, @{$t};

    return \@url_list;
}

sub _get_url_list {
    my ($category_page, $page_count, $pause) = @_;
    my @url_list;
    my $browser = LWP::UserAgent->new();

    my @headers = (
        'User-Agent'      => 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.0.3705)',
        'Accept'          => 'image/png, image/jpeg, image/gif, text/html, text/plain, */*',
        'Accept-Charset'  => 'utf-8',
        'Accept-Language' => 'ru',
    );
    for(my $i = 1; $i <= $page_count; $i ++) {
        $browser->proxy('http', 'http://'.Rplus::Class::Interface->get_proxy().'/');
        my $res = $browser->get($category_page . '?p=' . $i, @headers);
        if ($res->is_success && $res->content) {
            my $dom = Mojo::DOM->new($res->content);
            say "objects" . $dom->find('div[class*="offer-container"]')->size;
            $dom->find('div[class*="offer-container"]')->each (sub {
                my $item_url = $_->find('a[class*="-header--1_m0_"]');
                if ($item_url->size > 0){
                    $item_url = $item_url->first->{href};
                } else{
                    $item_url = $_->find('a[class*="--header--1C"]');
                    if ($item_url->size > 0) {
                        $item_url = $item_url->first->{href};
                    } else{
                        $item_url = $_->find('a[class*="-header-link--"]')->first->{href};
                    }
                }
                my $item_id = basename($item_url);
                my $date_str = $_->find('div[class*="absolute"]')->first->text;
                my $ts = _parse_date($date_str);
                push(@url_list, {id => $item_id, url => $item_url, ts => $ts});
            });
        }

        unless ($i + 1 == $page_count) {
            sleep $pause;
        }
    }

    return \@url_list;
}

sub _parse_date {
    my $date = lc(shift);

    my $res;
    my $dt_now = DateTime->now();
    my $year = $dt_now->year();
    my $mon = $dt_now->month();
    my $mday = $dt_now->mday();

    if ($date =~ /сегодня, (\d{1,2}):(\d{1,2})/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2:00");
        if ($res > $dt_now) {
            # substr 1 day
            $res->subtract(days => 1);
        }
    } elsif ($date =~ /вчера, (\d{1,2}):(\d{1,2})/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2:00");
        # substr 1 day
        $res->subtract(days => 1);
    } elsif ($date =~ /(\d+) (\w+), (\d{1,2}):(\d{1,2})/) {
        my $a_mon = _month_num($2);
        my $a_year = $year;
        if ($a_mon > $mon) { $a_year -= 1; }
        $res = $parser->parse_datetime("$a_year-$a_mon-$1 $3:$4:00");
    } else {
        $res = $dt_now;
    }

    return $res;
}

sub _month_num {
    my $month_str = lc(shift);

    given ($month_str) {
        when (/янв/) {
            return 1;
        }
        when (/фев/) {
            return 2;
        }
        when (/мар/) {
            return 3;
        }
        when (/апр/) {
            return 4;
        }
        when (/мая/) {
            return 5;
        }
        when (/июн/) {
            return 6;
        }
        when (/июл/) {
            return 7;
        }
        when (/авг/) {
            return 8;
        }
        when (/сен/) {
            return 9;
        }
        when (/окт/) {
            return 10;
        }
        when (/ноя/) {
            return 11;
        }
        when (/дек/) {
            return 12;
        }
    }
    return 0;
}

sub _make_eid {
    my ($id, $date) = @_;
    return $id . '_' . $date->strftime('%Y%m%d')
}

1;
