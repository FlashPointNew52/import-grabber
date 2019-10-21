package RplusImport2::Controller::API::Offer;
use Mojo::Base 'Mojolicious::Controller';
use utf8;
use Rplus::DB;
use Rplus::Model::Result::Manager;
use Search::Elasticsearch;
use Data::Dumper;
use Mojo::Util qw(trim);
use JSON::Parse 'parse_json';
use JSON;

# Search:

my %source_media = (
        "(авито)|(avito)" => "avito",
        "(из рук в руки)|(ирр)|(irr)" => "irr",
        "(презент архив)|(архив)" => "present_site",
        "(презент сайт)|(презент)|(present)" => "present_site",
        "(фарпост)|(farpost)" => "farpost",
        "(циан)|(cian)"  => "cian"
);

sub search {
    my $self = shift;

    my $query = $self->param('query') || '';
    my $filter = $self->param('filter') || undef;
    my $rangeFilter = $self->param('rangeFilters') || undef;
    my $page = $self->param('page') || 0;
    my $per_page = $self->param('per_page') || 50;
    my $search_area = $self->param('search_area') || 0;
    my $agent = $self->param('agent') || '';
    my $sort = $self->param('sort') || '';

    my %full_query = (
        index => 'ms_import',
        type => 'offers',
        body  => {
            _source => "data",
            query => {
                bool => {
                    must => []
                }
            },
            sort => [],
            size  => $per_page,
            from => $per_page * $page
        }
    );

    if(defined $filter) {
        $filter = parse_json($filter);
        foreach my $fltr (keys %{$filter}) {
            if($filter->{$fltr} ne 'all'){
                if ($fltr eq "changeDate" || $fltr eq "addDate") {
                    my $dt = DateTime->now()->set(hour => 0, minute => 0, second => 0, nanosecond => 0);
                    $dt->subtract(days => $filter->{$fltr});
                    push(
                        @{$full_query{body}{query}{bool}{must}},
                        {
                            range => {
                                $fltr => {
                                    gte => $dt->epoch()
                                }
                            }
                        }
                    );
                } else {
                    push( @{$full_query{body}{query}{bool}{must}},
                        {
                            term => { $fltr => $filter->{$fltr} }

                        }
                    );
                }
            }
        }
    }

    if(defined $rangeFilter){
        $rangeFilter = parse_json ($rangeFilter);
        foreach my $fltr (@{$rangeFilter}) {
            if(defined $fltr->{arrayVal} && scalar $fltr->{arrayVal} > 0){
                my $values;
                if($fltr->{fieldName} eq "phones"){
                    my $content_phones = '';
                    foreach my $val (@{$fltr->{arrayVal}}) {
                        $content_phones = $content_phones . $val . '|';
                    }
                    $content_phones =~ s/\|$//g;
                    if(defined $values){
                        push(
                            @{$full_query{body}{query}{bool}{must}},
                            {
                                "bool" => {
                                    "minimum_should_match" => 1,
                                    "should" => $values,
                                }
                            }
                        );
                    }
                    push(@{$full_query{body}{query}{bool}{must}},
                            { "regexp" => {"phones" => $content_phones } }
                    );


                } elsif($fltr->{fieldName} eq "mediatorCompany"){
                    my $content_phones = '';
                    foreach my $val (@{$fltr->{arrayVal}}) {
                        $content_phones = $content_phones . $val . '|';
                    }
                    $content_phones =~ s/\|$//g;
                    push( @{$full_query{body}{query}{bool}{must_not}}, { regexp => { "phones" => $content_phones}});

                    if($fltr->{exactVal} == 0){
                        push(
                            @{$full_query{body}{query}{bool}{must_not}},  { exists => { "field" => "mediatorCompany"}});
                    } else {
                        push(
                            @{$full_query{body}{query}{bool}{must}},{ exists => { "field" => "mediatorCompany"}});
                    }
                } else{
                    foreach my $val (@{$fltr->{arrayVal}}) {
                       push (@{$values},
                           {
                               "term"  => {
                                   $fltr->{fieldName} => $val
                               }
                           }
                       )
                    }

                    if(defined $values){
                        push(
                            @{$full_query{body}{query}{bool}{must}},
                            {
                                "bool" => {
                                    "minimum_should_match" => 1,
                                    "should" => $values,
                                }
                            }
                        );
                    }
                }
            } elsif($fltr->{exactVal}) {
                push(
                    @{$full_query{body}{query}{bool}{must}},
                    {
                        "term"  => {
                            $fltr->{fieldName} => $fltr->{exactVal}
                        }
                    }
                );
            } else {
               if (defined $fltr->{lowerVal} && defined $fltr->{upperVal}) {
                   push(
                       @{$full_query{body}{query}{bool}{must}},
                       {
                           range => {
                               $fltr->{fieldName} => {
                                   gte => $fltr->{lowerVal},
                                   lte => $fltr->{upperVal}
                               }
                           }
                       }
                   );
               } elsif (defined $fltr->{lowerVal}) {
                   push(
                       @{$full_query{body}{query}{bool}{must}},
                       {
                           range => {
                               $fltr->{fieldName} => {
                                   gte => $fltr->{lowerVal}
                               }
                           }
                       }
                   );
               } elsif (defined $fltr->{upperVal}) {
                   push(
                       @{$full_query{body}{query}{bool}{must}},
                       {
                           range => {
                               $fltr->{fieldName} => {
                                   lte => $fltr->{upperVal}
                               }
                           }
                       }
                   );
               }
            }
        }
    }

    if(defined $sort) {
        $sort = parse_json($sort);
        foreach my $srt (keys %{$sort}) {
            push(
                @{$full_query{body}{sort}},
                {
                    $srt => { order => $sort->{$srt} }
                }
            );
        }
    } else{
        push(
            @{$full_query{body}{sort}},
            {
                addDate => { order => 'DESC' }
            }
        );
    }

    if($search_area && scalar $search_area){
        # $search_area =~ s/\[|\]|\{|\}|\"//g;
        # my @area;
        # while($search_area =~ /(lat:(\d+\.\d+)\,lon:(\d+\.\d+))/){
        #     if($2 && $3){
        #         push(@area,{lat =>$2, lon=>$3});
        #     }
        #     $search_area =~ s/$1//i;
        # }
        $search_area = parse_json($search_area);
        $full_query{body}{query}{bool}{filter}{geo_polygon} =
        {
            location => {
                points => \@{$search_area}
            }
        };
    }
    if($agent eq 'private'){
        push(
            @{$full_query{body}{query}{bool}{must_not}},
            {
                exists => {
                    field =>  "mediator_company"
                }
            }
        );
    } elsif($agent =~ /realtor (.{1,})/){
        my $content_phones = '';
        my $phones_str = $1;
        while($phones_str =~ /((7|8){0,1}(\d{10}))|(7\s{0,1}\((\d{3,4})\)\s{0,1}(\d{2,3})-(\d{2})-(\d{2}))/){
            if($5 && $6 && $7 && $8){
                $content_phones = $content_phones.'7'.$5.$6.$7.$8.'|';
                $phones_str =~ s/7\s{0,1}\(($5)\)\s{0,1}$6-$7-$8//i;
            } else {
                $content_phones = $content_phones.'7'.$3.'|';
                $phones_str =~ s/$1//i;
            }
        }
        $content_phones =~ s/\|$//g;
        push(
             @{$full_query{body}{query}{bool}{must}},
             {
                "bool" => {
                    "minimum_should_match" => 1,
                    "should" => [
                        { "regexp" => {
                            "owner_phones" => $content_phones
                            }
                        },
                        {
                            "exists" => {
                                "field" => "mediator_company"
                            }
                        }

                     ],
                }
            }
        );
    } elsif($agent =~ /phones (.{1,})/){
        my $content_phones = '';
        my $phones_str = $1;
        while($phones_str =~ /((7|8){0,1}(\d{10}))|(7\s{0,1}\((\d{3,4})\)\s{0,1}(\d{2,3})-(\d{2})-(\d{2}))/){
            if($5 && $6 && $7 && $8){
                $content_phones = $content_phones.'7'.$5.$6.$7.$8.'|';
                $phones_str =~ s/7\s{0,1}\(($5)\)\s{0,1}$6-$7-$8//i;
            } else {
                $content_phones = $content_phones.'7'.$3.'|';
                $phones_str =~ s/$1//i;
            }
        }
        $content_phones =~ s/\|$//g;
        push(
             @{$full_query{body}{query}{bool}{must}},
             {
                "bool" => {
                    "minimum_should_match" => 1,
                    "should" => [
                        { "regexp" => {
                            "owner_phones" => $content_phones
                            }
                        }
                     ],
                }
            }
        );
    }


    foreach (keys %source_media) {
         if($query =~/$_/){
             push(
                 @{$full_query{body}{query}{bool}{must}},
                 {
                     term => {
                         sourceMedia =>  $source_media{$_}
                     }
                 }
             );
             $query =~ s/$_//i;
         }
    }
    my $content_phones = ''; #+7 (924) 404-28-80 +7 (4212) 94-14-01
    while($query =~ /((7|8){0,1}(\d{10}))|(7\s{0,1}\((\d{3,4})\)\s{0,1}(\d{2,3})-(\d{2})-(\d{2}))/){
        if($5 && $6 && $7 && $8){
            $content_phones = $content_phones.'7'.$5.$6.$7.$8.'|';
            $query =~ s/$_//i;
        } else {
            $content_phones = $content_phones.'7'.$3.'|';
            $query =~ s/$_//i;
        }
    }
    $query =~ s/\+//g;
    $query = trim($query);
    $content_phones =~ s/\|$//g;
    if($query =~/organisation/ && $content_phones ne ''){
        $query =~ s/organisation//g;
        push(
             @{$full_query{body}{query}{bool}{must}},
             {
                "bool" => {
                    "minimum_should_match" => 1,
                    "should" => [
                        { "regexp" => {
                            "owner_phones" => $content_phones
                            }
                        },
                        {
                            "term" => {
                                "mediator_company" => $query
                            }
                        }

                     ],
                }
            }
        );
        $query = '';
    }elsif($content_phones ne ''){
        push(
             @{$full_query{body}{query}{bool}{must}},
             {
                "regexp" => {
                    "owner_phones" => $content_phones
                }
            }
        );
    }

    if(trim($query) ne ''){
        push(
            @{$full_query{body}{query}{bool}{must}},
                { multi_match => {
                            query =>  $query,
                            type => 'cross_fields',
                            operator =>  "and",
                            fields => [ "address_ext", "spec", "mediatorCompany" ]
                        }
                },
        );
    }

    # if(trim($query) ne ''){
    #     push(
    #         @{$full_query{body}{query}{bool}{must}},
    #             { term => {
    #                         media_info_saller =>  $query
    #                     }
    #             },
    #     );
    # }

    # if($change_date ne 'all' && $change_date ne ''){
    #     my $dt = DateTime->now()->subtract(days => $change_date-1);
    #     $dt->set(
    #         hour       => 0,
    #         minute     => 0,
    #         second     => 0,
    #         nanosecond => 0
    #     );
    #     push(
    #         @{$full_query{body}{query}{bool}{must}},
    #         {
    #             range => {
    #                 add_date => {
    #                     gte => $dt->datetime()
    #                 }
    #             }
    #         }
    #     );
    # }

    say Dumper %full_query;

    my $e = Search::Elasticsearch->new(nodes  => 'import.maklersoft.com:9200');
    my $results = $e->search(%full_query);

    return $self->render(json => $results->{hits});
}

1;
