import click as clk
import g4
from antlr4 import CommonTokenStream, FileStream, ParserRuleContext
from enum import Enum
from typing import override, Sequence, Literal, MutableSequence, Any
import itertools
import logging
import networkx as nx

logger = logging.getLogger(__file__)

class ANTLR4GrammarKind(Enum):
    Lexer = 1
    Parser = 2
    Grammar = 3
    
class ANTLR4Grammar:
    def __init__(self, kind: ANTLR4GrammarKind, name: str, rules: Sequence[ParserRuleContext]):
        self.kind = kind
        self.name = name
        self.rules = rules
        
class BNFNonTerminal:
    def __init__(self, name: str):
        self.name = name
    
    def __str__(self) -> str:
        return f'<{self.name}>'
    
    def to_str(self) -> str:
        return str(self)
    
    def is_tmp(self) -> bool:
        return self.name.startswith('__')
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, BNFNonTerminal) and value.name == self.name
    
    def __hash__(self) -> int:
        return hash(self.name)

class BNFTerminal:
    class Special(Enum):
        SINGLE_CHAR_WILDCARD = 1
        
        def __str__(self) -> str:
            match self:
                case BNFTerminal.Special.SINGLE_CHAR_WILDCARD:
                    return '.'
    
    def __init__(self, value: str | Special):
        if isinstance(value, str):
            escaped = escape(value)
            self.value = escaped
        else:
            self.value = value
        
    def is_special(self) -> bool:
        return isinstance(self.value, BNFTerminal.Special)
        
    def __str__(self) -> str:
        return str(self.value) if not self.is_special() else str(self.value)
    
    def to_str(self) -> str:
        return f'"{self.unescape_quote(unescape(self.value))}"' if not self.is_special() else str(self.value)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, BNFTerminal) and value.value == self.value
    
    def __hash__(self) -> int:
        return hash(self.value)

    @staticmethod
    def unescape_quote(text: str) -> str:
        return text.replace('"', '\\"')
    
class BNFNotSet:
    def __init__(self, elements: Sequence[BNFNonTerminal | BNFTerminal]):
        self.elements = set(elements)
    
    def __str__(self) -> str:
        return f'~({" | ".join(str(e) for e in self.elements)})'
    
    def to_str(self) -> str:
        return f'~({" | ".join(e.to_str() for e in self.elements)})'
    
class BNFAlt:
    def __init__(self, seq: MutableSequence[BNFNonTerminal | BNFTerminal | BNFNotSet]):
        self.seq = seq
    
    def to_str(self) -> str:
        return ' '.join(e.to_str() for e in self.seq) if self.seq else '""'
    
    def set_element(self, i: int, value: BNFNonTerminal | BNFTerminal | BNFNotSet):
        self.seq[i] = value

class BNFRuleKind(Enum):
    PARSER = 1
    LEXER = 2
    REC_LEXER = 3

class BNFRule:
    def __init__(self, head: BNFNonTerminal, kind: BNFRuleKind, alts: Sequence[BNFAlt]):
        assert alts
        self.head = head
        self.alts = alts
        self.kind = kind

    def to_str(self) -> str:
        head_str = f'{self.head} ::= '
        indention = ' ' * (len(head_str) - 2)
        if not self.alts:
            return head_str
        elif len(self.alts) == 1:
            return head_str + self.alts[0].to_str()
        else:
            result_lines = [head_str + self.alts[0].to_str()]
            for alt in self.alts[1:]:
                result_lines.append(f'{indention}| {alt.to_str()}')
            return '\n'.join(result_lines)
        

class BNFGrammar:
    def __init__(self, name: str, rules: Sequence[BNFRule]):
        self.name = name
        self.rules = rules
    
    def to_str(self) -> str:
        return '\n'.join(rule.to_str() for rule in self.rules)

    def __getattr__(self, name: str) -> Any:
        match name:
            case 'root':
                return self.rules[0]
            case _:
                raise AttributeError(f'Attribute {name} not found')


