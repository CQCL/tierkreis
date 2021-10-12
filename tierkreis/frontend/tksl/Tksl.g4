grammar Tksl;
/*
 Parser rules
 */
start: declaration+;
declaration:
    function
    | TYPE alias = ID '=' type_def = type_ ';';
function: GRAPH function_name = ID graph_type code_block;
code_block: '{' (instruction ';')+ '}';
type_:
    | TYPE_INT
    | TYPE_BOOL
    | TYPE_STR
    | TYPE_FLOAT
    | TYPE_CIRCUIT
    | TYPE_PAIR '<' first = type_ ',' second = type_ '>'
    | TYPE_MAP '<' key = type_ ',' val = type_ '>'
    | TYPE_VEC '<' element = type_ '>'
    | TYPE_STRUCT '<' fields = f_param_list '>'
    | graph_type
    | ID;
graph_type:
    '(' inputs = f_param_list ')' '->' '(' outputs = f_param_list ')';
f_param_list: (par_list += f_param (',' par_list += f_param)*)?;
f_param: label = ID ':' annotation = type_;

instruction:
    call = node_inputs '->' target = ID                                                            # CallMap
    | OUTPUT '(' arglist ')'                                                                       # OutputCall
    | CONST const_name = ID '=' const_val = const_                                                 # ConstDecl
    | IF '(' outport ';' named_map? ')' if_block = code_block ELSE else_block = code_block '->' ID #
        IfBlock
    | WHILE '(' named_map? ')' condition = code_block DO body = code_block '->' target = ID # Loop
    | port_label '->' port_label                                                            # Edge;

node_inputs:
    f_name '(' arglist? ')'            # FuncCall
    | thunkable_port '(' named_map ')' # Thunk;

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
vec_const: '[' (elems += const_ (',' elems += const_)*)? ']';
const_:
    | bool_token
    | SIGNED_INT
    | SIGNED_FLOAT
    | SHORT_STRING
    | struct_const
    | vec_const;

f_name: func_name = ID | namespace = ID '::' func_name = ID;

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
GRAPH: 'graph';
TRUE: 'true';
FALSE: 'false';
IF: 'if';
ELSE: 'else';
WHILE: 'while';
DO: 'do';
CONST: 'const';
OUTPUT: 'output';

TYPE_INT: 'int';
TYPE_BOOL: 'bool';
TYPE_FLOAT: 'float';
TYPE_STR: 'str';
TYPE_PAIR: 'pair';
TYPE_MAP: 'map';
TYPE_VEC: 'vector';
TYPE_STRUCT: 'struct';
TYPE_CIRCUIT: 'circuit';

NEWLINE:
    '\r'? '\n' -> skip; // return newlines to parser (is end-statement signal)
WS: [ \t]+ -> skip; // toss out whitespace
COMMENT: '//' ~[\r\n]* -> skip;
fragment LCASE_LATTER: 'a' ..'z';
fragment UCASE_LATTER: 'A' ..'Z';
fragment LETTER: LCASE_LATTER | UCASE_LATTER;
ID: ('_' | LETTER) ('_' | LETTER | DIGIT)*;
