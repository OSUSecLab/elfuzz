/*
 * [The "BSD license"]
 *  Copyright (c) 2019 PANTHEON.tech
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *  1. Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *  2. Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *  3. The name of the author may not be used to endorse or promote products
 *     derived from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 *  IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 *  OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 *  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 *  NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 *  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 *  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 *  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/*
 * Lexer grammar for https://www.w3.org/TR/2004/REC-xmlschema-2-20041028/#regexs.
 *
 * This grammar is modified in following ways:
 * - we use lexer modes to disambiguate between Char, XmlChar and QuantExact
 * - we use separate lexer tokens to disambiguate positive and negative character groups
 * - XmlCharIncDash is removed in favor of DASH token, which is handled in parser
 */

// Modified to fit the `re2` library

// $antlr-format alignTrailingComments true, columnLimit 150, maxEmptyLinesToKeep 1, reflowComments false, useTab false
// $antlr-format allowShortRulesOnASingleLine true, allowShortBlocksOnASingleLine true, minEmptyLines 0, alignSemicolons ownLine
// $antlr-format alignColons trailing, singleLineOverrulesHangingColon true, alignLexerCommands true, alignLabels true, alignTrailers true

lexer grammar regexLexer;

LPAREN      : '(';
RPAREN      : ')';
PIPE        : '|';
PLUS        : '+';
QUESTION    : '?';
STAR        : '*';
WildcardEsc : '.';
StarQuestion : '*?';
PlusQuestion : '+?';
QuestionQuestion : '??';
StarPlus : '*+';
PlusPlus : '++';
QuestionPlus : '?+';
SpecialGroup : '(?' ([P:#]);
SpecialGroupFlag : [imsU];
SpecialGrpupRaw : '(?';
Colon : ':';
Caret : '^';
Dollar : '$';
Char        : (Dollar | Caret | ~('.' | '\\' | '?' | '*' | '+' | '(' | ')' | '|' | '[' | ']'));

// Quantifier's quantity rule support
StartQuantity: '{' -> pushMode(QUANTITY);

// Single Character Escape
SingleCharEsc: SINGLE_ESC;

// Multi-Character Escape
MultiCharEsc: MULTI_ESC;

// Category Escape
CatEsc   : CAT_ESC   -> pushMode(CATEGORY);
ComplEsc : COMPL_ESC -> pushMode(CATEGORY);
CatEscSingle   : CAT_ESC_SINGLE;
ComplEscSingle : COMPL_ESC_SINGLE;

// Positive/Negative Character Group
NegCharGroup : '[^' -> pushMode(CHARGROUP);
PosCharGroup : '['  -> pushMode(CHARGROUP);
AsciiCharClass : '[:';

mode QUANTITY;
EndQuantity : '}' -> popMode;
QuantExact  : [0-9]+;
COMMA       : ',';

mode CATEGORY;
EndCategory: '}' -> popMode;

// Categories
IsCategory  : Letters | Marks | Numbers | Punctuation | Separators | Symbols | Others;
Letters     : 'L' [ultmo]?;
Marks       : 'M' [nce]?;
Numbers     : 'N' [dlo]?;
Punctuation : 'P' [cdseifo]?;
Separators  : 'Z' [slp]?;
Symbols     : 'S' [mcko]?;
Others      : 'C' [cfons]?;
SingleCat   : [LMNPZSC];

mode CHARGROUP;
EndCharGroup        : ']'       -> popMode;
EndAsciiCharClass         : ':]'      -> popMode;
XmlChar             : ~('-' | '[' | ']');

fragment CAT_ESC_SINGLE : '\\p';
fragment COMPL_ESC_SINGLE : '\\P';
fragment CAT_ESC    : '\\p{';
fragment COMPL_ESC  : '\\P{';
fragment MULTI_ESC  : '\\' [sSiIcCdDwWAbBgGZz];
fragment SINGLE_ESC : '\\' [aftnrv*CQE];
OCT_ESC : '\\' [0-9][0-9][0-9];
HEX_ESC : '\\x' [0-9a-fA-F][0-9a-fA-F];
HEX_ESC_ALT : '\\x{' [0-9a-fA-F]+ '}';

AsciiCharClassAlpha : 'alpha';
AsciiCharClassAlphaNum : 'alnum';
AsciiCharClassAscii : 'ascii';
AsciiCharClassBlank : 'blank';
AsciiCharClassCntrl : 'cntrl';
AsciiCharClassDigit : 'digit';
AsciiCharClassGraph : 'graph';
AsciiCharClassLower : 'lower';
AsciiCharClassPrint : 'print';
AsciiCharClassPunct : 'punct';
AsciiCharClassSpace : 'space';
AsciiCharClassUpper : 'upper';
AsciiCharClassWord : 'word';
AsciiCharClassXDigit : 'xdigit';
