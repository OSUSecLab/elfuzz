/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2014 by Bart Kiers
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 *
 * Project      : python3-parser; an ANTLR4 grammar for Python 3
 *                https://github.com/bkiers/python3-parser
 * Developed by : Bart Kiers, bart@big-o.nl
 */

// Scraping from https://docs.python.org/3/reference/grammar.html

// $antlr-format alignTrailingComments true, columnLimit 150, minEmptyLines 1, maxEmptyLinesToKeep 1, reflowComments false, useTab false
// $antlr-format allowShortRulesOnASingleLine false, allowShortBlocksOnASingleLine true, alignSemicolons hanging, alignColons hanging

parser grammar Python3Parser;

options {
    // superClass = Python3ParserBase;
    tokenVocab = Python3Lexer;
}

// Insert here @header for C++ parser.

// All comments that start with "///" are copy-pasted from
// The Python Language Reference

single_input
    : NEWLINE
    | simple_stmts
    | compound_stmt NEWLINE
    ;

file_input
    : (NEWLINE | stmt)* EOF
    ;

eval_input
    : testlist NEWLINE* EOF
    ;

decorator
    : AT dotted_name (OPEN_PAREN arglist? CLOSE_PAREN)? NEWLINE
    ;

decorators
    : decorator+
    ;

decorated
    : decorators (classdef | funcdef | async_funcdef)
    ;

async_funcdef
    : ASYNC funcdef
    ;

funcdef
    : DEF name parameters (ARROW test)? COLON block
    ;

parameters
    : OPEN_PAREN typedargslist? CLOSE_PAREN
    ;

typedargslist
    : (
        tfpdef (ASSIGN test)? (COMMA tfpdef (ASSIGN test)?)* (
            COMMA (
                STAR tfpdef? (COMMA tfpdef (ASSIGN test)?)* (COMMA (POWER tfpdef COMMA?)?)?
                | POWER tfpdef COMMA?
            )?
        )?
        | STAR tfpdef? (COMMA tfpdef (ASSIGN test)?)* (COMMA (POWER tfpdef COMMA?)?)?
        | POWER tfpdef COMMA?
    )
    ;

tfpdef
    : name (COLON test)?
    ;

varargslist
    : (
        vfpdef (ASSIGN test)? (COMMA vfpdef (ASSIGN test)?)* (
            COMMA (
                STAR vfpdef? (COMMA vfpdef (ASSIGN test)?)* (COMMA (POWER vfpdef COMMA?)?)?
                | POWER vfpdef (COMMA)?
            )?
        )?
        | STAR vfpdef? (COMMA vfpdef (ASSIGN test)?)* (COMMA (POWER vfpdef COMMA?)?)?
        | POWER vfpdef COMMA?
    )
    ;

vfpdef
    : name
    ;

stmt
    : simple_stmts
    | compound_stmt
    ;

simple_stmts
    : simple_stmt (SEMI_COLON simple_stmt)* SEMI_COLON? NEWLINE
    ;

simple_stmt
    : (
        expr_stmt
        | del_stmt
        | pass_stmt
        | flow_stmt
        | import_stmt
        | global_stmt
        | nonlocal_stmt
        | assert_stmt
    )
    ;

expr_stmt
    : testlist_star_expr (
        annassign
        | augassign (yield_expr | testlist)
        | (ASSIGN (yield_expr | testlist_star_expr))*
    )
    ;

annassign
    : COLON test (ASSIGN test)?
    ;

testlist_star_expr
    : (test | star_expr) (COMMA (test | star_expr))* COMMA?
    ;

augassign
    : (
        ADD_ASSIGN
        | SUB_ASSIGN
        | MULT_ASSIGN
        | AT_ASSIGN
        | DIV_ASSIGN
        | MOD_ASSIGN
        | AND_ASSIGN
        | OR_ASSIGN
        | XOR_ASSIGN
        | LEFT_SHIFT_ASSIGN
        | RIGHT_SHIFT_ASSIGN
        | POWER_ASSIGN
        | IDIV_ASSIGN
    )
    ;

// For normal and annotated assignments, additional restrictions enforced by the interpreter
del_stmt
    : DEL exprlist
    ;

pass_stmt
    : PASS
    ;

flow_stmt
    : break_stmt
    | continue_stmt
    | return_stmt
    | raise_stmt
    | yield_stmt
    ;

break_stmt
    : BREAK
    ;

continue_stmt
    : CONTINUE
    ;

return_stmt
    : RETURN testlist?
    ;

yield_stmt
    : yield_expr
    ;

raise_stmt
    : RAISE (test (FROM test)?)?
    ;

import_stmt
    : import_name
    | import_from
    ;

import_name
    : IMPORT dotted_as_names
    ;

// note below: the (DOT | ELLIPSIS) is necessary because ELLIPSIS is tokenized as ELLIPSIS
import_from
    : (
        FROM ((DOT | ELLIPSIS)* dotted_name | (DOT | ELLIPSIS)+) IMPORT (
            STAR
            | OPEN_PAREN import_as_names CLOSE_PAREN
            | import_as_names
        )
    )
    ;

