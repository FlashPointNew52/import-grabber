package Rplus::Import::Item::Avito;


use feature 'say';

use Mojo::UserAgent;
use Data::Dumper;

use utf8;
use Encode;


use DateTime::Format::Strptime;
use Mojo::Util qw(trim);

use Rplus::Model::Result;
use Rplus::Util::Realty qw(save_data_to_all);
use Rplus::Modern;
use Rplus::Class::Media;
use Rplus::Class::Interface;
use Rplus::Class::UserAgent;

use JSON;
use Data::Dumper;

no warnings 'experimental';


my $media_name = 'avito';

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
