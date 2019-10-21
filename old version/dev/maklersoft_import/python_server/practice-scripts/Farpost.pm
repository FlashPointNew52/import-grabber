use FindBin;
use lib "$FindBin::Bin/../lib";

use DateTime::Format::Strptime;
use Mojo::Util qw(trim);

# use Rplus::Model::Result;
# use Rplus::Util::Realty qw(save_data_to_all);
use Rplus::Modern;
use Rplus::Class::Media;
# use Rplus::Class::Interface;
use Rplus::Class::UserAgent;
use Rplus::Util::2Captcha;
use URI::Escape qw(uri_escape uri_escape_utf8);

use JSON;
use Data::Dumper;

use utf8;

no warnings 'experimental';

my $media_name = 'farpost';
my $media_data;
my $parser = DateTime::Format::Strptime->new(pattern => '%Y-%m-%d %H:%M');
my $ua;
my $ip;

get_item('khv', '/khabarovsk/realty/land-rent/sdam-uchastok-5000-kv-m-45230525.html');

sub get_item {
    my ($location, $item_url) = @_;

    say 'loading ' . $media_name . ' - ' . $location . ' - ' . $item_url;
    my $data = _get_item($location, $item_url);

    say Dumper $data;

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

    # my $id_it = save_data_to_all($data, $media_name, $location);
    # say 'save new farpost '.$id_it;
}

sub _get_item {
    my ($location, $item_url) = @_;

    $media_data = Rplus::Class::Media->instance()->get_media($media_name, $location);
    # $ip = Rplus::Class::Interface->instance()->get_interface();
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

    sleep $media_data->{pause};
    parse_adv($data, $item_url);

    return $data;
}

