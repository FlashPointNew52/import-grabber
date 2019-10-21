#!/usr/bin/env perl

use FindBin;
use lib "$FindBin::Bin/../../../";
use Rplus::Modern;

#use Rplus::Model::Media::Manager;
#use Rplus::Model::MediaImportHistory::Manager;
#use Rplus::Model::Realty::Manager;

use Rplus::Util::PhoneNum;
use Rplus::Util::Config qw(get_config);
#use Rplus::Util::Realty qw(put_object);
use Rplus::Util::Realty qw(save_data_to_all);

use Time::HiRes qw(gettimeofday);
use LWP::UserAgent;
use File::Temp qw(tempdir);
use Archive::Extract;
use Text::Trim;
use JSON;
use POSIX qw(strftime);
use Data::Dumper;
use DateTime;
use DateTime::Format::Strptime;
#my $config = Rplus::Util::Config::get_config('media');#->{media_list}->{present_archive};
#print $config;
#my $MEDIA = Rplus::Model::Media::Manager->get_objects(query => [type => 'import', code => 'present', delete_date => undef])->[0];
#exit unless $MEDIA;
#my $META = from_json($MEDIA->metadata);

import_present($ARGV[0]);

# Процедура импорта
sub import_present {
    my $arch_file = shift; # Если задан файл - то будем обрабатывать его, а не скачивать последний архив\

    my ($arch_url, $media_num);
    my $tempdir = tempdir(CLEANUP => 1);

    if (!$arch_file) {
        say "Downloading archive";

        # Выясним, какой архив актуален
        my $ua = LWP::UserAgent->new;

        #$ua->proxy(['http', 'ftp'], 'http://185.5.250.133:19888');

        #http://old.present-dv.ru/archive/?y=2014&n=39
        #http://present-dv.ru/upload/present/archive/archive/2014085.zip
        #<a class="arc-link" href="/upload/present/archive/archive/2014085.zip">Скачать</a>
        my $response = $ua->get('https://present-dv.ru/present/archive');
        die $response->status_line unless $response->is_success;
        if ($response->decoded_content =~ /<a href="(.+?(\d+)\.zip)">Скачать<\/a>/) {
            $arch_url = $1;
            $media_num = $2;
            $arch_file = "$tempdir/${media_num}.zip";

            say $arch_url;
            say $media_num;

            open(my $out_file, '<', 'for_present_archive.txt') or die "Could not open file!";
            while (my $row = <$out_file>){
                chomp $row;
                if (!($row cmp $arch_url)){
                    say $row;
                    exit;
                }
            }
            close $out_file;
            open(my $in_file, '>', 'for_present_archive.txt') or die "File not found!";
            print $in_file $arch_url;
            close $in_file;

            # Скачаем актуальный архив во временную директорию
            say "http://present-dv.ru$arch_url" =~ s/&amp;/&/r;
            $response = $ua->get("http://present-dv.ru$arch_url" =~ s/&amp;/&/r, ':content_file' => $arch_file, 'Referer' => 'http://www.present-dv.ru/');
            die $response->status_line unless $response->is_success;
        } else {
            die "Can't parse page (no archive URL)\n";
        }
    } else {
        if ($arch_file =~ /(\d+)\.zip$/) {
            $media_num = $1;
        }
    }

    $media_num = strftime("%H%M_%d%m%Y", localtime) unless $media_num;

    # say strftime "%D %H:%M:%S", localtime;
    # say 'lalala', DateTime->now()->datetime();
    # say time;


    # Распакуем архив
    say "Extracting archive '$arch_file'";
    my $ae = Archive::Extract->new(archive => $arch_file, type => 'zip');
    $ae->extract(to => $tempdir) or die $ae->error;

    # Найдем категории недвижимости, доступные для импорта
    my @INPUT_FILES;
    open my $fh, "<:encoding(cp1251)", "$tempdir/CTAPT.bat" or die "Can't open file '$tempdir/CTAPT.bat': $!\n";
    while (<$fh>) {
        trim;
        if (
            # Продажа
            /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Срочно_в_номер)\\(Продам)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Элитное_жилье)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Комнаты_малосемейки)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Комнаты)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Малосемейки)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(1_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(2_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(3_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(4_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Многокомнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Прочие_квартиры)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Дома_в_городе)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Продам)\\(Дома_в_пригороде)\.txt/ ||

                # Аренда
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Срочно_в_номер)\\(Сдам)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(Комнаты_малосемейки)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(Комнаты)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(Малосемейки)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(1_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(1_2_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(2_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(2_3_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(3_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(4_комнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(Многокомнатные)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(Прочие_квартиры)\.txt/ ||
                /^copy data\\(nedv\d+\.txt) НЕДВИЖИМОСТЬ\\(Сдам)\\(Дома_в_городе)\.txt/
        ) {
            my ($file, $t1, $t2) = ($1, $2, $3);
            say "Found category: '$t1: $t2'";

            my %data;

            if (($t1 eq 'Срочно_в_номер' && $t2 eq 'Продам') || $t1 eq 'Продам') {
                $data{'offer_type_code'} = 'sale';
            } elsif (($t1 eq 'Срочно_в_номер' && $t2 eq 'Сдам') || $t1 eq 'Сдам') {
                $data{'offer_type_code'} = 'rent';
            }

            if ($t2 eq 'Комнаты') {
                $data{'category_code'} = 'rezidential';
                $data{'type_code'} = 'room';
                $data{'building_type'} = 'multisection_house';
                $data{'building_class'} = 'economy';
            } elsif ($t2 eq 'Малосемейки') {
                $data{'category_code'} = 'rezidential';
                $data{'type_code'} = 'apartment';
                $data{'building_type'} = 'corridor_house';
                $data{'building_class'} = 'small_apartm';
            } elsif ($t2 =~ /^(\d+)_комнатные$/) {
                $data{'category_code'} = 'rezidential';
                $data{'type_code'} = 'apartment';
                $data{'rooms_count'} = $1;
                $data{'building_type'} = 'multisection_house';
                $data{'building_class'} = 'economy';
            } elsif ($t2 =~ /квартиры$/) {
                $data{'category_code'} = 'rezidential';
                $data{'type_code'} = 'apartment';
                $data{'building_type'} = 'multisection_house';
                $data{'building_class'} = 'economy';
            } elsif ($t2 =~ /^Дома/) {
                $data{'category_code'} = 'rezidential';
                $data{'type_code'} = 'house';
                $data{'building_type'} = 'lowrise_house';
                $data{'building_class'} = 'house';
            } elsif ($t2 =~ /^Участки/ || $t2 eq 'Дачи_участки') {
                $data{'category_code'} = 'land';
                $data{'type_code'} = 'dacha_land';
                $data{'building_type'} = 'agricultural_land';
            } else {
                $data{'category_code'} = 'rezidential';
                $data{'type_code'} = 'other';
            }

            push @INPUT_FILES, {file => $file, category => "$t1: $t2", data => \%data};
        }
    }
    close $fh;

    # Загрузим базу телефонов посредников
    #my %MEDIATOR_PHONES;
    #{
    #    my $mediator_iter = Import::Model::Mediator::Manager->get_objects_iterator(query => [delete_date => undef], require_objects => ['company']);
    #    while (my $x = $mediator_iter->next) {
    #        $MEDIATOR_PHONES{$x->phone_num} = {
    #            id => $x->id,
    #            name => $x->name,
    #            company => $x->company->name,
    #        };
    #    }
    #}

    my $_recognize_adv = sub {
        my ($text, $data) = @_;
        my $text_lc = lc($text);

        my %types_re = (
            room => [
                qr/дол(?:я|и)(?:\s+в\s+(\d)-комн\.)?/ => sub { return rooms_count => $_[0]; },
                qr/(?:комн\.?|секция)/ => sub {},
            ],
            apartment => [
                qr/малосем\.?/ => sub { return type_code => 'small_apartm'; },
                qr/(\d)\s*\-\s*комн\.?/ => sub { return rooms_count => $_[0]; },
            ],
            house => [
                qr/коттедж/ => sub { return building_class => 'cottage'; },
                qr/таунхаус/ => sub { return building_class => 'townhouse'; },
                qr/дом/ => sub {},
            ],
            land => [
                qr/(?:уч\-к|участок)/ => sub {},
                qr/дача/ => sub { return type_code => 'dacha_land'; },
                qr/(\d+)\s+(?:сот\.?|с\/с)/ => sub { return square_land => $_[0], square_land_type => 'ar'; },
                qr/(\d(?:,\d+)?)\s+га/ => sub { return square_land => ($_[0] =~ s/,/./r), square_land_type => 'ha'; },
            ],
            other => [
                qr/(\d)\s*\-\s*комн\.?/ => sub { return type_code => 'apartment', rooms_count => $_[0]; },
                qr/коттедж/ => sub { return type_code => 'cottage'; },
                qr/малосем\.?/ => sub { return type_code => 'room'; },
                qr/комн\.?/ => sub { return type_code => 'room'; },
            ],
        );

        my ($addr, $body);
        my $cc = $data->{'category_code'};
        if (exists $types_re{$cc}) {
            for (my $i = 0; $i < @{$types_re{$cc}}; $i++) {
                my ($re, $cb) = ($types_re{$cc}->[$i], $types_re{$cc}->[++$i]);
                if (my @m = ($text_lc =~ /^(.*?)$re(.+)$/)) {
                    my %x = $cb->(@m[1..($#m-1)]);
                    @{$data}{keys %x} = values %x;
                    ($addr, $body) = ($m[0], $m[$#m]);
                    last;
                }
            }
        }

        if (!$body) {
            if ($text_lc =~ /^(.+?)\(([^()]+)\)([^()]+)$/) {
                $addr = $1;
                $body = $2.$3;
                if (scalar(grep { $_ && $_ ne '.' } split /[ ,()]/, $addr) > 5) {
                    $addr = undef;
                    $body = $text_lc;
                }
            } else {
                $body = $text_lc;
            }
        }

        $addr = trim $addr;
        $body = trim $body;
        return unless $body;

        # Распознавание цены и контактных телефонов
        {
            my $price;
            {
                my $price_ml = ($2 =~ s/,/./r) if $body =~ s/((\d+(,\d+)?)\s*млн\.)//;
                my $price_th = $2 if $body =~ s/((\d+)\s*тыс\.)//;
                $price = ($price_ml || 0)*1000 + ($price_th || 0);
            }
            $data->{'price'} = $price if $price;

            my @owner_phones;
            for my $x (split /[ .,]/, $body) {
                if ($x =~ /^\s*([\d-]{6,})\s*$/) {
                    if (my $phone_num = Rplus::Util::PhoneNum::refine_phonenum($1)) {
                        if (length $phone_num == 11){
                            substr($phone_num, 0, 1) = '7';
                        }
                        push @owner_phones, $phone_num;
                    }
                    $body =~ s/$x//;
                }
                if ($x =~ /^\s*8\(\d{3,4}\)([\d-]{6,})\s*$/) {

                    if (my $phone_num = Rplus::Util::PhoneNum::refine_phonenum($1)) {
                        if (length $phone_num == 11){
                            substr($phone_num, 0, 1) = '7';
                        }
                        push @owner_phones, $phone_num;
                    }
                    $body =~ s/$x//;
                }
            }
            $data->{'phones_import'} = \@owner_phones;
        }

        # Пропустим объявления без номеров телефонов
        # Пропустим объявления посредников
        # Возможно не следует это делать в этом месте, но зато сэкономим ресурсы
        return unless @{$data->{'phones_import'}};
        #for (@{$data->{'owner_phones'}}) {
        #    return if exists $MEDIATOR_PHONES{$_};
        #}

        if ($addr) {
            $data->{'address'} = $addr;
        }

        # Площадь
        if ($body =~ s/(\d+(?:,\d+)?)\/(\d+(?:,\d+)?)\/(\d+(?:,\d+)?)//) {
            my ($total, $living, $kitchen) = map { s/,/./r } ($1, $2, $3);
            if ($total > $living && $total > $kitchen) {
                if ($total > 0) {
                    $data->{'square_total'} = $total;
                }
                if ($living > 0) {
                    $data->{'square_living'} = $living;
                }
                if ($kitchen) {
                    $data->{'square_kitchen'} = $kitchen;
                }
            }
        } elsif ($body =~ s/(\d+(?:,\d+)?)\s+кв\.\s*м//) {
            $data->{'square_total'} = $1 =~ s/,/./r;
        }
        if ($body =~ s/(\d+)\s+сот\.?//) {
            $data->{'square_land'} = $1;
            $data->{'square_land_type'} = 'ar';
        }

        # Разделим остальную часть обявления на части и попытаемся вычленить полезную информацию
        my @bp = grep { $_ && length($_) > 1 } trim(split /[,()]/, $body);
        for my $el (@bp) {
            # Этаж/этажность
            if ($el =~ /^(\d{1,2})\/(\d{1,2})$/) {
                if ($2 > $1) {
                    $data->{'floor'} = $1;
                    $data->{'floors_count'} = $2;
                }
                next;
            }

            # for my $k (keys %{$META->{'params'}->{'dict'}}) {
            #     my %dict = %{$META->{'params'}->{'dict'}->{$k}};
            #     my $field = delete $dict{'__field__'};
            #     for my $re (keys %dict) {
            #         if ($el =~ /$re/i) {
            #             $data->{$field} = $dict{$re};
            #             last;
            #         }
            #     }
            # }
        }

        # Этаж#2
        if (!$data->{'floor'} && $body =~ /(\d{1,2})\s+эт\.?/) {
            $data->{'floor'} = $1;
        }

        return $data;
    };

    my %REALTY = (list => [], by_phone_num => {});

    # Обработка файлов объявлений
    for my $x (@INPUT_FILES) {
        say "Processing category: '".$x->{'category'}."'";

        my $file = "$tempdir/data/".$x->{'file'};
        open my $fl, "<:encoding(cp1251)", $file or do { say "Can't open file '$file': $!" if 0; next; };
        while (<$fl>) {
            trim;
            next unless $_;

            # Пропустим уже обработанные объявления
            #next if Import::Model::MediaImportHistory::Manager->get_objects_count(query => [media_id => $MEDIA->id, media_num => $media_num, media_text => $_]);
            my $id = gettimeofday * 100000;
            my $data = {
                id => $id,
                source_media => 'present_archive',
                description => $_,
                locality => 'г. Хабаровск',
                # new_building => true,
                %{$x->{'data'}},


            };

            if ($_recognize_adv->($_, $data)) { # Функция может пропускать объявления посредников и ничего не возвращять
                #next unless @{$data->{'owner_phones'}};

                my $id;

                eval {
                    #my $realty = Rplus::Model::Realty->new((map { $_ => $data->{$_} } grep { $_ ne 'category_code' } keys %$data), state_code => 'raw');
                    #$realty->save;

                   # say Dumper $data;
                    my $media_name = 'present_archive';
                    my $location = 'khv';
                    # say Dumper $data;
                    my $id_it = save_data_to_all($data, $media_name, $location);
                    say 'save new present_archive ' . $id_it;

                    # $id = put_object($data, get_config());
                    # if ($id) {
                    #     say "Saved new realty: $id";
                    # } else {
                    #     say 'skipped';
                    # }
                    1;
                } or do {
                    say $@;
                };

            }
        }
    }
}
