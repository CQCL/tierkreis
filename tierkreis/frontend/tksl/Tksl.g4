grammar Tksl;
/*
 Parser rules
 */
start: decs += declaration+;
declaration:
    GRAPH ID generics? graph_type code_block # FuncDef
    | USE namespace = ID '::' use_ids ';'    # UseDef
    | TYPE ID '=' type_ ';'                  # TypeAlias;
use_ids:
    names += ID
    | '{' names += ID (',' names += ID)* '}'
    | '*';

generics: '<' gen_ids += ID (',' gen_ids += ID)* '>';

code_block: '{' (inst_list += instruction ';')+ '}';
type_:
    | TYPE_INT
    | TYPE_BOOL
    | TYPE_STR
    | TYPE_FLOAT
    | TYPE_PAIR '<' first = type_ ',' second = type_ '>'
    | TYPE_MAP '<' key = type_ ',' val = type_ '>'
    | TYPE_VEC '<' element = type_ '>'
    | TYPE_STRUCT '<' fields = f_param_list '>'
    | TYPE_OPTION '<' inner = type_ '>'
    | graph_type
    | named_obj;

graph_type:
    '(' inputs = f_param_list ')' '->' '(' outputs = f_param_list ')';
f_param_list: (par_list += f_param (',' par_list += f_param)*)?;
f_param: label = ID ':' annotation = type_;

instruction:
    target = ID '<-' call = node_inputs            # CallMap
    | OUTPUT '(' arglist ')'                       # OutputCall
    | CONST const_name = ID '=' const_val = const_ # ConstDecl
    | target = ID '<-' IF '(' condition = outport ';' inputs = named_map? ')' if_block = code_block
        ELSE else_block = code_block                                      # IfBlock
    | target = ID '<-' LOOP '(' inputs = named_map? ')' body = code_block # Loop
    | source = port_label '->' target = port_label                        # Edge;

node_inputs:
    f_name '(' arglist? ')'             # FuncCall
    | thunkable_port '(' named_map? ')' # Thunk;

arglist: named_map | positional_args;
named_map: port_l += port_map (',' port_l += port_map)*;
positional_args: arg_l += outport (',' arg_l += outport)*;
port_map: inport ':' outport;

outport: thunkable_port | node_inputs | const_;

thunkable_port: port_label | ID;

const_assign: ID ':' const_;

struct_const:
    sid = struct_id '{' fields += const_assign (
        ',' fields += const_assign
    )* '}';

macro_const:
    ID '!' '(' cargs += const_ (',' cargs += const_)* ')';

vec_const: '[' (elems += const_ (',' elems += const_)*)? ']';
pair_const: '(' first = const_ ',' second = const_ ')';
opt_const: SOME '(' const_ ')' # Some | NONE # None;
const_:
    | bool_token
    | SIGNED_INT
    | SIGNED_FLOAT
    | SHORT_STRING
    | struct_const
    | macro_const
    | opt_const
    | pair_const
    | vec_const;

f_name: named_obj;
named_obj: name = ID | namespace = ID '::' name = ID;

struct_id: TYPE_STRUCT # AnonStruct | ID # NamedStruct;

port_label: ID '.' ID;

bool_token: TRUE | FALSE;

inport: ID;

/*
 Lexer rules
 */
fragment DIGIT: [0-9];
fragment INT: DIGIT+;
fragment DECIMAL: INT '.' INT? | '.' INT;
fragment EXP: ('e' | 'E') SIGNED_INT;
fragment SIGN: ('+' | '-');
SIGNED_INT: SIGN? INT; // match integers
SIGNED_FLOAT: SIGN? INT EXP | DECIMAL EXP?;

fragment STRING_ESCAPE_SEQ: '\\' . | '\\' NEWLINE;
SHORT_STRING:
    '\'' (STRING_ESCAPE_SEQ | ~[\\\r\n\f'])* '\''
    | '"' ( STRING_ESCAPE_SEQ | ~[\\\r\n\f"])* '"';

TYPE: 'type';
GRAPH: 'Graph';
TRUE: 'true';
FALSE: 'false';
IF: 'if';
ELSE: 'else';
LOOP: 'loop';
CONST: 'const';
OUTPUT: 'output';
USE: 'use';
SOME: 'Some';
NONE: 'None';

TYPE_INT: 'Int';
TYPE_BOOL: 'Bool';
TYPE_FLOAT: 'Float';
TYPE_STR: 'Str';
TYPE_OPTION: 'Option';
TYPE_PAIR: 'Pair';
TYPE_MAP: 'Map';
TYPE_VEC: 'Vector';
TYPE_STRUCT: 'Struct';
// TYPE_VAR: 'Var';

NEWLINE:
    '\r'? '\n' -> skip; // return newlines to parser (is end-statement signal)
WS: [ \t]+ -> skip; // toss out whitespace
COMMENT: '//' ~[\r\n]* -> skip;
fragment LCASE_LATTER: 'a' ..'z';
fragment UCASE_LATTER: 'A' ..'Z';
fragment LETTER: LCASE_LATTER | UCASE_LATTER;
ID: ('_' | LETTER) ('_' | LETTER | DIGIT)*;
