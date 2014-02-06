
use DBI;
use CGI;
use HTML::Table;

$dbh = DBI->connect( "dbi:SQLite:/home/dewoller/bin/wikiContribution.db" ) || die "Cannot connect: $DBI::errstr";
$user = $dbh->selectall_arrayref( q( SELECT distinct user from diff; ));

my $table = HTML::Table->new(-columns => 3);
foreach (@$user) {
    my $userName = $_->[0];
    $userName = substr($userName, 0, length($userName ) - 2);
    my $sel = " SELECT  deletions, additions from diff where user like '$userName". "%';" ;
    $posts = $dbh->selectall_arrayref( $sel );
    map {
	$table->addRow($userName, $_->[0],$_->[1]);
    } @$posts;
}
$table->print;
