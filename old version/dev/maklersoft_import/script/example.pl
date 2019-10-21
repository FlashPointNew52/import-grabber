#!/usr/bin/env perl
use FindBin;
use lib "$FindBin::Bin/../lib";
use DateTime::Format::Strptime;

use Rplus::Modern;
use Rplus::Class::Media;
use Rplus::Class::Interface;
use Rplus::Class::UserAgent;
use Rplus::Util::Task qw(add_task);
use File::Basename;
use Rplus::Model::History::Manager;
use Rplus::Util::Realty qw(save_data_to_all);
use LWP::UserAgent;
use JSON;
use Data::Dumper;

no warnings 'experimental';

#my $media_name = 'cian';
my $media_name = 'avito';
my $media_data;
my $parser = DateTime::Format::Strptime->new(pattern => '%Y-%m-%d %H:%M:%S');
my $ua;
my @url_list;

#enqueue_tasks('khv', '/snyat-1-komnatnuyu-kvartiru-habarovskiy-kray/');
get_item('khv', '/habarovsk/komnaty/komnata_12_m_v_1-k_55_et._925977596');

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
    # $ua = Rplus::Class::UserAgent->new(Rplus::Class::Interface->instance()->get_interface(),  );

    my $t = _get_url_list($media_data->{site_url} . $category, $media_data->{page_count}, $media_data->{pause});
    push @url_list, @{$t};

    return \@url_list;
}

sub _get_url_list {
    my ($category_page, $page_count, $pause) = @_;

    my $browser = LWP::UserAgent->new();
    $browser->proxy('http', 'http://'.Rplus::Class::Interface->get_proxy().'/');
    my @headers = (
        'Connection'    => 'keep-alive',
        'Cache-Control' => 'no-cache',
        'Accept'        =>  'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'User-Agent'      => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
        #'Accept-Encoding' => 'gzip, deflate, br',
        'Accept-Language' => 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        # 'Accept-Charset'  => 'ISO-8859-1,utf-8;q=0.7,*;q=0.7'
    );

    for(my $i = 1; $i <= $page_count; $i ++) {

        # my $res = $ua->get_res($category_page . '?p=' . $i, []);
        my $res = $browser->get($category_page . '?p=' . $i, @headers);

        if ($res->is_success && $res->content) {
            say $res->content;
            my $dom = Mojo::DOM->new($res->content);
            # say $dom;
            say $dom;
            say "size =" . $dom->find('div[class*="offer-container"]')->size;
            $dom->find('div[class*="offer-container"]')->each (sub {
                if($res->content =~ /Catcha/){
                    print "CAPTCHA";
                    exit;
                }
                my $item_url = $_->find('a[class*="-header--1_m0_"]');
                say Dumper $item_url;

                if ($item_url->size > 0){
                    $item_url = $item_url->first->{href};
                }else{
                    $item_url = $_->find('a[class*="--header--1C"]');
                    if ($item_url->size > 0) {
                        $item_url = $item_url->first->{href};
                    } else{
                        $item_url = $_->find('a[class*="-header-link--"]')->first->{href};
                    }
                }
                say $item_url;
                # my $item_id = basename($item_url);
                # my $date_str = $_->find('div[class*="absolute"]')->first->text;
                # my $ts = _parse_date($date_str);
                # push(@url_list, {id => $item_id, url => $item_url, ts => $ts});
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



sub get_item {
    my ($location, $item_url) = @_;
    say 'loading ' . $media_name . ' - ' . $location . ' - ' . $item_url;
    my $data = _get_item($location, $item_url);
    my $id_it = save_data_to_all($data, $media_name, $location);
    say 'save new avito '.$id_it;
}

sub _get_item {
    my ($location, $item_url) = @_;
    my $ip = Rplus::Class::Interface->instance()->get_interface();
    my $media_data = Rplus::Class::Media->instance()->get_media($media_name, $location);

    my $user_agent = Mojo::UserAgent->new;

    sleep($media_data->{pause});
    my $raw_data = $user_agent->inactivity_timeout(0)->connect_timeout(45)->request_timeout(0)->get('http://localhost:9000/get_media_data?url=https://www.avito.ru'.$item_url.'&ip='.$ip)->res->{'buffer'};
    if (!defined $raw_data){
        die "Error:  null data" ;
    }elsif ($raw_data =~ '(error:)(.*)'){
       die "Error: " . $2;
    } else{
        my $data = decodeJSON($raw_data);
        my $res;
        my $counter = 0;
        while(1){
            my $ua = Rplus::Class::UserAgent->new(Rplus::Class::Interface->instance()->get_interface());
            $res = $ua->get_res('m.avito.ru'. $item_url, [
                Host => 'm.avito.ru',
                Referer => 'm.avito.ru'. $item_url,
                Accept => 'application/json, text/javascript, */*; q=0.01'
            ]);
            if(!$res && $counter < 10){
                sleep(5);
                $counter = $counter + 1;
            } else{
                last;
            }
        }

        my $dom = $res->dom;
        my $phone;
        $dom->find('a[data-marker="item-contact-bar/call"')->each (sub {
            if($_->{'data-marker'} eq 'item-contact-bar/call'){
                $phone = $_->{href} =~ s/tel:\+7/7/r;
                if (substr($phone, 0, 1) eq '8' && length($phone) == 11){
                    $phone=~ s/^8/7/;
                }elsif (length($phone) == 6){
                    $phone = '74212' . $phone
                }
            }

        });

        $data->{'phoneBlock'} = { 'main' => $phone};
        return $data;
    }



}

sub decodeJSON {
    my ($JSONText) = @_;
    my $hashRef = decode_json($JSONText);
    return $hashRef;
}

1;
