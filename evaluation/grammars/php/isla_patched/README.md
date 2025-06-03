# Truncated ISLa grammar of PHP

The grammar of PHP contains complex loops, and will likely trap the ISLa solver. In our evaluation, it can never generate one test case within 10 minutes, which makes the grammar obviously impractical for fuzzing. The problem is due to the tree expansion algorithm used by ISLa (see [the ISLa paper](https://doi.org/10.1145/3519939.3523716)), and doesn't indicate errors in the grammar. A man-made yet simple grammar that contains complex loops is as follows:

```text
<start> ::= <n1>
<n1> ::= <n1> | <n2>
<n2> ::= <n1> | <n3> <n2> | <n2>
<n3> ::= <n1> | <n4> | <n2> <n3>
<n4> ::= <n1> | <n5> | <n1> <n3> <n5>
<n5> ::= <n1> | <n6> | <n2> <n2> <n4>
<n6> ::= <n1> | <n7>
<n7> ::= <n1> | <n8> | <n1> <n8>
<n8> ::= <n1> | <n9> | <n9> <n8> <n1>
<n9> ::= <n1> | "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" 
       | "i" | "j" | "k" | "l" | "m" | "n" | "o" | "p" | "q" 
       | "r" | "s" | "t" | "u" | "v" | "w" | "x" | "y" | "z"
```

The following command to invoke the ISLa solver on it will likely get stuck until hitting the recursion depth limit:

```bash
isla solve -d ./out grammar.bnf
```

To avoid this, we truncate some grammar rules to break loops larger than 70. It may cause imprecision but is necessary, as otherwise we cannot get any results from the ISLa solver. How we truncate the grammar is recorded in `removed_edges.txt`. A line in the file as follows

```text
<nonterm1> -> <nonterm1>-choice-1
```

means that we remove the first alternative of `<nonterm1>` in the grammar. We use `$project_root/evaluation/isla_adapt/truncate_grammar.py` to conduct the truncation.

Besides, we manually fix some problems that are not bugs but will cause ISLa solver to throw errors (due to its implementation limitation). Specifically, ISLa rejects to generate test cases when it encounters a rule like this:

```text
<consecutive_epsilons> ::= <maybe_epsilon1> <maybe_epsilon2>
<maybe_epsilon_1> ::= "a" | ""
<maybe_epsilon_2> ::= "b" | ""
```

We rewrite it as follows:

```text
<consecutive_epsilon> ::= <maybe_epsilon1> <maybe_epsilon2>
<maybe_epsilon_1> ::= "a" | <white_space>
<maybe_epsilon_2> ::= "b" | ""
```

It is functionally equivalent to the original grammar, as the parser will ignore the `<white_space>` token.
