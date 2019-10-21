use FindBin;
use lib "$FindBin::Bin/../lib";

use Search::Elasticsearch;
use JSON;
use Data::Dumper;
use utf8;

use DateTime::Format::Strptime;
use Mojo::Util qw(trim);

#use Rplus::Model::Result;
#use Rplus::Util::Realty qw(save_data_to_all);
use Mojo::Log;
use Rplus::Modern;
use Rplus::Class::Media;
#use Rplus::Class::Interface;
use Rplus::Class::UserAgent;

use JSON;
use Data::Dumper;

no warnings 'experimental';


my $media_name = 'avito';
my $media_data;
my $parser = DateTime::Format::Strptime->new(pattern => '%Y-%m-%d %H:%M');
my $ua;

get_item('khv', '/habarovsk/kvartiry/2-k_kvartira_54_m_45_et._1256208037');

# update();

sub update {
    for(my $i=1; $i<=1200; $i++){
        my %full_query = (
            index => 'rplus-import',
            type => 'offer',
            body  => {
                query => {
                    bool => {
                        must => []
                    }
                },
                size  => 100,
                from => 100 * $i
            }
        );
        my $e = Search::Elasticsearch->new(nodes  => 'import.rplusmgmt.com:9200');
        my $results = $e->search(%full_query);
        #say  $results->{hits}->{hits};
        foreach my $val (@{$results->{hits}->{hits}}){
            foreach my $ph(@{$val->{_source}->{owner_phones}}){
                $ph =~ s/\+|\(|\)|-|\s//g;
            }

            my $rez = $e->index(
                index   => 'rplus-import',
                 type    => 'offer',
                 id => $val->{_id},
                 body    => {
                     %{$val->{_source}}
                 }
             );
             say  $rez;
        }
    }
}

sub get_item {
    my ($location, $item_url) = @_;

    # say 'loading ' . $media_name . ' - ' . $location . ' - ' . $item_url;
    my $data = _get_item($location, $item_url);

    say Dumper $data;

    say $data->{offer_type_code}, ' - тип предложения (offer_type_code)';
    say $data->{category_code}, ' - категория недвижимости (category_code)';
    say $data->{building_type}, ' - тип дома (building_type)';
    say $data->{building_class}, ' - тип недвижимости (building_class)';
    say $data->{type_code}, ' - тип объекта (type_code)';
    say $data->{address}, ' - адрес целиком (address)';

    # my $id_it = save_data_to_all($data, $media_name, $location);
    # say 'save new avito '.$id_it;
}

sub _get_item {
    my ($location, $item_url) = @_;

    $media_data = Rplus::Class::Media->instance()->get_media('avito', $location);

    my $data = {
        source_media => $media_name, # наименование источника
        source_url => $media_data->{site_url} . $item_url, # адрес источника
        add_date => '', # дата добавления
        offer_type_code => '', # тип предложения
        category_code => '', # категория недвижимости
        building_type => '', # тип дома
        building_class => '', # тип недвижимости (планировка)
        type_code => '', # тип объекта
        address => '', # адрес целиком
        owner_phones => '', # массив телефонов
        phones_import => '', # телефоны объекта импорта

    };

    parse_adv($data, $item_url);

    return $data;
}

