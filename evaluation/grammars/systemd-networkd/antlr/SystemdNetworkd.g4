grammar SystemdNetworkd;

config : configSec*;

configSec
    : MATCH_TAG match
    | LINK_TAG link
    | NETWORK_TAG network
    | ADDR_TAG address
    | DHCP_SERVER_TAG dhcp_server
    ;

match 
    : NAME_KW ASSIGN nameList NL
    | MAC_ADDR_KW ASSIGN MAC_ADDR NL
    | HOST_KW ASSIGN NAME NL
    | VIRTUALIZATION_KW ASSIGN boolValue NL
    | DHCPV4_KW ASSIGN dhcpv4 NL
    ;

boolValue
    : TRUE | YES
    | FALSE | NO
    ;

link
    : MAC_ADDR_KW ASSIGN MAC_ADDR NL
    | MTU_BYTES_KW ASSIGN INTEGER NL
    | MULTICAST_KW ASSIGN boolValue NL
    ;

network
    : DHCP_KW ASSIGN (boolValue | IPV4 | IPV6) NL
    | DHCP_SERVER_KW ASSIGN boolValue NL
    | MULTICAST_DNS_KW ASSIGN (boolValue | RESOLVE) NL
    | DNSSEC_KW ASSIGN (boolValue | ALLOW_DOWNGRADE) NL
    | DNS_KW ASSIGN ip_addr NL
    | DOMAINS_KW ASSIGN domain_list NL
    | (IPV4_FORWARDING_KW | IPV6_FORWARDING_KW) ASSIGN boolValue NL
    | IP_MASQUERADE_KW ASSIGN (IPV4 | IPV6 | NO | BOTH) NL
    | IPV6_PRIVACY_EXTENSIONS_KW ASSIGN (boolValue | KERNEL | PREFER_PUBLIC) NL
    ;

nameAndNegName
    : NAME
    | EXCLAIM NAME
    ;

nameList
    : nameAndNegName*
    ;

domain : TILDE? NAME;
domain_list : domain*;

ip_addr
    : IPV4_ADDR
    | IPV6_ADDR
    ;

////////

ADDR_TAG : LB 'Address' RB NL;
ADDR_KW : 'Address';
address : ADDR_KW ASSIGN ip_addr NL;

////////

DHCPV4_KW : LB 'DHCPv4' RB;
USE_DNS_KW : 'UseDNS';
ANONYMIZE_KW : 'Anonymize';
USE_DOMAINS_KW : 'UseDomains';
ROUTE : 'route';
IPV6_ONLY_MODE : 'IPv6OnlyMode';

dhcpv4
    : USE_DNS_KW ASSIGN boolValue NL
    | ANONYMIZE_KW ASSIGN boolValue NL
    | USE_DOMAINS_KW ASSIGN (boolValue | ROUTE) NL
    | IPV6_ONLY_MODE ASSIGN boolValue NL;

////////

DHCP_SERVER_TAG : LB 'DHCPServer' RB NL;
POOL_OFFSET_KW : 'PoolOffset';
POOL_SIZE_KW : 'PoolSize';
EMIT_DNS_KW : 'EmitDNS';

dhcp_server
    : POOL_OFFSET_KW ASSIGN INTEGER NL
    | POOL_SIZE_KW ASSIGN INTEGER NL
    | EMIT_DNS_KW ASSIGN boolValue NL
    | DNS_KW ASSIGN ip_addr NL
    ;

LB : '[';
RB : ']';

NL: '\n';

IPV6_FORWARDING_KW : 'IPv6Forwarding';
IPV4_FORWARDING_KW : 'IPv4Forwarding';

MATCH_TAG : LB 'Match' RB NL;
LINK_TAG : LB 'Link' RB NL;
NETWORK_TAG : LB 'Network' RB NL;
NAME_KW : 'Name';
MAC_ADDR_KW : 'MACAddress';
HOST_KW : 'Host';
VIRTUALIZATION_KW : 'Virtualization';
MTU_BYTES_KW : 'MTUBytes';
MULTICAST_KW : 'Multicast';
DOMAINS_KW : 'Domains';
IP_MASQUERADE_KW : 'IPMasquerade';
IPV6_PRIVACY_EXTENSIONS_KW : 'IPv6PrivacyExtensions';
KERNEL : 'kernel';
PREFER_PUBLIC : 'prefer-public';

TRUE : 'true';
FALSE : 'false';

NO : 'no';
YES : 'yes';

BOTH : 'both';

EXCLAIM : '!';

ASSIGN : '=';

TILDE : '~';

IPV4 : 'ipv4';
IPV6 : 'ipv6';

DHCP_KW : 'DHCP';
DHCP_SERVER_KW : 'DHCPServer';
MULTICAST_DNS_KW : 'MulticastDNS';
RESOLVE : 'resolve';
DNSSEC_KW : 'DNSSEC';
ALLOW_DOWNGRADE : 'allow-downgrade';
DNS_KW : 'DNS';

WS
    : [ \t]+ -> skip
    ;

MAC_ADDR_SEG : [0-9a-fA-F][0-9a-fA-F];

MAC_ADDR : MAC_ADDR_SEG ':' MAC_ADDR_SEG ':' MAC_ADDR_SEG ':' MAC_ADDR_SEG ':' MAC_ADDR_SEG ':' MAC_ADDR_SEG;

IPV4_ADDR : IPV4_ADDR_SEG '.' IPV4_ADDR_SEG '.' IPV4_ADDR_SEG '.' IPV4_ADDR_SEG;

IPV4_ADDR_SEG : [0-9]+;

IPV6_ADDR : IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG? ':' IPV4_ADDR_SEG?;

IPV6_ADDR_SEG : [0-9a-fA-F]+;

INTEGER : [0-9]+ [KMG]?;

NAME
    : [_a-zA-Z0-9*]+
    ;