import_as_name
    : name (AS name)?
    ;

dotted_as_name
    : dotted_name (AS name)?
    ;

import_as_names
    : import_as_name (COMMA import_as_name)* COMMA?
    ;

dotted_as_names
    : dotted_as_name (COMMA dotted_as_name)*
    ;

dotted_name
    : name (DOT name)*
    ;

global_stmt
    : GLOBAL name (COMMA name)*
    ;

nonlocal_stmt
    : NONLOCAL name (COMMA name)*
    ;

assert_stmt
    : ASSERT test (COMMA test)?
    ;

compound_stmt
    : if_stmt
    | while_stmt
    | for_stmt
    | try_stmt
    | with_stmt
    | funcdef
    | classdef
    | decorated
    | async_stmt
    | match_stmt
    ;

async_stmt
    : ASYNC (funcdef | with_stmt | for_stmt)
    ;

if_stmt
    : IF test COLON block (ELIF test COLON block)* (ELSE COLON block)?
    ;

while_stmt
    : WHILE test COLON block (ELSE COLON block)?
    ;

for_stmt
    : FOR exprlist IN testlist COLON block (ELSE COLON block)?
    ;

try_stmt
    : (
        TRY COLON block (
            (except_clause COLON block)+ (ELSE COLON block)? (FINALLY COLON block)?
            | FINALLY COLON block
        )
    )
    ;

with_stmt
    : WITH with_item (COMMA with_item)* COLON block
    ;

with_item
    : test (AS expr)?
    ;

// NB compile.c makes sure that the default except clause is last
except_clause
    : EXCEPT (test (AS name)?)?
    ;

block
    : simple_stmts
    | NEWLINE INDENT stmt+ 
    ;

match_stmt
    : MATCH subject_expr COLON NEWLINE INDENT case_block+
    ;

subject_expr
    : star_named_expression COMMA star_named_expressions?
    | test
    ;

star_named_expressions
    : COMMA star_named_expression+ COMMA?
    ;

star_named_expression
    : STAR expr
    | test
    ;

case_block
    : CASE patterns guard? COLON block
    ;

guard
    : IF test
    ;

patterns
    : open_sequence_pattern
    | pattern
    ;

pattern
    : as_pattern
    | or_pattern
    ;

as_pattern
    : or_pattern AS pattern_capture_target
    ;

or_pattern
    : closed_pattern (OR_OP closed_pattern)*
    ;

closed_pattern
    : literal_pattern
    | capture_pattern
    | wildcard_pattern
    | value_pattern
    | group_pattern
    | sequence_pattern
    | mapping_pattern
    | class_pattern
    ;

literal_pattern
    : signed_number
    | complex_number
    | strings
    | NONE
    | TRUE
    | FALSE
    ;

literal_expr
    : signed_number
    | complex_number
    | strings
    | NONE
    | TRUE
    | FALSE
    ;

complex_number
    : signed_real_number ADD imaginary_number
    | signed_real_number MINUS imaginary_number
    ;

signed_number
    : NUMBER
    | MINUS NUMBER
    ;

signed_real_number
    : real_number
    | MINUS real_number
    ;

real_number
    : NUMBER
    ;

imaginary_number
    : NUMBER
    ;

capture_pattern
    : pattern_capture_target
    ;

pattern_capture_target
    : /* cannot be UNDERSCORE */ name
    ;

wildcard_pattern
    : UNDERSCORE
    ;

value_pattern
    : attr
    ;

attr
    : name (DOT name)+
    ;

name_or_attr
    : attr
    | name
    ;

group_pattern
    : OPEN_PAREN pattern CLOSE_PAREN
    ;

sequence_pattern
    : OPEN_BRACK maybe_sequence_pattern? CLOSE_BRACK
    | OPEN_PAREN open_sequence_pattern? CLOSE_PAREN
    ;

open_sequence_pattern
    : maybe_star_pattern COMMA maybe_sequence_pattern?
    ;

maybe_sequence_pattern
    : maybe_star_pattern (COMMA maybe_star_pattern)* COMMA?
    ;

maybe_star_pattern
    : star_pattern
    | pattern
    ;

star_pattern
    : STAR pattern_capture_target
    | STAR wildcard_pattern
    ;

mapping_pattern
    : OPEN_BRACE CLOSE_BRACE
    | OPEN_BRACE double_star_pattern COMMA? CLOSE_BRACE
    | OPEN_BRACE items_pattern COMMA double_star_pattern COMMA? CLOSE_BRACE
    | OPEN_BRACE items_pattern COMMA? CLOSE_BRACE
    ;

items_pattern
    : key_value_pattern (COMMA key_value_pattern)*
    ;

key_value_pattern
    : (literal_expr | attr) COLON pattern
    ;

double_star_pattern
    : POWER pattern_capture_target
    ;

class_pattern
    : name_or_attr OPEN_PAREN CLOSE_PAREN
    | name_or_attr OPEN_PAREN positional_patterns COMMA? CLOSE_PAREN
    | name_or_attr OPEN_PAREN keyword_patterns COMMA? CLOSE_PAREN
    | name_or_attr OPEN_PAREN positional_patterns COMMA keyword_patterns COMMA? CLOSE_PAREN
    ;

