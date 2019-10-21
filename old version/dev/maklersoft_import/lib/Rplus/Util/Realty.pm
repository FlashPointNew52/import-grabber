package Rplus::Util::Realty;
binmode(STDOUT,':utf8');

use Rplus::Modern;
use utf8;
use Rplus::Model::Result;
use Rplus::Model::Result::Manager;
use JSON;
use Data::Dumper;
use Search::Elasticsearch;
use Rplus::Util::Geo;
use Geo::Hash;
use Exporter qw(import);
use Mojo::Util qw(trim);
use Try::Tiny;

our @EXPORT_OK = qw(save_data_to_all);

my $parser = DateTime::Format::Strptime->new( pattern => '%FT%T' );
my $parser_tz = DateTime::Format::Strptime->new( pattern => '%FT%T%z' );
my $media_name;
my $location;

my $e = Search::Elasticsearch->new(nodes => 'import.maklersoft.com:9200');

sub save_data_to_all {
    my ($data, $mn, $loc) = @_;
    my $id;
    unless ($data->{addDate}) {
        # my $dt = DateTime->now();
        # $data->{add_date} = $dt->datetime();
        $data->{addDate} = time;
        $data->{changeDate} = $data->{addDate};
    }
    while(my ($k,$v)=each(%$data)) {
        if(defined $v){
            $v = trim($v);
            $v =~ s/^\n{1,}//i;
            $v =~ s/\n{1,}$//i;
        }

    }

    $id = Rplus::Model::Result->new(metadata => to_json($data), media => $mn, location => $loc)->save;
    my $save_obj;
    if ($data->{addressBlock}) {
        my $address_str = '';
        foreach my $key (keys %{$data->{addressBlock}}) {
            if(defined $data->{addressBlock}->{$key}){
                $address_str = $address_str . $data->{addressBlock}->{$key}. ' ';
            }
        }
        my %coords = Rplus::Util::Geo::get_coords_by_addr(undef, $address_str, undef);
        if (%coords) {
            $data->{location} = {"lat" => $coords{latitude},"lon"=> $coords{longitude}};
        }

        my %area = Rplus::Util::Geo::get_district_by_coords($coords{latitude}, $coords{longitude});
        $data->{addressBlock}->{admArea} = $area{district};
        $data->{addressBlock}->{area} = $area{subdistrict};
        $data->{addressBlock}->{metro} = $area{metro};
        my $gh = Geo::Hash->new;
        my $geohash = $gh->encode($coords{latitude}, $coords{longitude});

        $address_str = '';
        foreach my $key (keys %{$data->{addressBlock}}) {
            if(defined $data->{addressBlock}->{$key}){
                $address_str = $address_str . $data->{addressBlock}->{$key}. ' ';
            }
        }
        $address_str = lc ($address_str =~ s/\./. /r);
        $address_str = $address_str =~ s/,/ /r;
        $address_str = $address_str =~ s/й/и/r;
        $address_str = $address_str =~ s/ё/е/r;
        $address_str = $address_str =~ s/ъ/ь/r;

        #строка адреса для поиска дублей
        my $addr_dubles= '';
        $addr_dubles = $addr_dubles . $data->{addressBlock}->{city} . ' '       if(defined $data->{addressBlock}->{city});
        $addr_dubles = $addr_dubles . $data->{addressBlock}->{street} . ' '     if(defined $data->{addressBlock}->{street});
        $addr_dubles = $addr_dubles . $data->{addressBlock}->{house} . ' '      if(defined $data->{addressBlock}->{house});
        $addr_dubles = $addr_dubles . $data->{addressBlock}->{apartment} . ' '  if(defined $data->{addressBlock}->{apartment});

        $addr_dubles = lc ($addr_dubles =~ s/\./. /r);
        $addr_dubles = $addr_dubles =~ s/,/ /r;
        $addr_dubles = $addr_dubles =~ s/й/и/r;
        $addr_dubles = $addr_dubles =~ s/ё/е/r;
        $addr_dubles = $addr_dubles =~ s/ъ/ь/r;

        $data->{tags} = $address_str;
        my $phone_str = '';


        $phone_str = $phone_str . $data->{phoneBlock}->{main} . ' '             if(defined $data->{phoneBlock}->{main});
        $phone_str = $phone_str . $data->{phoneBlock}->{cellphone} . ' '        if(defined $data->{phoneBlock}->{cellphone});
        $phone_str = $phone_str . $data->{phoneBlock}->{office} . ' '           if(defined $data->{phoneBlock}->{office});
        $phone_str = $phone_str . $data->{phoneBlock}->{home} . ' '             if(defined $data->{phoneBlock}->{home});
        $phone_str = $phone_str . $data->{phoneBlock}->{other} . ' '            if(defined $data->{phoneBlock}->{other});
        $phone_str = $phone_str . $data->{phoneBlock}->{fax} . ' '              if(defined $data->{phoneBlock}->{fax});

        if(defined $phone_str && trim($phone_str) ne ''){
            $save_obj = {
                id => lc $data->{importId},
                address_ext => trim ($address_str),
                addr_dbl => trim ($addr_dubles),
                description => trim(lc $data->{description}),
                spec => lc $data->{mediatorCompany},
                offerTypeCode => $data->{offerTypeCode},
                typeCode => $data->{typeCode},
                changeDate => $data->{changeDate},
                addDate => $data->{addDate},
                floor => $data->{floor},
                floorsCount => $data->{floorsCount},
                ownerPrice => $data->{ownerPrice},
                roomsCount => $data->{roomsCount},
                squareTotal => $data->{squareTotal},
                squareKitchen => $data->{squareKitchen},
                squareLiving => $data->{squareLiving},
                houseType => $data->{houseType},
                roomScheme => $data->{roomScheme},
                condition => $data->{condition},
                balcony => $data->{balcony},
                bathroom => $data->{bathroom},
                newBuilding => $data->{newBuilding} ? 1 : 0,
                mortgages => $data->{mortgages} ? 1 : 0,
                roomScheme => $data->{roomScheme},
                phones => trim($phone_str),
                data => to_json($data),
                locality => lc ($data->{addressBlock}->{city} =~ s/\./. /r),
                location => $geohash,
                sourceMedia => $data->{sourceMedia}
            };
            if(trim($data->{mediatorCompany}) ne ''){
                $save_obj->{mediatorCompany} = lc trim($data->{mediatorCompany});
            }

        } else {
            die "Phone is empty";
        }

        my $res = check_doubles(%$save_obj);

        if($res == 0){
            $e->index(
                index   => 'ms_import',
                type    => 'offers',
                body    => {
                    %$save_obj
                }
            );
        }

        my $response = $e->indices->refresh(
            index => 'ms_import'
        );
    } else{
        die "Address is empty";
    }

    return $id;
}