class Analyzer(g4.ANTLRv4ParserVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.grammar_kind = None
        self.grammar_name = None
        self.rules = []

    def reset(self):
        self.grammar_kind = None
        self.grammar_name = None
        self.rules = []
        
    def analyze(self, ctx: g4.ANTLRv4Parser.GrammarSpecContext) -> ANTLR4Grammar:
        self.reset()
        self.visit(ctx)
        if self.grammar_kind == ANTLR4GrammarKind.Grammar:
            first_grammar_rule = None
            for i, rule in enumerate(self.rules):
                if isinstance(rule, g4.ANTLRv4Parser.ParserRuleSpecContext):
                    first_grammar_rule = i
                    break
            assert first_grammar_rule is not None
            if first_grammar_rule != 0:
                r = self.rules.pop(first_grammar_rule)
                self.rules.insert(0, r)
        return self.grammar()
    
    def grammar(self):
        assert self.grammar_kind is not None
        assert self.grammar_name is not None
        return ANTLR4Grammar(self.grammar_kind, self.grammar_name, self.rules)
    
    @override
    def visitGrammarType(self, ctx: g4.ANTLRv4Parser.GrammarTypeContext):
        if ctx.LEXER() is not None:
            self.grammar_kind = ANTLR4GrammarKind.Lexer
        elif ctx.PARSER() is not None:
            self.grammar_kind = ANTLR4GrammarKind.Parser
        else:
            self.grammar_kind = ANTLR4GrammarKind.Grammar
        return self.visitChildren(ctx)
    
    @override
    def visitGrammarDecl(self, ctx: g4.ANTLRv4Parser.GrammarDeclContext):
        r = self.visitChildren(ctx)
        id: str = ctx.identifier().getText()
        
        if id.endswith('Lexer'):
            assert self.grammar_kind == ANTLR4GrammarKind.Lexer
            self.grammar_name = id.removesuffix('Lexer')
        elif id.endswith('Parser'):
            assert self.grammar_kind == ANTLR4GrammarKind.Parser
            self.grammar_name = id.removesuffix('Parser')
        else:
            assert self.grammar_kind == ANTLR4GrammarKind.Grammar
            self.grammar_name = id

        return r

    @override
    def visitParserRuleSpec(self, ctx: g4.ANTLRv4Parser.ParserRuleSpecContext):
        self.rules.append(ctx)
        return self.visitChildren(ctx)
    
    @override
    def visitLexerRuleSpec(self, ctx: g4.ANTLRv4Parser.LexerRuleSpecContext):
        assert self.grammar_kind == ANTLR4GrammarKind.Lexer or self.grammar_kind == ANTLR4GrammarKind.Grammar
        self.rules.append(ctx)
        return self.visitChildren(ctx)
    
def parse_one_file(filename) -> ANTLR4Grammar:
    parser = g4.ANTLRv4Parser(CommonTokenStream(g4.ANTLRv4Lexer(FileStream(filename))))
    return Analyzer().analyze(parser.grammarSpec())

    
class Transpiler(g4.ANTLRv4ParserVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.__tmp_rule_counter = 0
        self.skippable_tokens: dict[BNFNonTerminal, set[BNFNonTerminal]] = {}
        
    def reset(self):
        self.__tmp_rule_counter = 0
        self.skippable_tokens = {}
        
    def get_and_increment_rule_counter(self) -> int:
        r = self.__tmp_rule_counter
        self.__tmp_rule_counter += 1
        return r
    
    @staticmethod
    def shrink(bnf_grammar: BNFGrammar) -> BNFGrammar:
        rule_map: dict[BNFNonTerminal, BNFRule] = {}
        for rule in bnf_grammar.rules:
            rule_map[rule.head] = rule
        
        reachable: set[BNFNonTerminal] = set()
        work_list: list[BNFRule] = [bnf_grammar.root]
        
        while work_list:
            top = work_list.pop()
            if top.head in reachable:
                continue
            reachable.add(top.head)
            for alt in top.alts:
                for elem in alt.seq:
                    if isinstance(elem, BNFNonTerminal):
                        work_list.append(rule_map[elem])
        
        new_rules = []
        for rule in bnf_grammar.rules:
            if rule.head in reachable:
                new_rules.append(rule)
        return BNFGrammar(bnf_grammar.name, new_rules)

    def __all_skippable(self, current_rule: BNFNonTerminal) -> Sequence[BNFNonTerminal]:
        result = set()
        for skippable, exclude in self.skippable_tokens.items():
            if current_rule in exclude:
                continue
            result.add(skippable)
        return list(result)

    def __insert_skippable_tokens(self, bnf_grammar: BNFGrammar) -> BNFGrammar:
        new_rules = []
        for rule in bnf_grammar.rules:
            skippables = self.__all_skippable(rule.head)
            if rule.kind != BNFRuleKind.PARSER or not skippables:
                new_rules.append(rule)
                continue
            new_alts = []
            for alt in rule.alts:
                new_seq = []
                for i, elem in enumerate(alt.seq):
                    if (i > 0 
                        and isinstance(elem, BNFNonTerminal) and isinstance(alt.seq[i - 1], BNFNonTerminal)
                        and (not elem.is_tmp() or not alt.seq[i - 1].is_tmp())
                    ):
                        new_seq.extend(skippables)
                    new_seq.append(elem)
                new_alts.append(BNFAlt(new_seq))
            new_rules.append(BNFRule(rule.head, rule.kind, new_alts))
        return BNFGrammar(bnf_grammar.name, new_rules)
    
    def __skippable_closure(self, bnf_grammar: BNFGrammar):
        def dfs(current_rule_head: BNFNonTerminal, visited: set[BNFNonTerminal], rule_map: dict[BNFNonTerminal, BNFRule]):
            if current_rule_head in visited:
                return
            visited.add(current_rule_head)
            rule = rule_map[current_rule_head]
            for alt in rule.alts:
                for elem in alt.seq:
                    if isinstance(elem, BNFNonTerminal):
                        dfs(elem, visited, rule_map)
        
        rule_map: dict[BNFNonTerminal, BNFRule] = {}
        for rule in bnf_grammar.rules:
            rule_map[rule.head] = rule
        
        for skippable in self.skippable_tokens.keys():
            new_skippables = set()
            new_skippables.update(self.skippable_tokens[skippable])
            dfs(skippable, new_skippables, rule_map)
            self.skippable_tokens[skippable] = new_skippables
    
    def transpile(
        self, 
        antlr4_grammar: ANTLR4Grammar, 
        canonicalize: bool = False, 
        char_set: set[int] | Literal['ascii', 'unicode'] | None = None,
        white_space: str| None = None
    ) -> BNFGrammar:
        logger.info(f'Transpiling {antlr4_grammar.name}')
        self.grammar_name = antlr4_grammar.name
        
        rule_num = len(antlr4_grammar.rules) 
        bnf_rules: list[BNFRule] = []
        for i, antlr4_rule in enumerate(antlr4_grammar.rules):
            rule_name = (antlr4_rule.RULE_REF().getText() 
                         if isinstance(antlr4_rule, g4.ANTLRv4Parser.ParserRuleSpecContext)
                         else antlr4_rule.TOKEN_REF().getText())
            logger.info(f'Transpiling rule {rule_name} [{i + 1} / {rule_num}]')
            new_bnf_rules = self.visit(antlr4_rule)
            bnf_rules.extend(new_bnf_rules)
        
        original_root = bnf_rules[0].head
        root_head = BNFNonTerminal("start")
        root = BNFRule(root_head, BNFRuleKind.PARSER, [BNFAlt([original_root])])
        bnf_rules.insert(0, root)

        # Insert a rule for the special EOF token if needed
        rule_names = set([rule.head for rule in bnf_rules])
        EOF_TOKEN = BNFNonTerminal("EOF")
        if EOF_TOKEN not in rule_names:
            break_all = False
            for rule in bnf_rules:
                for alt in rule.alts:
                    for elem in alt.seq:
                        if elem == EOF_TOKEN:
                            bnf_rules.append(BNFRule(EOF_TOKEN, BNFRuleKind.LEXER, [BNFAlt([])]))
                            break_all = True
                            break
                    if break_all:
                        break
                if break_all:
                    break

        assert not self.skippable_tokens
        if white_space is not None:
            one_or_none_ws_head = BNFNonTerminal(self.new_tmp_rule_name('white_space01'))
            # ws_rule = self.__gen_repeat_rule('?', one_or_none_ws_head, BNFNonTerminal(white_space))
            ws_rule = BNFRule(one_or_none_ws_head, BNFRuleKind.LEXER, [BNFAlt([BNFNonTerminal(white_space)])])
            self.skippable_tokens[one_or_none_ws_head] = set()
            bnf_rules.append(ws_rule)
            
        logger.info('Sanitizing')
        r = BNFGrammar(antlr4_grammar.name, bnf_rules)
        self.__sanitize(r)
        
        if canonicalize:
            assert char_set is not None
            
            logger.info('Lex canonicalizing')
            r = self.__canonicalize_lex(r, char_set)
            
            logger.info('Grammar canonicalizing')
            r = self.__canonicalize_grammar(r)
            for rule in r.rules:
                for alt in rule.alts:
                    for elem in alt.seq:
                        if isinstance(elem, BNFNotSet):
                            assert False, f'Not canonicalized: {rule.head}'
        
        logger.info('Computing skippable closures')
        self.__skippable_closure(r)

        logger.info('Inserting skippable tokens')
        r = self.__insert_skippable_tokens(r)

        logger.info('Shrinking')
        r = self.shrink(r)
        return r
    
    def new_tmp_rule_name(self, prefix: str = 'tmp_rule') -> str:
        return f'__{prefix}_{self.get_and_increment_rule_counter()}'
    
    @override
    def visitParserRuleSpec(self, ctx: g4.ANTLRv4Parser.ParserRuleSpecContext) -> Sequence[BNFRule]:
        head = BNFNonTerminal(ctx.RULE_REF().getText())
        alts, new_rules = self.visit(ctx.ruleBlock())
        result = [BNFRule(head, BNFRuleKind.PARSER, alts)] + new_rules
        return result
    
    @override
    def visitRuleBlock(self, ctx: g4.ANTLRv4Parser.RuleBlockContext) -> tuple[Sequence[BNFAlt], Sequence[BNFRule]]:
        return self.visit(ctx.ruleAltList())

    @override
    def visitRuleAltList(self, ctx: g4.ANTLRv4Parser.RuleAltListContext) -> tuple[Sequence[BNFAlt], Sequence[BNFRule]]:
        labeled_alts = ctx.labeledAlt()
        arms = []
        new_rules = []
        for labeled_alt in labeled_alts:
            arm, new_rules_ = self.visit(labeled_alt)
            arms.append(arm)
            new_rules.extend(new_rules_)
        return arms, new_rules
    
    @override
    def visitLabeledAlt(self, ctx: g4.ANTLRv4Parser.LabeledAltContext) -> tuple[BNFAlt, Sequence[BNFRule]]:
        return self.visit(ctx.alternative())
    
    @override
    def visitAlternative(self, ctx: g4.ANTLRv4Parser.AlternativeContext) -> tuple[BNFAlt, Sequence[BNFRule]]:
        elements = ctx.element()
        seq = []
        new_rules = []
        for element in elements:
            single, new_rules_ = self.visit(element)
            seq.append(single)
            new_rules.extend(new_rules_)
        return BNFAlt(seq), new_rules

    @override
    def visitElement(self, ctx: g4.ANTLRv4Parser.ElementContext) -> tuple[BNFNonTerminal | BNFTerminal | BNFNotSet, Sequence[BNFRule]]:
        if (atom := ctx.atom()) is not None:
            single: BNFNonTerminal | BNFTerminal | BNFNotSet = self.visit(atom)
            if (enbf_suffix := ctx.ebnfSuffix()) is None:
                return single, []
            tmp_rule_head = BNFNonTerminal(self.new_tmp_rule_name())
            tmp_rule = self.__gen_repeat_rule(enbf_suffix.getText(), tmp_rule_head, single)
            return tmp_rule_head, [tmp_rule]
        elif (labeled_element := ctx.labeledElement()) is not None:
            return self.visit(labeled_element)
        elif (ebnf := ctx.ebnf()) is not None:
            return self.visit(ebnf)
        else:
            return NotImplemented()
        
    @staticmethod
    def __gen_repeat_rule(suffix: str, this_head: BNFNonTerminal, single, kind: Literal[BNFRuleKind.PARSER, BNFRuleKind.LEXER] = BNFRuleKind.PARSER) -> BNFRule:
        match suffix:
            case '?' | '??':
                arms =  [BNFAlt([]), BNFAlt([single])]
                match kind:
                    case BNFRuleKind.PARSER:
                        actual_kind = BNFRuleKind.PARSER
                    case BNFRuleKind.LEXER:
                        actual_kind = BNFRuleKind.LEXER
                    case _:
                        raise NotImplementedError()
            case '+' | '+?':
                arms =  [BNFAlt([single]), BNFAlt([single, this_head])]
                match kind:
                    case BNFRuleKind.PARSER:
                        actual_kind = BNFRuleKind.PARSER
                    case BNFRuleKind.LEXER:
                        actual_kind = BNFRuleKind.REC_LEXER
                    case _:
                        raise NotImplementedError()
            case '*' | '*?':
                arms =  [BNFAlt([]), BNFAlt([single, this_head])]
                match kind:
                    case BNFRuleKind.PARSER:
                        actual_kind = BNFRuleKind.PARSER
                    case BNFRuleKind.LEXER:
                        actual_kind = BNFRuleKind.REC_LEXER
                    case _:
                        raise NotImplementedError()
            case _:
                raise NotImplementedError()
        return BNFRule(this_head, actual_kind, arms)
    
    @override
    def visitEbnf(self, ctx: g4.ANTLRv4Parser.EbnfContext) -> tuple[BNFNonTerminal, Sequence[BNFRule]]:
        new_rules = []
        block, new_rules_ = self.visit(ctx.block())
        new_rules.extend(new_rules_)
        
        head = BNFNonTerminal(self.new_tmp_rule_name())
        
        if (block_suffix := ctx.blockSuffix()) is not None:
            rule = self.__gen_repeat_rule(block_suffix.getText(), head, block)
        else:
            rule = BNFRule(head, BNFRuleKind.PARSER, [BNFAlt([block])])
            
        new_rules.append(rule)
        return head, new_rules
    
    @override
    def visitLabeledElement(self, ctx: g4.ANTLRv4Parser.LabeledElementContext) -> tuple[BNFNonTerminal | BNFTerminal | BNFNotSet, Sequence[BNFRule]]:
        if (atom := ctx.atom()) is not None:
            return self.visit(atom), []
        else:
            block = ctx.block()
            assert block is not None
            return self.visit(block)
    
    @override
    def visitBlock(self, ctx: g4.ANTLRv4Parser.BlockContext) -> tuple[BNFNonTerminal, Sequence[BNFRule]]:
        return self.visit(ctx.altList())
        
    @override
    def visitAltList(self, ctx: g4.ANTLRv4Parser.AltListContext) -> tuple[BNFNonTerminal, Sequence[BNFRule]]:
        rule_head = BNFNonTerminal(self.new_tmp_rule_name())
        new_rules = []
        alt_list = ctx.alternative()
        arms = []
        for alt in alt_list:
            _tmp: tuple[BNFAlt, Sequence[BNFRule]] = self.visit(alt)
            arm, new_rules_ = _tmp
            new_rules.extend(new_rules_)
            arms.append(arm)
        rule = BNFRule(rule_head, BNFRuleKind.PARSER, arms)
        new_rules.append(rule)
        return rule_head, new_rules

    @override
    def visitAtom(self, ctx: g4.ANTLRv4Parser.AtomContext) -> BNFNonTerminal | BNFTerminal | BNFNotSet:
        if (terminal := ctx.terminal()) is not None:
            return self.visit(terminal)
        elif (rule_ref := ctx.ruleref()) is not None:
            return self.visit(rule_ref)
        elif (not_set := ctx.notSet()) is not None:
            return self.visit(not_set)
        else:
            assert ctx.DOT() is not None
            return BNFTerminal(BNFTerminal.Special.SINGLE_CHAR_WILDCARD)
        
    @override
    def visitRuleref(self, ctx: g4.ANTLRv4Parser.RulerefContext) -> BNFNonTerminal:
        return BNFNonTerminal(ctx.RULE_REF().getText())
    
    @override
    def visitNotSet(self, ctx: g4.ANTLRv4Parser.NotSetContext) -> BNFNotSet:
        if (set_element := ctx.setElement()) is not None:
            return BNFNotSet(self.visit(set_element))
        elif (block_set := ctx.blockSet()) is not None:
            return BNFNotSet(self.visit(block_set))
        else:
            assert False
        
    @override
    def visitBlockSet(self, ctx: g4.ANTLRv4Parser.BlockSetContext) -> Sequence[BNFNonTerminal | BNFTerminal]:
        set_elements = ctx.setElement()
        result = []
        for set_element in set_elements:
            result.extend(self.visit(set_element))
        return result
    
    def transpile_lexer_char_set(self, char_set: str) -> Sequence[BNFTerminal] | BNFNotSet:
        assert char_set.startswith('[') and char_set.endswith(']')
        char_set = char_set.removeprefix('[').removesuffix(']')
        
        neg = False
        if char_set.startswith('^'):
            neg = True
            char_set = char_set.removeprefix('^')
        
        escaped_count = 0
        escaped_seq = ''
        
        result: Sequence[BNFTerminal] = []
        start_ord = None
        for i, c in enumerate(char_set):
            if escaped_count == 0:
                assert c != ']'
                match c:
                    case '\\':
                        escaped_count = 1
                        escaped_seq = '\\'
                    case _:
                        if start_ord is None:
                            if i < len(char_set) - 1 and char_set[i + 1] == '-':
                                logger.info(f'Char range from {c}')
                                start_ord = ord(c)
                            else:
                                result.append(BNFTerminal(c))
                        else:
                            match c:
                                case '-':
                                    pass
                                case _:
                                    logger.info(f'Char range to {c}')
                                    if start_ord == -1:
                                        continue
                                    end_ord = ord(c)
                                    for i in range(start_ord, end_ord + 1):
                                        result.append(BNFTerminal(chr(i)))
                                    start_ord = None
            else:
                match c:
                    case 'u':
                        escaped_count = 4
                        escaped_seq += 'u'
                    case 'p' | 'P':
                        escaped_count = -1
                    case _:
                        escaped_seq += c
                        match escaped_count:
                            case -1:
                                if c == '}':
                                    escaped_count = 0
                                    match CHAR_SET:
                                        case 'ascii':
                                            pass
                                        case 'unicode':
                                            return NotImplemented()
                                        case _:
                                            raise NotImplementedError()
                                else:
                                    escaped_seq += c
                            case 1:
                                escaped_count -= 1
                                if (
                                    escaped_seq.startswith('\\p')
                                    or escaped_seq.startswith('\\P')
                                ) and CHAR_SET == 'ascii':
                                    if i < len(char_set) - 1 and char_set[i + 1] == '-':
                                        start_ord = -1
                                    continue
                                if escaped_seq.startswith('\\u') and CHAR_SET == 'ascii':
                                    escaped_seq = escaped_seq.removeprefix('\\u')
                                    escaped_seq = escaped_seq.zfill(4)
                                    e_ord = int(escaped_seq, 16)
                                    if ord in range(0, 127):
                                        if i < len(char_set) - 1 and char_set[i + 1] == '-':
                                            start_ord = e_ord
                                        else:
                                            result.append(BNFTerminal(chr(e_ord)))
                                    else:
                                        if i < len(char_set) - 1 and char_set[i + 1] == '-':
                                            start_ord = -1
                                        continue
                                else:
                                    if i < len(char_set) - 1 and char_set[i + 1] == '-':
                                        start_ord = ord(escape(escaped_seq))
                                    else:
                                        result.append(BNFTerminal(escaped_seq))
                            case _:
                                escaped_count -= 1
        if not neg:
            return result
        else:
            return BNFNotSet(result)
    
    @override
    def visitSetElement(self, ctx: g4.ANTLRv4Parser.SetElementContext) -> Sequence[BNFNonTerminal | BNFTerminal] | BNFNotSet:
        if (char_set := ctx.LEXER_CHAR_SET()) is not None:
            return self.transpile_lexer_char_set(char_set.getText())
        elif (string_literal := ctx.STRING_LITERAL()) is not None:
            return [BNFTerminal(string_literal.getText().removesuffix("'").removeprefix("'"))]
        elif (token_ref := ctx.TOKEN_REF()) is not None:
            return [BNFNonTerminal(token_ref.getText())]
        elif (char_range := ctx.characterRange()) is not None:
            return self.visit(char_range)
        else:
            assert False
    
    @override
    def visitCharacterRange(self, ctx: g4.ANTLRv4Parser.CharacterRangeContext) -> Sequence[BNFTerminal]:
        [start, end] = ctx.STRING_LITERAL()
        start_c: str = start.getText().removesuffix("'").removeprefix("'")
        end_c: str = end.getText().removesuffix("'").removeprefix("'")
        
        global CHAR_SET
        if CHAR_SET == 'ascii' and start_c.startswith('\\u'):
            return []
        
        assert all(len(c) == 1 for c in [start_c, end_c])
        
        start_i = ord(start_c)
        end_i = ord(end_c)
        
        result = []
        for i in range(start_i, end_i + 1):
            result.append(BNFTerminal(chr(i)))
        return result

    @override
    def visitLexerRuleSpec(self, ctx: g4.ANTLRv4Parser.LexerRuleSpecContext) -> Sequence[BNFRule]:
        rule_head = BNFNonTerminal(ctx.TOKEN_REF().getText())
        arms, new_rules, skippable = self.visit(ctx.lexerRuleBlock())
        rule = BNFRule(rule_head, BNFRuleKind.LEXER, arms)
        for s in skippable:
            self.skippable_tokens[s] = set([rule_head])
        return [rule] + new_rules
        
    
    @override
    def visitLexerRuleBlock(self, ctx: g4.ANTLRv4Parser.LexerRuleBlockContext) -> tuple[Sequence[BNFAlt], Sequence[BNFRule], Sequence[BNFNonTerminal]]:
        return self.visit(ctx.lexerAltList())

    @override
    def visitLexerAltList(self, ctx: g4.ANTLRv4Parser.LexerAltListContext) -> tuple[Sequence[BNFAlt], Sequence[BNFRule], Sequence[BNFNonTerminal]]:
        lexer_alts = ctx.lexerAlt()
        arms = []
        new_rules = []
        skippable = []
        for lexer_alt in lexer_alts:
            arm, new_rules_, commands = self.visit(lexer_alt)
            new_rules.extend(new_rules_)
            # if 'skip' in set(commands):
                # skippable_head = BNFNonTerminal(self.new_tmp_rule_name('skippable_token'))
                # skippable_rule = BNFRule(skippable_head, BNFRuleKind.LEXER, [arm])
                # repeat_skippable_head = BNFNonTerminal(self.new_tmp_rule_name('repeat_skippable_token'))
                # repeat_skippable_rule = self.__gen_repeat_rule('?', repeat_skippable_head, skippable_head, kind=BNFRuleKind.LEXER)
                # new_rules.append(skippable_rule)
                # new_rules.append(repeat_skippable_rule)
                # arms.append(BNFAlt([repeat_skippable_head]))
                # skippable.append(repeat_skippable_head)
            # else:
            #     arms.append(arm)
            arms.append(arm)
        return arms, new_rules, skippable

    '''
    Mark lexer rules that contain or are on cycles
    '''
    def __sanitize(self, bnf_grammar: BNFGrammar):
        rule_map: dict[BNFNonTerminal, BNFRule] = {}
        for rule in bnf_grammar.rules:
            rule_map[rule.head] = rule
        
        rule_refs: dict[BNFNonTerminal, set[BNFNonTerminal]] = {}
        for rule_head, rule in rule_map.items():
            rule_refs[rule_head] = set()
            for alt in rule.alts:
                for elem in alt.seq:
                    if isinstance(elem, BNFNonTerminal):
                        if rule_head not in rule_refs:
                            rule_refs[rule_head] = set()
                        rule_refs[rule_head].add(elem)

        edges = []
        for head, refs in rule_refs.items():
            for ref in refs:
                edges.append((head, ref))
        
        g = nx.DiGraph(edges)
        cycles = nx.simple_cycles(g, length_bound=20) # Dude, the grammar won't be so complex that any cycle is longer than 20
        tainted = set()
        for rule in bnf_grammar.rules:
            if rule.kind == BNFRuleKind.REC_LEXER:
                tainted.add(rule.head)
        for cycle in cycles:
            for head in cycle:
                rule = rule_map[head]
                if rule.head in tainted:
                    continue
                if rule.kind == BNFRuleKind.LEXER:
                    rule.kind = BNFRuleKind.REC_LEXER
                tainted.add(rule.head)

        count = 1
        changed = True
        while changed:
            logger.debug(f'Taint iter {count}')
            changed = False

            for head, rule in rule_map.items():
                if head in tainted:
                    continue
                inner_changed = False
                for alt in rule.alts:
                    for ele in alt.seq:
                        if isinstance(ele, BNFNonTerminal):
                            if ele in tainted:
                                if rule.kind == BNFRuleKind.LEXER:
                                    rule.kind = BNFRuleKind.REC_LEXER
                                tainted.add(head)
                                changed = True
                                inner_changed = True
                                break
                    if inner_changed:
                        break
                if inner_changed:
                    break
    
    @override
    def visitLexerAtom(self, ctx: g4.ANTLRv4Parser.LexerAtomContext) -> Sequence[BNFNonTerminal | BNFTerminal] | BNFNotSet:
        if (char_range := ctx.characterRange()) is not None:
            return self.visit(char_range)
        elif (terminal := ctx.terminal()) is not None:
            return [self.visit(terminal)]
        elif (not_set := ctx.notSet()) is not None:
            return [self.visit(not_set)]
        elif (char_set := ctx.LEXER_CHAR_SET()) is not None:
            return self.transpile_lexer_char_set(char_set.getText())
        else:
            assert ctx.DOT() is not None
            return [BNFTerminal(BNFTerminal.Special.SINGLE_CHAR_WILDCARD)]
    
    @override
    def visitLexerElement(self, ctx: g4.ANTLRv4Parser.LexerElementContext) -> tuple[BNFNonTerminal, Sequence[BNFRule]]:
        new_rules = []
        kind = BNFRuleKind.LEXER
        if (lexer_atom := ctx.lexerAtom()) is not None:
            base_head = BNFNonTerminal(self.new_tmp_rule_name())
            single_seq: Sequence[BNFNonTerminal | BNFTerminal] | BNFNotSet = self.visit(lexer_atom)
            single_head = BNFNonTerminal(self.new_tmp_rule_name())
            if isinstance(single_seq, BNFNotSet):
                single = BNFRule(single_head, BNFRuleKind.LEXER, [BNFAlt([single_seq])])
            else:
                single = BNFRule(
                    single_head,
                    BNFRuleKind.LEXER,
                    [BNFAlt([t]) for t in single_seq] if single_seq else [BNFAlt([])]
                )
            new_rules.append(single)
            if (suffix := ctx.ebnfSuffix()) is not None:
                base = self.__gen_repeat_rule(suffix.getText(), base_head, single_head, kind=BNFRuleKind.LEXER)
            else:
                base = BNFRule(base_head, BNFRuleKind.LEXER, [BNFAlt([single_head])])
            new_rules.append(base)
        elif (lexer_block := ctx.lexerBlock()) is not None:
            base_head = BNFNonTerminal(self.new_tmp_rule_name())
            _tmp: tuple[Sequence[BNFAlt], Sequence[BNFRule], Sequence[BNFNonTerminal]] = self.visit(lexer_block)
            arms, new_rules_, skippable = _tmp
            assert not skippable
            new_rules.extend(new_rules_)
            single_head = BNFNonTerminal(self.new_tmp_rule_name())
            single = BNFRule(single_head, BNFRuleKind.LEXER, arms)
            new_rules.append(single)
            if (suffix := ctx.ebnfSuffix()) is not None:
                base = self.__gen_repeat_rule(suffix.getText(), base_head, single_head, kind=BNFRuleKind.LEXER)
            else:
                base = BNFRule(base_head, BNFRuleKind.LEXER, [BNFAlt([single_head])])
            new_rules.append(base)
        else:
            assert ctx.actionBlock() is not None
            base_head = BNFNonTerminal(self.new_tmp_rule_name())
            base = BNFRule(base_head, BNFRuleKind.LEXER, [BNFAlt([])])
            new_rules.append(base)
        head = BNFNonTerminal(self.new_tmp_rule_name())
        rule = BNFRule(head, kind, [BNFAlt([base_head])])
        new_rules.append(rule)
        return head, new_rules
        
    @override
    def visitLexerBlock(self, ctx: g4.ANTLRv4Parser.LexerBlockContext) -> tuple[Sequence[BNFAlt], Sequence[BNFRule], Sequence[BNFNonTerminal]]:
        return self.visit(ctx.lexerAltList())
        
    @override
    def visitLexerAlt(self, ctx: g4.ANTLRv4Parser.LexerAltContext) -> tuple[BNFAlt, Sequence[BNFRule], list[str]]:
        elements = ctx.lexerElements()
        seq, new_rules = self.visit(elements)
        if (lexer_commands := ctx.lexerCommands()) is not None:
            commands = self.visit(lexer_commands)
        else:
            commands = []
        return BNFAlt(seq), new_rules, commands

    @override
    def visitLexerCommands(self, ctx: g4.ANTLRv4Parser.LexerCommandsContext) -> list[str]:
        return [ctx.getText() for ctx in ctx.lexerCommand()]

    @override
    def visitLexerElements(self, ctx: g4.ANTLRv4Parser.LexerElementsContext) -> tuple[Sequence[BNFNonTerminal], Sequence[BNFRule]]:
        elements = ctx.lexerElement()
        seq = []
        new_rules = []
        for element in elements:
            head, new_rules_ = self.visit(element)
            seq.append(head)
            new_rules.extend(new_rules_)
        return seq, new_rules
    
    @override
    def visitTerminal(self, ctx: g4.ANTLRv4Parser.TerminalContext) -> BNFNonTerminal | BNFTerminal:
        if (token_ref := ctx.TOKEN_REF()) is not None:
            return BNFNonTerminal(token_ref.getText())
        elif (string_literal := ctx.STRING_LITERAL()) is not None:
            return BNFTerminal(string_literal.getText().removesuffix("'").removeprefix("'"))
        else:
            assert False
            
    @staticmethod
    def __compute_set(rule: BNFRule, rule_set_map: dict[BNFNonTerminal, list[set[str] | BNFAlt]], char_set: set[int]) -> list[set[str] | BNFAlt]:
        assert rule.kind == BNFRuleKind.LEXER
        result = list()
        
        def process_elem(elem: BNFNonTerminal | BNFTerminal | BNFNotSet) -> set[BNFTerminal] | None:
            result = set()
            if isinstance(elem, BNFTerminal):
                match elem.value:
                    case BNFTerminal.Special.SINGLE_CHAR_WILDCARD:
                        result.update(chr(c) for c in char_set)
                    case _:
                        assert isinstance(elem.value, str)
                        result.add(elem.value)
            elif isinstance(elem, BNFNotSet):
                sub = set()
                for e in elem.elements:
                    if isinstance(e, BNFNonTerminal):
                        assert e in rule_set_map
                        if len(tmp := rule_set_map[e]) == 1 and isinstance((s := tmp[0]), set):
                            sub.update(s)
                        else:
                            return None
                    else:
                        match e.value:
                            case BNFTerminal.Special.SINGLE_CHAR_WILDCARD:
                                sub.update(chr(c) for c in char_set)
                            case _:
                                assert isinstance(e.value, str)
                                escaped = str(e)
                                sub.add(escaped)
                assert all(
                    len(e) == 1 or e == '\\"'
                    for e in sub
                )
                char_set_str = set(map(lambda ord: chr(ord), char_set))
                result.update(char_set_str - sub)
            else:
                assert isinstance(elem, BNFNonTerminal)
                assert elem in rule_set_map
                if len(tmp := rule_set_map[elem]) == 1 and isinstance((s := tmp[0]), set):
                    result.update(s)
                else:
                    return None
            return result
        
        accumulate = set()
        for alt in rule.alts:
            throwed = False
            choices = []
            for elem in alt.seq:
                if (s := process_elem(elem)) is None:
                    throwed = True
                    result.append(accumulate)
                    result.append(alt)
                    break
                choices.append(process_elem(elem))
            if throwed:
                continue
            count = 1
            for c in choices:
                count *= len(c)
            logger.debug(f'Seq count: {rule.head} -> {count}')
            LIMIT = 1000
            if count > LIMIT:
                logger.warning(f'Rule {rule.head} has {count} possible choices exceeding {LIMIT}. Give up expanding.')

                # Pray and hope no bug occurs
                result.append(accumulate)
                result.append(alt)
                continue
            possible_seq = itertools.product(*choices)
            for seq in possible_seq:
                accumulate.add(''.join(seq))
        if accumulate:
            result.append(accumulate)
        return result
    
    @staticmethod
    def __topo_order(rule_map: dict[BNFNonTerminal, BNFRule]) -> Sequence[BNFRule]:
        result = []
        
        COUNT_MAX = 1e9
        
        rule_ref_count: dict[BNFNonTerminal, int] = {}
        for rule in rule_map.values():
            if rule.kind != BNFRuleKind.LEXER:
                continue
            refed = set()
            for alt in rule.alts:
                for elem in alt.seq:
                    if isinstance(elem, BNFNonTerminal):
                        assert elem != rule.head
                        refed.add(elem)
            for r in refed:
                rule_ref_count[r] = rule_ref_count.get(r, 0) + 1
                assert rule_ref_count[r] < COUNT_MAX, "May have a cycle!"
        for rule in rule_map.values():
            if rule.kind != BNFRuleKind.LEXER:
                continue
            rule_ref_count[rule.head] = rule_ref_count.get(rule.head, 0)
        
        work_list: list[BNFNonTerminal] = []
        for rule_head, count in rule_ref_count.items():
            if count == 0:
                work_list.append(rule_head)
        
        while work_list:
            top_head = work_list.pop()
            top = rule_map[top_head]
            result.append(top)
            assert rule_ref_count[top_head] == 0
            
            refed = set() 
            for alt in top.alts:
                for elem in alt.seq:
                    if isinstance(elem, BNFNonTerminal):
                        refed.add(elem)
            
            to_add = set()
            for r in refed:
                assert rule_ref_count[r] >= 1
                rule_ref_count[r] -= 1
                if rule_ref_count[r] == 0:
                    to_add.add(r)
            
            for a in to_add:
                work_list.append(a)
        return result

    '''
    Expand not sets in parser rules to token sets.
    '''
    def __canonicalize_grammar(self, bnf_grammar: BNFGrammar) -> BNFGrammar:
        # XXX: The ANTLR4 grammar is stronger than standard BNF grammars
        #  For example, `grammarHead: ~"string_literal"` cannot be represented in standard BNF
        #  since `union(set_of_all_tokens)` may be infinite. We would have to exclude `"string_literal"`
        #  from the infinite set, which is not possible in standard BNF.
        #  As a result, we only transpile a restricted version of the syntax and leave the other cases undefined.
        #  It may cause imprecision.
        
        new_rules = []
        token_set: set[BNFNonTerminal] = set()
        for rule in bnf_grammar.rules:
            if rule.kind == BNFRuleKind.PARSER:
                continue
            if rule.head.is_tmp():
                continue
            token_set.add(rule.head)
        
        to_add = []
        for rule in bnf_grammar.rules:
            if rule.kind != BNFRuleKind.PARSER:
                new_rules.append(rule)
                continue
            new_alts = []
            for alt in rule.alts:
                new_seq = []
                for elem in alt.seq:
                    if isinstance(elem, BNFNotSet):
                        tmp_head = BNFNonTerminal(self.new_tmp_rule_name())
                        sub = set()
                        for e in elem.elements:
                            if isinstance(e, BNFNonTerminal):
                                sub.add(e)
                        choices = token_set - sub
                        tmp_alts = [
                            BNFAlt([c]) for c in choices
                        ]
                        tmp_rule = BNFRule(tmp_head, BNFRuleKind.LEXER, tmp_alts)
                        to_add.append(tmp_rule)
                        new_seq.append(tmp_head)
                        continue        
                    new_seq.append(elem)
                new_alts.append(BNFAlt(new_seq))
            new_rules.append(BNFRule(rule.head, BNFRuleKind.PARSER, new_alts))
        new_rules.extend(to_add)
        return BNFGrammar(bnf_grammar.name, new_rules)
        
    '''
    Expand non-recursive lexer rules to character sets.
    '''
    def __canonicalize_lex(self, bnf_grammar: BNFGrammar, char_set: set[int] | Literal['ascii', 'unicode']) -> BNFGrammar:
        match char_set:
            case 'ascii':
                all_chars = set(range(0, 128))
            case _:
                raise NotImplementedError()
            
        rule_map: dict[BNFNonTerminal, BNFRule] = {}
        for rule in bnf_grammar.rules:
            rule_map[rule.head] = rule    
        
        topo_order = self.__topo_order(rule_map)
        rule_set_map: dict[BNFNonTerminal, list[set[str] | BNFAlt]] = {}
        for rule in reversed(topo_order):
            rule_set_map[rule.head] = self.__compute_set(rule, rule_set_map, all_chars)
            
        new_rules = []
        for rule in bnf_grammar.rules:
            if rule.kind == BNFRuleKind.LEXER:
                rule_set = rule_set_map[rule.head]
                new_alts = []
                already_in = set()
                for set_or_arm in rule_set:
                    if isinstance(set_or_arm, set):
                        new_alts.extend([BNFAlt([BNFTerminal(unescape(c))]) for c in sorted(set_or_arm) if c not in already_in])
                        already_in.update(set_or_arm)
                    else:
                        assert isinstance(set_or_arm, BNFAlt)
                        new_alts.append(set_or_arm)
                new_rules.append(BNFRule(rule.head, BNFRuleKind.LEXER, new_alts))
            else:
                new_rules.append(rule)
        
        return BNFGrammar(bnf_grammar.name, new_rules)
            

def escape(text: str) -> str:
    return text.encode('ascii').decode('unicode_escape')

def unescape(text: str) -> str:
    return text.encode('unicode_escape').decode('ascii')
    

def combine_grammars(grammar1: ANTLR4Grammar, grammar2: ANTLR4Grammar) -> ANTLR4Grammar:
    match (grammar1.kind, grammar2.kind):
        case (ANTLR4GrammarKind.Lexer, ANTLR4GrammarKind.Parser):
            lexer_grammar = grammar1
            parser_grammar = grammar2
        case (ANTLR4GrammarKind.Parser, ANTLR4GrammarKind.Lexer):
            lexer_grammar = grammar2
            parser_grammar = grammar1
        case _:
            raise ValueError("There must be one lexer grammar and one parser grammar")
    assert lexer_grammar.name == parser_grammar.name
    
    rules = list(parser_grammar.rules) + list(lexer_grammar.rules)
    
    return ANTLR4Grammar(ANTLR4GrammarKind.Grammar, lexer_grammar.name, rules)


@clk.command()
@clk.argument('input',
              type=clk.Path(exists=True, file_okay=True, dir_okay=False, readable=True), 
              required=True,
              nargs=-1)
@clk.option('--output', '-o',
             type=clk.Path(file_okay=True, dir_okay=False, writable=True, allow_dash=True),
             help='The output file to write the transpiled grammar to',
             default='-')
@clk.option('--log-level', type=str, default='INFO')
@clk.option('--character-set', '-s', type=str, default='ascii')
@clk.option('--white-space', '-ws', type=str, default=None)
def main(input, output, log_level, character_set, white_space):
    global CHAR_SET
    match character_set:
        case 'ascii':
            CHAR_SET = 'ascii'
        case 'unicode':
            raise NotImplementedError('Unicode character set is not supported yet')
        case _:
            raise ValueError("Invalid character set")
    match log_level:
        case 'INFO':
            logging.basicConfig(level=logging.INFO)
        case 'DEBUG':
            logging.basicConfig(level=logging.DEBUG)
        case _:
            raise ValueError("Invalid log level")
    match input:
        case [grammar_file]:
            antlr4_grammar = parse_one_file(grammar_file)
            assert antlr4_grammar.kind == ANTLR4GrammarKind.Grammar
        case [grammar_file1, grammar_file2]:
            _grammar1 = parse_one_file(grammar_file1)
            _grammar2 = parse_one_file(grammar_file2)
            antlr4_grammar = combine_grammars(_grammar1, _grammar2)
        case _:
            raise ValueError("Invalid number of input files")
    bnf_grammar = Transpiler().transpile(antlr4_grammar, canonicalize=True, char_set=CHAR_SET, white_space=white_space)
    with clk.open_file(output, 'w') as outfile:
        outfile.write(bnf_grammar.to_str())

if __name__ == '__main__':
    main()
