# Transpiler from ANTLR4 to ISLa BNFs

A simple transpiler from ANTLR4 grammars to [ISLa BNFs](https://github.com/rindPHI/isla).

To use it, first generate code to parse ANTLR4 grammars:

```bash
antlr4 -Dlanguage=Python3 -lib $(pwd)/g4 -o $(pwd)/g4 -visitor g4/ANTLRv4Lexer.g4 g4/ANTLRv4Parser.g4
```

Then run the transpiler:

```bash
python transpile_g4.py grammarParser.g4 grammarLexer.g4 -o grammar.bnf
```

or

```bash
python transpile_g4.py grammar.g4 -o grammar.bnf
```