sub check_doubles{
    my %save_obj = @_;

    my $conditions;

    try {
        # Обязательные поля
        push ( @$conditions, {term => { offerTypeCode => $save_obj{offerTypeCode}}});
        push ( @$conditions, {term => { typeCode => $save_obj{typeCode}}});
        push ( @$conditions, {term => { phones => trim($save_obj{phones})}});
        push ( @$conditions, {match_phrase_prefix => { addr_dbl => $save_obj{addr_dbl}}});
        push ( @$conditions, {match_phrase_prefix => { locality => $save_obj{locality}}});
        # Этих полей может и не быть
        push ( @$conditions, {match_phrase_prefix => { description => $save_obj{description}}})               if defined $save_obj{description};
        push ( @$conditions, {term => { floor => $save_obj{floor}}})                                          if defined $save_obj{floor};
        push ( @$conditions, {term => { roomsCount => $save_obj{roomsCount}}})                                if defined $save_obj{roomsCount};
        push ( @$conditions, {term => { squareTotal => $save_obj{squareTotal}}})                              if defined $save_obj{squareTotal};
        push ( @$conditions, {term => { floorsCount => $save_obj{floorsCount}}})                              if defined $save_obj{floorsCount};
        push ( @$conditions, {term => { squareKitchen => $save_obj{squareKitchen}}})                          if defined $save_obj{squareKitchen};
        push ( @$conditions, {term => { squareLiving => $save_obj{squareLiving}}})                            if defined $save_obj{squareLiving};

        my %full_query = (
            index => 'ms_import',
            type => 'offers',
            body  => {
                _source => ["data", "addDate", "id"],
                query => {
                    bool => {
                        must => [@$conditions]
                    }
                },
                sort => [],
                size  => 10,
                from => 0
            }
        );
        my $results = $e->search(%full_query);

        if($results->{hits}->{total} > 0){
            say "find similar offers " . $results->{hits}->{hits}->[0]->{_id};

            my $addDate = $results->{hits}->{hits}->[0]->{_source}->{addDate};
            my $id = $results->{hits}->{hits}->[0]->{_source}->{id};
            my $new_save_obj = from_json($save_obj{data});

            $new_save_obj->{importId} = $id;
            $new_save_obj->{addDate} = $addDate;
            $save_obj{data} = to_json($new_save_obj);
            $save_obj{id} = $id;
            $save_obj{addDate} = $addDate;

            my $e = Search::Elasticsearch->new(nodes => 'import.maklersoft.com:9200');
            $e->index(
                index   => 'ms_import',
                type    => 'offers',
                id     => $results->{hits}->{hits}->[0]->{_id},
                body    => \%save_obj
            );
            return 1;

        } else{
            say "no similar";
            return 0;
        }
    } catch {
        warn "caught error: $_";
        return 0;
    }

    # return $results->{hits};
}

