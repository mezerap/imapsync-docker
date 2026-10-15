use strict;
use warnings;
use Test::More;
use Mail::IMAPClient;
use bytes ();

for my $unicode_folder (0, 1) {
    for my $body ("Subject: ASCII\r\n\r\nplain\r\n", "Subject: raw octets\r\n\r\n" . ("\xE9\xC4\x8D" x 20) . "\r\n") {
        my $folder = 'trash';
        utf8::upgrade($folder) if $unicode_folder;
        my ($captured, $options);
        {
            no warnings 'redefine';
            local *Mail::IMAPClient::_imap_command = sub {
                my ($self, $opt, $command) = @_;
                $captured = $command;
                $options = $opt;
                return $self;
            };
            local *Mail::IMAPClient::Results = sub { return ('1 OK [APPENDUID 1 42] complete'); };
            my $imap = Mail::IMAPClient->new();
            is($imap->append_string($folder, $body), 42, 'APPENDUID remains supported');
        }
        ok(!utf8::is_utf8($captured), 'APPEND payload is an octet string');
        is(length($captured), bytes::length($captured), 'write length equals byte length');
        my ($declared, $literal) = $captured =~ /\{(\d+)\}\r\n(.*)\z/s;
        is($declared, bytes::length($body), 'declared literal length is exact');
        is($literal, $body . "\r\n", 'message bytes preserved, including 8-bit content');
        is($options->{doretry}, 0, 'ambiguous APPEND cannot be automatically replayed');
    }
}
done_testing();