sub parse_adv {
    my ($data, $item_url) = @_;

    my $source_url = $media_data->{site_url} . $item_url;

    my $res;
    my $counter = 0;
    while(1){
        $ua = Rplus::Class::UserAgent->new();
        $res = $ua->get_res($source_url, [
            Host => $media_data->{host},
            Referer => $media_data->{site_url}
        ]);
        if(!$res && $counter < 10){
            sleep(5);
            $counter = $counter + 1;
        } else{
            last;
        }
    }

    my $dom = $res->dom;

    # время размещения
    my $id_data_str = '';
    if( $dom->at('div[class="title-info-metadata"]')){
        $id_data_str = $dom->at('div[class="title-info-metadata"]')->find('div[class="title-info-metadata-item"]')->first->text;
    }
    my $item_id;
    if ($id_data_str =~ /№ (\d+),/i) {
        $item_id = $1 * 1;
    }
    if ($id_data_str =~ /размещено (.+)/i) {
        my $dt = _parse_date($1);
        $data->{add_date} = $dt->format_cldr("yyyy-MM-dd'T'HH:mm:ssZ");
    }

    my $breadcrumbs = lc($dom->at('div[class~="breadcrumbs"]')->all_text);
    say $breadcrumbs;

    # тип предложения
    if ($breadcrumbs =~ /продам/) {
      $data->{offer_type_code} = 'sale';
    }
    elsif ($breadcrumbs =~ /сдам/) {
        $data->{offer_type_code} = 'rent';
        if ($breadcrumbs =~ /посуточно/) {
            $data->{rent_type} = 'short';
        }
    }

    # категория недвижимости
    if ($breadcrumbs =~ /квартиры/ || $breadcrumbs =~ /комнаты/ || $breadcrumbs =~ /коттеджи/) {
      $data->{category_code} = 'REZIDENTIAL';
      $data->{building_type} = 'multisection_house';
      $data->{building_class} = 'econom';
      $data->{type_code} = 'apartment';
      if ($breadcrumbs =~ /комнаты/){
        $data->{type_code} = 'room';
      }
    }
    elsif ($breadcrumbs =~ /земельные/i){
      $data->{category_code} = 'LAND';
      $data->{building_type} = 'agricultural_land';
      $data->{building_class} = 'dacha';
      $data->{type_code} = 'dacha_land';
      if ($breadcrumbs =~ /ИЖС/i){
        $data->{building_class} = 'dacha ????';
        $data->{building_type} = 'settlements_land';
      }

    }
    elsif ($breadcrumbs =~ /коммерческая/i){
      $data->{category_code} = 'COMMERSIAL';

      $data->{type_code} = _get_type_code($breadcrumbs);
      $data->{building_class} = 'A+';
      $data->{building_type} = _get_building_type($data->{type_code})
    }

    # тип объекта
    if ($dom->at('li[class~="item-params-list-item"]')) {
      my $info = $dom->at('li[class~="item-params-list-item"]')->all_text;
      if ($info =~ /вид объекта/i) {
        $data->{type_code} = _get_type_code($info);
        $data->{building_class} = _get_building_class($info);
        $data->{building_type} = _get_building_type($data->{building_class});
        if ($info =~ /дач/i) {
          $data->{category_code} = 'LAND';
        }
      }
    }

    # описание
    if ($dom->find('div[class="item-description"]')) {
      my $info_description = '';
      if ($dom->find('div[class="item-description-text"]')->first) {
        $info_description = $dom->find('div[class="item-description-text"]')->first->all_text;
      }
      elsif ($dom->find('div[class="item-description-html"]')->first){
        $info_description = $dom->find('div[class="item-description-html"]')->first->all_text;
      }
      $data->{source_media_text} = $info_description;
    }

    if (exists $data->{source_media_text}) {
      $data->{building_class} = _get_building_class($data->{source_media_text});
      $data->{building_type} = _get_building_type($data->{building_class});
      # if ($data->{source_media_text} =~ /доля/i || $data->{source_media_text} =~ /доли/i) {
      #   $data->{type_code} = 'share';
      # }
    }

    # цена в рублях, переведем в тыс.
    if ($dom->at('div[class~="item-price"]')) {
        my $price = $dom->at('span[class~="js-item-price"]')->text;
        $price =~s/\s//g;
        if ($price =~ /^(\d{1,}).*?$/) {
            $data->{owner_price} = $1 / 1000;
        }
    }

    # адрес
    if ($dom->find('div[class="seller-info-prop"]')->first) {
      my $address_info = $dom->find('div[class="seller-info-prop"]')->first;
      $data->{address} = $address_info->find('div[class="seller-info-value"]')->first->text;
    }
    else {
      my $address_info = $dom->find('span[class="item-map-address"]')->first;
      $data->{address} = $address_info->find('span[itemprop="streetAddress"]')->first->text;
    }

    # номера телефонов
    my @owner_phones;
    my $item_phone = '';
    my $pkey = '';
    $dom->find('script')->each(sub{
        if ($_->all_text =~ /item.phone = '(.+?)'/) {
            $item_phone = $1;
        }
    });

    $pkey = _phone_demixer($item_id * 1, $item_phone);

    sleep $media_data->{pause};

    my $m_url = 'https://m.avito.ru' . $item_url;

    $ua->get_res($m_url, [
        Host => 'm.avito.ru',
        Referer => $media_data->{site_url},
    ]);

    my $mr = $ua->get_res($m_url . '/phone/' . $pkey . '?async', [
        Host => 'm.avito.ru',
        Referer => $m_url,
        Accept => 'application/json, text/javascript, */*; q=0.01'
    ]);
    if ($mr && $mr->json) {
         my $phone_str = $mr->json->{phone};
        for my $x (split /[.,;:]/, $phone_str) {
            push @owner_phones, $x;
        }
    }
    $data->{owner_phones} = \@owner_phones;

    # вытащим фото
    my @photos;
    $dom->find('meta[property="og:image"]')->each (sub {
        unless ($_->{content} =~ /logo/) {
            my $img_url = $_->{content};
            push @photos, $img_url;
        }
    });
    $data->{photo_url} = \@photos;

    return $data;
}