sub put_object {
    my ($data, $mn, $loc) = @_;
    $media_name = $mn;
    $location =$loc;
    my $id;
    my @realtys = @{_find_similar(%$data)};


    if (scalar @realtys > 0) {
        foreach (@realtys) {
            $id = $_->id;   # что если похожий объект не один? какой id возвращать?
            my $o_realty = $_;
            say "Found similar realty: $id";

            my @phones = ();
            # foreach (@{$o_realty->{metadata}->owner_phones}) {
            #     push @phones, $_;
            # }

            if ($data->{add_date}) {
                $o_realty->{metadata}->last_seen_date($data->{add_date});
            } else {
                $o_realty->{metadata}->last_seen_date('now()');
            }
            $o_realty->{metadata}->change_date('now()');

            if ($o_realty->{metadata}->state_code ne 'work') {
                my @fields = qw(type_code source_media_id source_url source_media_text locality address house_num owner_price ap_scheme_id rooms_offer_count rooms_count condition_id room_scheme_id house_type_id floors_count floor square_total square_living square_kitchen square_land square_land_type);
                foreach (@fields) {
                    $o_realty->{metadata}->$_($data->{$_}) if $data->{$_};
                }
            }


            $o_realty->save(changes_only => 1);
            say "updated realty: ". $id;
        }
    } else {

        unless ($data->{add_date}) {
            my $dt = DateTime->now();
            $data->{add_date} = $dt->datetime();
        }

        $id = Rplus::Model::Result->new(metadata => to_json($data), media => $media_name, location => $location)->save;

        say "Saved new realty:". $id;
    }
}

sub _find_similar {
    my %data = @_;

    #
    # Универсальное правило
    # Совпадение: один из номеров телефонов + проверка по остальным параметрам
    #
    say 'is find';
    sleep(10);
    if (ref($data{'owner_phones'}) eq 'ARRAY' && @{$data{'owner_phones'}}) {

        my $realty = Rplus::Model::Result::Manager->get_objects(
            #select => 'id',
            query => [
                metadata => {
                    ltree_ancestor => to_json(
                        {
                            type_code=> $data{'type_code'},
                            offer_type_code=> $data{'offer_type_code'},
                            address=> $data{'address'},
                            house_num=> $data{'house_num'},
                            address=> $data{'address'},
                            \("owner_phones && '{".join(',', map { '"'.$_.'"' } @{$data{'owner_phones'}})."}'"),
                        }
                    )
                },

                #     ($data{'ap_num'} ? (OR => [ap_num => $data{'ap_num'}, ap_num => undef]) : ()),
                #     ($data{'rooms_count'} ? (OR => [rooms_count => $data{'rooms_count'}, rooms_count => undef]) : ()),
                #     ($data{'rooms_offer_count'} ? (OR => [rooms_offer_count => $data{'rooms_offer_count'}, rooms_offer_count => undef]) : ()),
                #     ($data{'floor'} ? (OR => [floor => $data{'floor'}, floor => undef]) : ()),
                #     ($data{'floors_count'} ? (OR => [floors_count => $data{'floors_count'}, floors_count => undef]) : ()),
                #     ($data{'square_total'} ? (OR => [square_total => $data{'square_total'}, square_total => undef]) : ()),
                #     ($data{'square_living'} ? (OR => [square_living => $data{'square_living'}, square_living => undef]) : ()),
                #     ($data{'square_land'} ? (OR => [square_land => $data{'square_land'}, square_land => undef]) : ()),
                # },
            media => $media_name,
            location => $location
            ],
            limit => 10,
        );

        return $realty if scalar @{$realty} > 0;
    }

    return [];
}

1;