positional_patterns
    : pattern (COMMA pattern)*
    ;

keyword_patterns
    : keyword_pattern (COMMA keyword_pattern)*
    ;

keyword_pattern
    : name ASSIGN pattern
    ;

test
    : or_test (IF or_test ELSE test)?
    | lambdef
    ;

test_nocond
    : or_test
    | lambdef_nocond
    ;

lambdef
    : LAMBDA varargslist? COLON test
    ;

lambdef_nocond
    : LAMBDA varargslist? COLON test_nocond
    ;

or_test
    : and_test (OR and_test)*
    ;

and_test
    : not_test (AND not_test)*
    ;

not_test
    : NOT not_test
    | comparison
    ;

comparison
    : expr (comp_op expr)*
    ;

// <> isn't actually a valid comparison operator in Python. It's here for the
// sake of a __future__ import described in PEP 401 (which really works :-)
comp_op
    : LESS_THAN
    | GREATER_THAN
    | EQUALS
    | GT_EQ
    | LT_EQ
    | NOT_EQ_1
    | NOT_EQ_2
    | IN
    | NOT IN
    | IS
    | IS NOT
    ;

star_expr
    : STAR expr
    ;

expr
    : atom_expr
    | expr POWER expr
    | (ADD | MINUS | NOT_OP)+ expr
    | expr (STAR | AT | DIV | MOD | IDIV) expr
    | expr (ADD | MINUS) expr
    | expr (LEFT_SHIFT | RIGHT_SHIFT) expr
    | expr AND_OP expr
    | expr XOR expr
    | expr OR_OP expr
    ;

//expr: xor_expr (OR_OP xor_expr)*;
//xor_expr: and_expr (XOR and_expr)*;
//and_expr: shift_expr (AND_OP shift_expr)*;
//shift_expr: arith_expr (('<<OR_OP>>') arith_expr)*;
//arith_expr: term (('+OR_OP-') term)*;
//term: factor ((STAR|'@OR_OP/OR_OP%OR_OP//') factor)*;
//factor: ('+OR_OP-OR_OP~') factor | power;
//power: atom_expr (POWER factor)?;
atom_expr
    : AWAIT? atom trailer*
    ;

atom
    : OPEN_PAREN (yield_expr | testlist_comp)? CLOSE_PAREN
    | OPEN_BRACK testlist_comp? CLOSE_BRACK
    | OPEN_BRACE dictorsetmaker? CLOSE_BRACE
    | name
    | NUMBER
    | STRING+
    | ELLIPSIS
    | NONE
    | TRUE
    | FALSE
    ;

name
    : NAME
    | UNDERSCORE
    | MATCH
    ;

testlist_comp
    : (test | star_expr) (comp_for | (COMMA (test | star_expr))* COMMA?)
    ;

trailer
    : OPEN_PAREN arglist? CLOSE_PAREN
    | OPEN_BRACK subscriptlist CLOSE_BRACK
    | DOT name
    ;

subscriptlist
    : subscript_ (COMMA subscript_)* COMMA?
    ;

subscript_
    : test
    | test? COLON test? sliceop?
    ;

sliceop
    : COLON test?
    ;

exprlist
    : (expr | star_expr) (COMMA (expr | star_expr))* COMMA?
    ;

testlist
    : test (COMMA test)* COMMA?
    ;

dictorsetmaker
    : (
        ((test COLON test | POWER expr) (comp_for | (COMMA (test COLON test | POWER expr))* COMMA?))
        | ((test | star_expr) (comp_for | (COMMA (test | star_expr))* COMMA?))
    )
    ;

classdef
    : CLASS name (OPEN_PAREN arglist? CLOSE_PAREN)? COLON block
    ;

arglist
    : argument (COMMA argument)* COMMA?
    ;

// The reason that keywords are test nodes instead of NAME is that using NAME
// results in an ambiguity. ast.c makes sure it's a NAME.
// "test ASSIGN test" is really "keyword ASSIGN test", but we have no such token.
// These need to be in a single rule to avoid grammar that is ambiguous
// to our LL(1) parser. Even though 'test' includes '*expr' in star_expr,
// we explicitly match STAR here, too, to give it proper precedence.
// Illegal combinations and orderings are blocked in ast.c:
// multiple (test comp_for) arguments are blocked; keyword unpackings
// that precede iterable unpackings are blocked; etc.
argument
    : (test comp_for? | test ASSIGN test | POWER test | STAR test)
    ;

comp_iter
    : comp_for
    | comp_if
    ;

comp_for
    : ASYNC? FOR exprlist IN or_test comp_iter?
    ;

comp_if
    : IF test_nocond comp_iter?
    ;

// not used in grammar, but may appear in "node" passed from Parser to Compiler
encoding_decl
    : name
    ;

yield_expr
    : YIELD yield_arg?
    ;

yield_arg
    : FROM test
    | testlist
    ;

strings
    : STRING+
    ;