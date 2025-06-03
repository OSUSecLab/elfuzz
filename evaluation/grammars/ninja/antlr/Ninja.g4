grammar Ninja;

script : (statement NL)*;

statement
    : varDef
    | rule
    | build;

varDef: IDENTIFIER WS? ASSIGN WS? ARBITRARY_STRING;

indentVarDefList : (NL INDENT varDef)+;

rule : RULE WS IDENTIFIER NL indentVarDefList;
build : BUILD WS NO_WS_STRING WS? COLON WS? IDENTIFIER WS fileList;

FILE : NO_WS_STRING;

fileList : FILE (WS FILE)*;

INDENT : '  ';

IDENTIFIER : [_a-zA-Z][_a-zA-Z0-9]*;
ASSIGN : '=';
COLON : ':';
ARBITRARY_STRING : [^\n\r]+;
NO_WS_STRING : [^ \t\n\r]+;
WS : [ \t]+;
NL : [\n\r];
RULE : 'rule';
BUILD : 'build';
