#!/usr/bin/perl

use strict;
use warnings;

my @url = ();
my @savePath = ();

$url[0] = 'https://habarovsk.cian.ru/snyat-1-komnatnuyu-kvartiru/';
$savePath[0] = '/home/user/WWW/i/eur_cb_forex_000066_88x90.gif';

# $url[1] = 'http://informer.gismeteo.ru/27196-6.GIF';
# $savePath[1] = '/home/user/WWW/i/27196-6.GIF';


use LWP::UserAgent;
use Data::Dumper;

my $browser = LWP::UserAgent->new();


# если нужно использовать прокси
 $browser->proxy('http', 'http://178.132.223.96:57332/');


my @headers = (
	'User-Agent'      => 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.0.3705)',
	'Accept'          => 'image/png, image/jpeg, image/gif, text/html, text/plain, */*',
	'Accept-Charset'  => 'utf-8',
	'Accept-Language' => 'ru',
);

my $i = 0;

foreach (@url) {

	my $response = $browser->get($_, @headers);

	print Dumper $response;

	if ( $response->is_success ) {
        # print $response->content;
		if (open(FILE2, '>' . $savePath[$i])) {
			binmode(FILE2);
			flock(FILE2, 2);
			print FILE2 $response->content;
			flock(FILE2, 8);
			close(FILE2);
		}
	}
	$i++;
}
