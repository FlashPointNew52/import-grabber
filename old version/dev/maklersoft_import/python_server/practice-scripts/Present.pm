use FindBin;
use lib "$FindBin::Bin/../lib";

# use Rplus::Model::Result;
# use Rplus::Util::Realty qw(save_data_to_all);
use Rplus::Modern;
use Rplus::Class::Media;
# use Rplus::Class::Interface;
use Rplus::Class::UserAgent;

use JSON;
use Data::Dumper;
use DateTime::Format::Strptime;
use Mojo::Util qw(trim);

no warnings 'experimental';


my $media_name = 'present_site';
my $media_data;
my $parser = DateTime::Format::Strptime->new(pattern => '%Y-%m-%d %H:%M:%S');
my $ua;

get_item('khv', '/present/notice/view/3966448');

sub get_item {
    my ($location, $item_url) = @_;

    say ('loading ' . $media_name . ' - ' . $location . ' - ' . $item_url );
    my $data = _get_item($location, $item_url);
    say (Dumper $data);

    # say $data->{source_media}, ' - наименование источника';
    # say $data->{source_url}, ' - адрес источника';
    # say $data->{add_date}, ' - дата добавления';
    say $data->{offer_type_code}, ' - тип предложения';
    say $data->{category_code}, ' - категория недвижимости';
    say $data->{building_type}, ' - тип дома';
    say $data->{building_class}, ' - тип недвижимости';
    say $data->{type_code}, ' - тип объекта';
    say $data->{address}, ' - адрес целиком';
    # say $data->{owner_phones}, ' - массив телефонов';
    # say $data->{phones_import}, ' - телефоны объекта импорта';
}

