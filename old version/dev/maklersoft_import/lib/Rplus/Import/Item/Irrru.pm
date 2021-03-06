package Rplus::Import::Item::Irrru;

use feature 'say';

use Mojo::UserAgent;

use utf8;
use Encode;

use DateTime::Format::Strptime;
use MIME::Base64;
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


my $media_name = 'irr';

sub get_item {
    my ($location, $item_url) = @_;
    say 'loading ' . $media_name . ' - ' . $location . ' - ' . $item_url;
    my $data = _get_item($location, $item_url);
    my $id_it = save_data_to_all($data, $media_name, $location);
    say 'save new ' . $media_name . ' ' . $id_it;
}

sub _get_item {
    my ($location, $item_url) = @_;
    my $ip = Rplus::Class::Interface->instance()->get_interface();
    my $media_data = Rplus::Class::Media->instance()->get_media($media_name, $location);
    my $user_agent = Mojo::UserAgent->new;

    sleep($media_data->{pause});
    my $raw_data = $user_agent->inactivity_timeout(0)->connect_timeout(45)->request_timeout(0)->get('http://localhost:9000/get_media_data?url='.$item_url.'&ip='.$ip)->res->{'buffer'};

    my $data = decodeJSON($raw_data);
    say Dumper $data;

    return $data;
}

sub decodeJSON {
    my ($JSONText) = @_;
    my $hashRef = decode_json($JSONText);
    return $hashRef;
}

# sub decodeJSON {
#     my ($JSONText) = @_;
#     my $hashRef = decode_json(Encode::encode_utf8($JSONText));
#     return $hashRef;
# }

1;