sub _phone_demixer {
    my ($id, $key) = @_;

    my @parts = $key =~ /[0-9a-f]+/g;

    my $mixed = join '', $id % 2 == 0 ? reverse @parts : @parts;
    my $s = length $mixed;
    my $r = '';
    my $k;

    for($k = 0; $k < $s; ++ $k) {
        if( $k % 3 == 0 ) {
            $r .= substr $mixed, $k, 1;
        }
    }

    return $r;
}

sub _parse_date {
    my $date = lc(shift);

    my $res;
    my $dt_now = DateTime->now();
    my $year = $dt_now->year();
    my $mon = $dt_now->month();
    my $mday = $dt_now->mday();

    if ($date =~ /сегодня в (\d{1,2}):(\d{1,2})/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2");
        if ($res > $dt_now) {
            # substr 1 day
            #$res->subtract(days => 1);
        }
    } elsif ($date =~ /вчера в (\d{1,2}):(\d{1,2})/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2");
        # substr 1 day
        $res->subtract(days => 1);
    } elsif ($date =~ /(\d+) (\w+) в (\d{1,2}):(\d{1,2})/) {
        my $a_mon = _month_num($2);
        my $a_year = $year;
        if ($a_mon > $mon) { $a_year -= 1; }
        $res = $parser->parse_datetime("$a_year-$a_mon-$1 $3:$4");
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

sub _get_type_code {

  my $breadcrumbs_str = lc(shift);

  if ($breadcrumbs_str =~ /дол/i) {
      return 'share';
  }
  elsif ($breadcrumbs_str =~ /комнат/i) {
      return 'room';
  }
  elsif ($breadcrumbs_str =~ /квартир/i) {
      return 'apartment';
  }
  elsif ($breadcrumbs_str =~ /дом/i) {
      return 'house';
  }
  elsif ($breadcrumbs_str =~ /коттедж/i) {
      return 'cottage';
  }
  elsif ($breadcrumbs_str =~ /дач/i) {
      return 'dacha_land';
  }
  elsif ($breadcrumbs_str =~ /таунхаус/i) {
      return 'townhouse';
  }
  elsif ($breadcrumbs_str =~ /дуплекс/i) {
      return 'duplex';
  }

  elsif ($breadcrumbs_str =~ /участок/i) {
      return 'dacha_land';
  }

  elsif ($breadcrumbs_str =~ /отель/i) {
      return 'hotel';
  }
  elsif ($breadcrumbs_str =~ /гостинниц/i) {
      return 'hotel';
  }
  elsif ($breadcrumbs_str =~ /ресторан/i) {
      return 'restaurant';
  }
  elsif ($breadcrumbs_str =~ /кафе/i) {
      return 'cafe';
  }
  elsif ($breadcrumbs_str =~ /спорт/i) {
      return 'sport_building';
  }

  elsif ($breadcrumbs_str =~ /магазин/i) {
      return 'shop';
  }
  elsif ($breadcrumbs_str =~ /торгов/i && $breadcrumbs_str =~ /центр/i) {
      return 'shops_center';
  }
  elsif ($breadcrumbs_str =~ /торгово-развлекательный/i) {
      return 'shop_entertainment';
  }

  elsif ($breadcrumbs_str =~ /кабинет/i) {
      return 'cabinet';
  }
  elsif ($breadcrumbs_str =~ /офисное помещение/i) {
      return 'office_space';
  }
  elsif ($breadcrumbs_str =~ /офисное здание/i) {
      return 'office_building';
  }
  elsif ($breadcrumbs_str =~ /бизнес/i) {
      return 'business_center';
  }

  elsif ($breadcrumbs_str =~ /производст/i) {
      return 'manufacture_building';
  }
  elsif ($breadcrumbs_str =~ /склад/i) {
      return 'warehouse_space';
  }
  elsif ($breadcrumbs_str =~ /промышленное/i) {
      return 'industrial_enterprice';
  }
  else {
    return 'other';
  }
}

sub _get_building_type {
  my $breadcrumbs_str = lc(shift);

  if ($breadcrumbs_str eq 'individual'){
    return 'galary_house'
  }
  elsif ($breadcrumbs_str eq 'brezhnev' || $breadcrumbs_str eq 'improved' || $breadcrumbs_str eq 'econom' ||
  $breadcrumbs_str eq 'business' || $breadcrumbs_str eq 'elite' || $breadcrumbs_str eq 'khrushchev' ||
  $breadcrumbs_str eq 'stalin' || $breadcrumbs_str eq 'old_fund'){
    return 'multisection_house';
  }
  elsif ($breadcrumbs_str eq 'brezhnev' || $breadcrumbs_str eq 'improved' || $breadcrumbs_str eq 'econom' ||
  $breadcrumbs_str eq 'business' || $breadcrumbs_str eq 'elite'){
    return 'singlesection_house';
  }
  elsif ($breadcrumbs_str eq 'gostinka' || $breadcrumbs_str eq 'dormitory' || $breadcrumbs_str eq 'small_apartm'){
    return 'corridor_house';
  }
  elsif ($breadcrumbs_str eq 'single_house' || $breadcrumbs_str eq 'cottage' || $breadcrumbs_str eq 'townhouse' ||
   $breadcrumbs_str eq 'duplex'){
    return 'lowrise_house';
  }

  if ($breadcrumbs_str eq 'manufacture_building' || $breadcrumbs_str eq 'warehouse_space' ||
  $breadcrumbs_str eq 'industrial_enterprice'){
    return 'production_place';
  }
  elsif ($breadcrumbs_str eq 'cabinet' || $breadcrumbs_str eq 'office_space' || $breadcrumbs_str eq 'office_building' ||
  $breadcrumbs_str eq 'business_center'){
    return 'office';
  }
  elsif ($breadcrumbs_str eq 'shop_building' || $breadcrumbs_str eq 'shop' || $breadcrumbs_str eq 'shops_center' ||
  $breadcrumbs_str eq 'shop_entertainment'){
    return 'market_place';
  }
  elsif ($breadcrumbs_str eq 'hotel' || $breadcrumbs_str eq 'restaurant' || $breadcrumbs_str eq 'cafe' ||
  $breadcrumbs_str eq 'sport_building' || $breadcrumbs_str eq 'other'){
    return 'gpurpose_place';
  }
  if ($breadcrumbs_str eq 'dacha'){
    return 'agricultural_land';
  }
}

sub _get_building_class{
  my $text = lc(shift);

  given ($text) {
      when (/улучшен/i) {
        return 'improved';
      }
      when (/брежневка/i) {
          return 'brezhnev';
      }
      when (/хрущев/i) {
          return 'khrushchev';
      }
      when (/сталин/i) {
          return 'stalin';
      }
      when (/новая/i) {
          return 'improved';
      }
      when (/элит/i) {
        return 'elite';
      }
      when (/бизнес/i) {
        return 'business'
      }
      when (/экон/i) {
        return 'econom';
      }
      when (/улучшен/i) {
        return 'improved';
      }
      when (/фонд/i) {
          return 'old_fund';
      }
      when (/общежит/i) {
          return 'dormitory';
      }
      when (/гостинк/i) {
          return 'gostinka';
      }
      when (/индивидуал/i) {
          return 'individual';
      }
      when (/дом/i) {
          return 'single_house';
      }
      when (/коттедж/i) {
          return 'cottage';
      }
      when (/дач/i) {
          return 'dacha';
      }
      when (/таунхаус/i) {
          return 'townhouse';
      }
      when (/дуплекс/i) {
          return 'duplex';
      }
      default {
        return 'econom';
      }
  }
}

1;