sub parse_adv {
    my ($data, $item_url) = @_;

    my $source_url = $media_data->{site_url} . $item_url;
    $data->{source_url} = $source_url;

    my $res;
    my $counter = 0 ;
    while(1){
        $res = $ua->get_res($source_url, [
            Host => $media_data->{host},
            Referer => $media_data->{site_url}
        ]);
        if(!$res &&  $counter < 10){
            sleep($media_data->{pause});
            $counter = $counter + 1;
            # $ip = Rplus::Class::Interface->instance()->get_interface();
            # $ua = Rplus::Class::UserAgent->new($ip);
            $ua = Rplus::Class::UserAgent->new();
        } else{
            last;
        }
    }

    my $dom = $res->dom;

    # дата
    my $date_str = $dom->at('span[class="viewbull-header__actuality"]')->text;
    my $dt = _parse_date($date_str);
    $data->{add_date} = $dt->format_cldr("yyyy-MM-dd'T'HH:mm:ssZ");

    my $breadcrumbs_str = lc(trim($dom->at('div[id="breadcrumbs"]')->all_text));

    # тип предложения
    if($breadcrumbs_str =~ /посуточно/i){
      $data->{offer_type_code} = 'rent';
      $data->{rent_type} = 'short';
    }
    elsif ($breadcrumbs_str =~ /аренда/i) {
      $data->{offer_type_code} = 'rent';
    }
    elsif ($breadcrumbs_str =~ /продажа/i) {
        $data->{offer_type_code} = 'sale';
    }


    # категория недвижимости
    if ($breadcrumbs_str =~ /квартир/i) {
        $data->{category_code} = 'REZIDENTIAL';
        $data->{building_type} = 'multisection_house def';
        $data->{building_class} = 'econom def';
        $data->{type_code} = 'apartment def';
        if ($breadcrumbs_str =~ /комната/){
          $data->{type_code} = 'room def';
        }
        elsif ($breadcrumbs_str =~ /гостинк/i){
          $data->{building_class} = 'corridor_house';
        }
    }
    elsif ($breadcrumbs_str =~ /домов/i) {
        $data->{category_code} = 'REZIDENTIAL';
        $data->{building_type} = 'lowrise_house def';
        $data->{building_class} = 'single_house def';
        $data->{type_code} = 'single_house def';
    }
    elsif ($breadcrumbs_str =~ /помещений/i) {
        $data->{category_code} = 'COMMERSIAL';
        $data->{building_type} = 'gpurpose_place def';
        $data->{building_class} = 'A+';
        $data->{type_code} = 'other def';
    }
    elsif ($breadcrumbs_str =~ /дач/i || $breadcrumbs_str =~ /земельных/i) {
        $data->{category_code} = 'LAND';
        $data->{building_type} = 'agricultural_land def';
        $data->{building_class} = 'dacha ???? def';
        $data->{type_code} = 'dacha_land def';
    }

    # название объявления
    my $info_title = $dom->find('span[class="inplace"]')->first->text;
    if ($info_title =~ /ИЖС/i) {
      $data->{building_type} = 'settlements_land';
    }
    elsif ($info_title =~ /дом/i || $info_title =~ /таунхаус/i ||
    $info_title =~ /коттедж/i || $info_title =~ /дуплекс/i) {
      $data->{type_code} = _get_type_code($info_title);
      $data->{building_class} = _get_building_class($info_title);
      $data->{building_type} = _get_building_type($data->{building_class});
    }
    elsif ($data->{category_code} eq 'COMMERSIAL'){
      $data->{type_code} = _get_type_code($info_title);
      $data->{building_type} = _get_building_type($data->{type_code});
      # my $info = $dom->find('div[class="field  viewbull-field__container"]')->each( sub {
      #   if ($_->at('div[class="label"]')->text =~ /вид помещения/i ){
      #     $data->{type_code} = _get_type_code($_->at('span[data-field="flatType"]')->text);
      #     $data->{building_type} = _get_building_type($data->{type_code});
      #   }
      # });
    }

    # описание
    $data->{source_media_text} = '';

    if (my $text = $dom->at('p[data-field="text"]')) {
        $data->{source_media_text} = trim($text->text);
    }

    if (my $features = $dom->at('p[data-field="realtyFeature"]')) {
        $data->{source_media_text} .= trim($features->text);
    }

    if (my $features = $dom->at('p[data-field="realtyFurnitureAndHousehold"]')) {
        $data->{source_media_text} .= "\n" . trim($features->text);
    }

    if (my $features = $dom->at('p[data-field="realtyInfrastructure"]')) {
        $data->{source_media_text} .= "\n" . trim($features->text);
    }

    if (my $features = $dom->at('p[data-field="realtyAdditionalServices"]')) {
        $data->{source_media_text} .= "\n" . trim($features->text);
    }

    # найдем телефон
    # my @owner_phones = ();
    # if ($dom->find('div[class="contacts"]')->size > 0) {
    #
    #     sleep $media_data->{pause};
    #
    #     my $contacts = $dom->find('div[class="contacts"]')->first;
    #     my $c_ref = $contacts->find('a[class~="viewAjaxContacts"]')->first->{href};
    #
    #     my $retry = 5;
    #     while ($retry) {
    #         $retry -= 1;
    #
    #         my $c_res = $ua->get_res($media_data->{site_url} . $c_ref . '&ajax=1', [
    #             Accept => '*/*',
    #             Host => $media_data->{host},
    #             Referer => $source_url
    #         ]);
    #
    #         if ($c_res) {
    #             my $c_dom = $c_res->dom;
    #             if ($c_dom->find('form style')->size > 0) {
    #                 say 'capcha!';
    #                 my $style_with_base64 = $c_res->dom->find('form style')->first->text;
    #                 my $base64;
    #                 if($style_with_base64 =~ /background-image: url\((.{1,})\);/){
    #                     $base64 = $1;
    #                 }
    #
    #                 my $w2c = Rplus::Util::2Captcha->new(
    #                     key => '421c2b39ed6977831960e21abca5b350'
    #                 );
    #
    #                 my $captcha = $w2c->decaptcha($base64);
    #                 if(lc($captcha->{text}) =~ /[a-zA-Z1-9]/){
    #                     say 'wrong captcha';
    #                     $w2c->reportbad($captcha->{id});
    #                     sleep (10);
    #                     $captcha = $w2c->decaptcha($base64) or ($retry ? next : (die $w2c->errstr)) ;
    #                 }
    #                 if ($w2c->errstr =~/ERROR_NO_SLOT_AVAILABLE/){
    #                     sleep($media_data->{pause}*40 > 630 ? $media_data->{pause}*40 : 630);
    #                     $captcha = $w2c->decaptcha($base64) or ($retry ? next : (die $w2c->errstr));
    #                 } elsif($w2c->errstr =~/ERROR_ZERO_BALANCE/){
    #                     sleep(3600);
    #                     $captcha = $w2c->decaptcha($base64) or ($retry ? next : (die $w2c->errstr));
    #                 } elsif($w2c->errstr =~/ERROR_CAPTCHA_UNSOLVABLE/){
    #                     sleep(10);
    #                     $captcha = $w2c->decaptcha($base64) or ($retry ? next : (die $w2c->errstr));
    #                 }
    #                 say 'captcha text: ' .$captcha->{text};
    #                 $c_ref =~ s/paid=1//;
    #                 say 'c_ref '.$c_ref;
    #                 $c_res = $ua->get_res($media_data->{site_url} . $c_ref . 'ajax=1&captcha_code='.uri_escape_utf8($captcha->{text}),  [
    #                             Accept => '*/*',
    #                             Host => $media_data->{host},
    #                             Referer => $source_url
    #                 ]);
    #                 if($c_res->dom->find('form style')->size < 1){
    #                     $retry = 0;
    #                     my $phone_str = $c_res->dom->find('span[class="phone"]')->each(sub {
    #                         my $phone_str = $_->text;
    #                         $phone_str =~ s/\D//g;
    #                         if (length $phone_str > 0) {
    #                             push @owner_phones, $phone_str;
    #                         }
    #                     });
    #                 }
    #
    #             } else {
    #
    #                 my $phone_str = $c_dom->find('span[class="phone"]')->each(sub {
    #                     my $phone_str = $_->text;
    #                     $phone_str =~ s/\D//g;
    #                     if (length $phone_str > 0) {
    #                         push @owner_phones, $phone_str;
    #                     }
    #                 });
    #                 $retry = 0;
    #             }
    #         }
    #     }
    # }
    # $data->{'owner_phones'} = \@owner_phones;
    # say Dumper @owner_phones;

    # адрес, улица + номер дома или только улица
    my $addr_o = $dom->find('span[data-field="street-district"]');
    if ($addr_o->size > 0) {
        my $address_field;
        if($addr_o->size > 1){
            $address_field = $addr_o->slice(1)->first;
        } else {
            $address_field = $addr_o->first;
        }
        if($address_field->children->size > 0 && $address_field->parent->previous->text =~ /Адрес/){
            if(lc($address_field->children->first->tag) eq 'br'){
                $data->{address} = trim($address_field->text);
            } else{
                $data->{address} = trim($address_field->find('a')->first->text);
            }
        } elsif ($address_field->parent->previous->text =~ /Адрес/){
            $data->{address} = trim($address_field->text);
        }
    }

    # цена в рублях, переведем в тыс.
    my $n = $dom->find('span[itemprop="price"]');
    if ($n->size > 0) {
        my $t = trim($n->first->all_text);
        $t =~s/\s//g;
        if ($t =~ /^(\d{1,}).*?$/) {
            $data->{'owner_price'} = $1 / 1000;
        }
    }
    else{
        $n = $dom->find('span[data-field="price"]');
        if ($n->size > 0) {
            my $t = trim($n->first->all_text);
            $t =~s/\s//g;
            if ($t =~ /^(\d{1,}).*?$/) {
                $data->{'owner_price'} = $1 / 1000;
            }
        }
    }

	# вытащим фото
	$dom->find('div[class="bulletinImages"] img')->each ( sub {
		my $img_url = $_->{'data-zoom-image'};
		unless ($img_url) {
			$img_url = $_->{'src'};
		}
		push @{$data->{photo_url}}, $img_url;
	});

}

sub _parse_date {
    my $date = lc(shift);

    my $res;
    my $dt_now = DateTime->now(time_zone => $media_data->{timezone});
    my $year = $dt_now->year();
    my $mon = $dt_now->month();
    my $mday = $dt_now->mday();


    if ($date =~ /(\d{1,2}):(\d{1,2}), сегодня/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2");
        if ($res > $dt_now) {
            # substr 1 day
            #$res->subtract(days => 1);
        }
    } elsif ($date =~ /(\d{1,2}):(\d{1,2}), вчера/) {
        $res = $parser->parse_datetime("$year-$mon-$mday $1:$2");
        $res->subtract(days => 1);
        if ($res > $dt_now) {
            # substr 1 day
            #$res->subtract(days => 1);
        }
    } elsif ($date =~ /(\d{1,2}):(\d{1,2}), (\d+) (\w+)/) {
        my $a_mon = _month_num($4);
        $res = $parser->parse_datetime("$year-$a_mon-$3 $1:$2");
    } else {
        $res = $dt_now;
    }

    $res->set_time_zone($media_data->{timezone});

    return $res;
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