sub _get_item {
    my ($location, $item_url) = @_;

    $media_data = Rplus::Class::Media->instance()->get_media($media_name, $location);;
    $ua = Rplus::Class::UserAgent->new();

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
    my $counter = 0 ;
    while(1){
        $ua = Rplus::Class::UserAgent->new();
        $res = $ua->get_res($source_url, [
            Host => $media_data->{host},
            Referer => $media_data->{site_url}
        ]);
        if(!$res &&  $counter < 10){
            sleep($media_data->{pause});
            $counter = $counter + 1;
        } else{
            last;
        }
    }

    my $dom = $res->dom;

    # дата
    my $data_str = trim($dom->find('div[class="text-muted"]')->first->find('div[class~="items-bar__group items-bar__group--double-indent"]')->first->text);

    if ($data_str =~ /^Размещено:\s+(.+)$/i) {
        my $dt = _parse_date($data_str);

        $data->{add_date} = $dt->format_cldr("yyyy-MM-dd'T'HH:mm:ssZ");
    }

    my $breadcrumbs_str = trim($dom->at('div[class="breadcrumbs"]')->all_text);
    say $breadcrumbs_str , "\n";


    # тип предложения
    if ($breadcrumbs_str =~ /сдам/i) {
        $data->{offer_type_code} = 'rent';
    }
    elsif ($breadcrumbs_str =~ /продам/i) {
        $data->{offer_type_code} = 'sale';
    }


    # категория недвижимости
    if ($breadcrumbs_str =~ /жилая/i) {
        $data->{category_code} = 'REZIDENTIAL';
        $data->{building_type} = 'multisection_house';
        $data->{building_class} = 'econom';
        $data->{type_code} = 'apartment';
    }
    elsif ($breadcrumbs_str =~ /коммерческая/i) {
        $data->{category_code} = 'COMMERSIAL';
        $data->{building_type} = 'gpurpose_place';
        $data->{building_class} = 'A+';
        $data->{type_code} = 'other';
    }
    elsif ($breadcrumbs_str =~ /участки и дачи/i) {
        $data->{category_code} = 'LAND';
        $data->{building_type} = 'agricultural_land';
        $data->{building_class} = 'dacha ????';
        $data->{type_code} = 'dacha_land';
    }

    if ($breadcrumbs_str =~ /посуточно/i) {
        $data->{rent_type} = 'short';
    }
    elsif ($breadcrumbs_str =~ /комнаты/i) {
        $data->{type_code} = 'room';
    }
    elsif ($breadcrumbs_str =~ /квартиры/i) {
        $data->{type_code} = 'apartment';
    }
    elsif ($breadcrumbs_str =~ /малосемейк/i) {
        $data->{building_type} = 'corridor_house';
    }
    elsif ($breadcrumbs_str =~ /дома/i) {
        $data->{building_type} = 'lowrise_house';
    }

    #информация из полей объявления
    $dom->find('div[class="notice-card__field word-break"]')->each (sub {

      #парсинг адреса
      if ($_->at('strong')->text =~ /улица/i) {
          $data->{address} = $_->at('span')->text;
      }
      elsif ($_->at('strong')->text =~ /местоположение/i) {
          $data->{address} = $_->at('span')->text;
      }

      #парсинг количества комнат
      if ($_->at('strong')->text =~ /количество комнат/i) {
        if (_get_type_code($_->at('span')->text) && $data->{type_code} ne 'apartment'){
          $data->{type_code} = _get_type_code($_->at('span')->text);
        }
      }

      #парсинг объекта аренды
      elsif ($_->at('strong')->text =~ /объект аренды/i) {
        if (_get_type_code($_->at('span')->text)){
          $data->{type_code} = _get_type_code($_->at('span')->text);
          if ($_->at('span')->text =~ /общежит/i){
            $data->{building_class} = 'dormitory';
          }
        }
      }
      #парсинг объекта продажи
      elsif ($_->at('strong')->text =~ /объект продажи/i) {
        if (_get_type_code($_->at('span')->text)){
          $data->{type_code} = _get_type_code($_->at('span')->text);
          $data->{building_class} = _get_building_class($_->at('span')->text);
          if ($_->at('span')->text =~ /общежит/i){
            $data->{building_class} = 'dormitory';
          }
        }
      }

      #парсинг планировка
      elsif ($_->at('strong')->text =~ /планировка/i) {
          $data->{building_class} = _get_building_class($_->at('span')->text);
          $data->{building_type} = _get_building_type($data->{building_class});
      }

      #парсинг вида объекта
      elsif ($_->at('strong')->text =~ /вид объекта/i) {
        if (_get_type_code($_->at('span')->text)){
          $data->{type_code} = _get_type_code($_->at('span')->text);
          $data->{building_type} = _get_building_type($data->{type_code});
        }
      }

      #парсинг описания объявления
      elsif ($_->at('strong')->text =~ /дополнительно/i) {
          my $media_text = $_->at('span')->text;
          $data->{source_media_text} = $media_text;
      }

      #проверка исключений
      if (exists $data->{source_media_text}) {
        if ($data->{source_media_text} =~ /ИЖС/i && $data->{category_code} eq 'LAND') {
          $data->{building_type} = 'settlements_land';
        }
      }
    });

    # парсим телефон
    my $phone_text=$dom->find('div[class="notice-card__contacts media"] div[class="media-body"]')->first;
    my @phone;
    my @phones;
    if($phone_text){
      $phone_text->find('a')->each( sub{
        push @phone, $_->text;
        push @phones, $_->text;
      });
    }
    $data->{owner_phones}= \@phone;
    $data->{phones_import}= \@phones;

    #извлечение цены
    if($dom->find('div[class="notice-card__financial-fields media"]')->size > 0) {
        my $price = $dom->find('div[class="notice-card__financial-fields media"] div[class="media-body"] ')->first->all_text;
        $price =~ s/\D//g;
        $data->{owner_price} = $price / 1000 if $price > 0;
    }

    # парсинг url-адресов фотографий
    my $do = $dom->find('div[class="light-box"]')->first;
    if($do){
	   $do->find('a')->each ( sub {
           my $img_url = $media_data->{site_url} . $_->{'href'};
	       push @{$data->{photo_url}}, $img_url;
	   });
    }

    # парсинг адреса
    unless ($data->{address}) {
        if($dom->at('div[class="content column2right-1"]')){
            my $title = $dom->at('div[class="content column2right-1"]')->at('h1')->text;
            $data->{address} = $title;
        }
    }

    return $data;
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

sub _parse_date {
    my $date = lc(shift);
    my $res;
    my $dt_now = DateTime->now();
    my $year = $dt_now->year();
    my $mon = $dt_now->month();
    my $mday = $dt_now->mday();

    if ($date =~ /сегодня в (\d{1,2}):(\d{1,2})/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2:00");
        if ($res > $dt_now) {
            # substr 1 day
            #$res->subtract(days => 1);
        }
    } elsif ($date =~ /(\d{1,2}):(\d{1,2})/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2:00");
        # substr 1 day
        $res->subtract(days => 1);
    } elsif ($date =~ /(\d+) (\w+)/) {
        my $a_mon = _month_num($2);
        my $a_year = $year;
        if ($a_mon > $mon) { $a_year -= 1; }
        $res = $parser->parse_datetime("$a_year-$a_mon-$1 12:00:00");
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

1;
