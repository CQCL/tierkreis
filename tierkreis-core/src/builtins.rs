//! Contains a [FunctionDeclaration] for each builtin function,
//! all grouped together in [namespace].
use std::collections::HashMap;

// The [`SignatureEntry`]s for all builtin operations.
use crate::graph::{Constraint, GraphType, Kind, Type, TypeScheme};
use crate::namespace::{FunctionDeclaration, Namespace};
use crate::symbol::{Label, Name, TypeVar};

/// Description of [builtin_id].
pub const DOCS_ID: &str = "Passes a single, arbitrary, value from input to output.";
/// Description of [builtin_sleep].
pub const DOCS_SLEEP: &str = "Identity function with an asynchronous delay input in seconds.";
/// Description of [builtin_eval].
pub const DOCS_EVAL: &str = "Evaluates the graph on the `thunk` input with other inputs \
    matching the graph inputs, producing outputs matching those of the graph.";
/// Description of [builtin_copy].
pub const DOCS_COPY: &str = "Copies its input value to each of its two outputs.";
/// Description of [builtin_discard].
pub const DOCS_DISCARD: &str = "Ignores its input value, has no outputs.";
/// Description of [builtin_equality].
pub const DOCS_EQUALITY: &str = "Check two input values of the same type for equality, \
    producing a boolean.";
/// Description of [builtin_switch].
pub const DOCS_SWITCH: &str = "Passes one or other of two inputs through according to a \
    third, boolean, input.";
/// Description of [builtin_make_pair].
pub const DOCS_MAKE_PAIR: &str = "Makes an output `Pair` from two separate inputs.";
/// Description of [builtin_unpack_pair].
pub const DOCS_UNPACK_PAIR: &str = "Splits an input `Pair` into two separate outputs.";
/// Description of [builtin_push].
pub const DOCS_PUSH: &str = "Adds an input element onto an input `Vec` to give an output `Vec`.";
/// Description of [builtin_pop].
pub const DOCS_POP: &str = "Pops the first element from an input `Vec`, returning said \
    element separately from the remainder `Vec`. Fails at runtime if the input `Vec` \
    is empty.";
/// Description of [builtin_loop].
pub const DOCS_LOOP: &str = "Repeatedly applies a `Graph` input while it produces \
    a `Variant` tagged `continue`, i.e. until it returns a value tagged `break`, \
    and then returns that value.";
/// Description of [builtin_sequence].
pub const DOCS_SEQUENCE: &str =
    "Sequence two graphs, where the outputs of the first graph match the inputs of the second.";
/// Description of [builtin_make_struct].
pub const DOCS_MAKE_STRUCT: &str = "Takes any number of inputs and produces a single \
    `Struct` output with a field for each input, field names matching input ports.";
/// Description of [builtin_unpack_struct].
pub const DOCS_UNPACK_STRUCT: &str = "Destructure a single `Struct` input, outputting one value \
     per field in the input, output ports matching field names.";
/// Description of [builtin_insert_key].
pub const DOCS_INSERT_KEY: &str = "Transforms an input `Map` into an output by adding an \
    entry (or replacing an existing one) for an input key and value.";
/// Description of [builtin_remove_key].
pub const DOCS_REMOVE_KEY: &str =
    "Remove a key (input) from a map (input), return the map and value.";
/// Description of [builtin_parallel].
pub const DOCS_PARALLEL: &str = "Merges two input `Graph`s into a single output `Graph` \
    with the disjoint union of their inputs and similarly their outputs.";
/// Description of [builtin_map].
pub const DOCS_MAP: &str = "Runs a Graph input on each element of a `Vec` input and \
    collects the results into a `Vec` output.";

/// Declaration for the `id` function, see [DOCS_ID].
pub fn builtin_id() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(Label::value(), a);
        t.add_output(Label::value(), a);
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_ID.to_string(),
        input_order: vec![Label::value()],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `sleep` function, see [DOCS_SLEEP].
pub fn builtin_sleep() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");

    let delay = Label::symbol("delay_secs");
    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(Label::value(), a);
        t.add_input(delay, Type::Float);
        t.add_output(Label::value(), a);
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_SLEEP.to_string(),
        input_order: vec![Label::value(), delay],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `eval` function, see [DOCS_EVAL].
pub fn builtin_eval() -> FunctionDeclaration {
    let inv = TypeVar::symbol("in");
    let outv = TypeVar::symbol("out");

    let type_scheme = TypeScheme::from({
        let mut thunk = GraphType::new();
        thunk.inputs.rest = Some(inv);
        thunk.outputs.rest = Some(outv);

        let mut t = GraphType::new();
        t.add_input(Label::thunk(), Type::Graph(thunk));
        t.inputs.rest = Some(inv);
        t.outputs.rest = Some(outv);

        t
    })
    .with_variable(inv, Kind::Row)
    .with_variable(outv, Kind::Row);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_EVAL.to_string(),
        input_order: vec![Label::thunk()],
        output_order: vec![],
    }
}

/// Declaration for the `copy` function, see [DOCS_COPY].
pub fn builtin_copy() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");
    let value_0 = Label::symbol("value_0");
    let value_1 = Label::symbol("value_1");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(Label::value(), a);
        t.add_output(value_0, a);
        t.add_output(value_1, a);
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_COPY.to_string(),
        input_order: vec![Label::value()],
        output_order: vec![value_0, value_1],
    }
}

/// Declaration for the `discard` function, see [DOCS_DISCARD].
pub fn builtin_discard() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(Label::value(), a);
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_DISCARD.to_string(),
        input_order: vec![Label::value()],
        output_order: vec![],
    }
}

/// Declaration for the `eq` function, see [DOCS_EQUALITY].
pub fn builtin_equality() -> FunctionDeclaration {
    let val = TypeVar::symbol("val");
    let value_0 = Label::symbol("value_0");
    let value_1 = Label::symbol("value_1");
    let result = Label::symbol("result");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(value_0, val);
        t.add_input(value_1, val);
        t.add_output(result, Type::Bool);
        t
    })
    .with_variable(val, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_EQUALITY.to_string(),
        input_order: vec![value_0, value_1],
        output_order: vec![result],
    }
}

/// Declaration for the `"neq"` function, which compares two inputs of the same
/// type and returns `true` if-and-only-if they are different.
pub fn builtin_not_equality() -> FunctionDeclaration {
    let val = TypeVar::symbol("val");
    let value_0 = Label::symbol("value_0");
    let value_1 = Label::symbol("value_1");
    let result = Label::symbol("result");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(value_0, val);
        t.add_input(value_1, val);
        t.add_output(result, Type::Bool);
        t
    })
    .with_variable(val, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: "Check two values are not equal.".into(),
        input_order: vec![value_0, value_1],
        output_order: vec![result],
    }
}

/// Declaration for the `switch` function, see [DOCS_SWITCH].
pub fn builtin_switch() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");
    let pred = Label::symbol("pred");
    let if_true = Label::symbol("if_true");
    let if_false = Label::symbol("if_false");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(pred, Type::Bool);
        t.add_input(if_true, a);
        t.add_input(if_false, a);
        t.add_output(Label::value(), a);
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_SWITCH.to_string(),
        input_order: vec![pred, if_true, if_false],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `make_pair` function, see [DOCS_MAKE_PAIR].
pub fn builtin_make_pair() -> FunctionDeclaration {
    let first = Label::symbol("first");
    let second = Label::symbol("second");
    let pair = Label::symbol("pair");
    let a = TypeVar::symbol("a");
    let b = TypeVar::symbol("b");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(first, a);
        t.add_input(second, b);
        t.add_output(pair, Type::Pair(Box::new(a.into()), Box::new(b.into())));
        t
    })
    .with_variable(a, Kind::Star)
    .with_variable(b, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_MAKE_PAIR.to_string(),
        input_order: vec![first, second],
        output_order: vec![pair],
    }
}

/// Declaration for the `unpack_pair` function, see [DOCS_UNPACK_PAIR].
pub fn builtin_unpack_pair() -> FunctionDeclaration {
    let first = Label::symbol("first");
    let second = Label::symbol("second");
    let pair = Label::symbol("pair");
    let a = TypeVar::symbol("a");
    let b = TypeVar::symbol("b");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(pair, Type::Pair(Box::new(a.into()), Box::new(b.into())));
        t.add_output(first, a);
        t.add_output(second, b);
        t
    })
    .with_variable(a, Kind::Star)
    .with_variable(b, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_UNPACK_PAIR.to_string(),
        input_order: vec![pair],
        output_order: vec![first, second],
    }
}

/// Declaration for the `push` function, see [DOCS_PUSH].
pub fn builtin_push() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");
    let item = Label::symbol("item");
    let vec = Label::symbol("vec");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(vec, Type::Vec(Box::new(a.into())));
        t.add_input(item, a);
        t.add_output(vec, Type::Vec(Box::new(a.into())));
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_PUSH.to_string(),
        input_order: vec![vec, item],
        output_order: vec![vec],
    }
}

/// Declaration for the `pop` function, see [DOCS_POP].
pub fn builtin_pop() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");
    let item = Label::symbol("item");
    let vec = Label::symbol("vec");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(vec, Type::Vec(Box::new(a.into())));
        t.add_output(vec, Type::Vec(Box::new(a.into())));
        t.add_output(item, a);
        t
    })
    .with_variable(a, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_POP.to_string(),
        input_order: vec![vec],
        output_order: vec![vec, item],
    }
}

/// Declaration for the `loop` function, see [DOCS_LOOP].
pub fn builtin_loop() -> FunctionDeclaration {
    let loop_var = TypeVar::symbol("loop_var");
    let result = TypeVar::symbol("result");
    let body = Label::symbol("body");

    let type_scheme = TypeScheme::from({
        use crate::graph::RowType;
        use std::collections::BTreeMap;
        let mut body_ty = GraphType::new();
        body_ty.add_input(Label::value(), loop_var);

        body_ty.add_output(
            Label::value(),
            Type::Variant(RowType {
                content: BTreeMap::from([
                    (Label::continue_(), Type::Var(loop_var)),
                    (Label::break_(), Type::Var(result)),
                ]),
                rest: None,
            }),
        );

        let mut t = GraphType::new();
        t.add_input(body, Type::Graph(body_ty));
        t.add_input(Label::value(), loop_var);
        t.add_output(Label::value(), result);
        t
    })
    .with_variable(loop_var, Kind::Star)
    .with_variable(result, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_LOOP.to_string(),
        input_order: vec![body, Label::value()],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `sequence` function, see [DOCS_SEQUENCE].
pub fn builtin_sequence() -> FunctionDeclaration {
    let inv = TypeVar::symbol("in");
    let middle = TypeVar::symbol("middle");
    let outv = TypeVar::symbol("out");
    let first = Label::symbol("first");
    let second = Label::symbol("second");
    let sequenced = Label::symbol("sequenced");

    let type_scheme = TypeScheme::from({
        let mut g1 = GraphType::new();
        g1.inputs.rest = Some(inv);
        g1.outputs.rest = Some(middle);

        let mut g2 = GraphType::new();
        g2.inputs.rest = Some(middle);
        g2.outputs.rest = Some(outv);

        let mut g3 = GraphType::new();
        g3.inputs.rest = Some(inv);
        g3.outputs.rest = Some(outv);

        let mut t = GraphType::new();
        t.add_input(first, Type::Graph(g1));
        t.add_input(second, Type::Graph(g2));
        t.add_output(sequenced, Type::Graph(g3));

        t
    })
    .with_variable(inv, Kind::Row)
    .with_variable(middle, Kind::Row)
    .with_variable(outv, Kind::Row);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_SEQUENCE.to_string(),
        input_order: vec![first, second],
        output_order: vec![sequenced],
    }
}

/// Declaration for the `make_struct` function, see [DOCS_MAKE_STRUCT].
pub fn builtin_make_struct() -> FunctionDeclaration {
    let fields = TypeVar::symbol("fields");
    let structv = Label::symbol("struct");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.inputs.rest = Some(fields);
        t.add_output(structv, Type::struct_from_row(fields.into()));
        t
    })
    .with_variable(fields, Kind::Row);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_MAKE_STRUCT.to_string(),
        input_order: vec![],
        output_order: vec![structv],
    }
}

/// Declaration for the `unpack_struct` function, see [DOCS_UNPACK_STRUCT].
pub fn builtin_unpack_struct() -> FunctionDeclaration {
    let fields = TypeVar::symbol("fields");
    let structv = Label::symbol("struct");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.outputs.rest = Some(fields);
        t.add_input(structv, Type::struct_from_row(fields.into()));
        t
    })
    .with_variable(fields, Kind::Row);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_UNPACK_STRUCT.to_string(),
        input_order: vec![structv],
        output_order: vec![],
    }
}

/// Declaration for the `"insert_key"` function, see [DOCS_INSERT_KEY].
pub fn builtin_insert_key() -> FunctionDeclaration {
    let keytype = TypeVar::symbol("a");
    let valtype = TypeVar::symbol("b");
    let maptype = Type::Map(Box::new(keytype.into()), Box::new(valtype.into()));
    let map = Label::symbol("map");
    let key = Label::symbol("key");
    let val = Label::symbol("val");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(map, maptype.clone());
        t.add_input(key, keytype);
        t.add_input(val, valtype);
        t.add_output(map, maptype);
        t
    })
    .with_variable(keytype, Kind::Star)
    .with_variable(valtype, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_INSERT_KEY.to_string(),
        input_order: vec![map, key, val],
        output_order: vec![map],
    }
}

/// Declaration for the `"remove_key"` function, see [DOCS_REMOVE_KEY].
pub fn builtin_remove_key() -> FunctionDeclaration {
    let keytype = TypeVar::symbol("a");
    let valtype = TypeVar::symbol("b");
    let maptype = Type::Map(Box::new(keytype.into()), Box::new(valtype.into()));
    let map = Label::symbol("map");
    let key = Label::symbol("key");
    let val = Label::symbol("val");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(map, maptype.clone());
        t.add_input(key, keytype);
        t.add_output(map, maptype);
        t.add_output(val, valtype);
        t
    })
    .with_variable(keytype, Kind::Star)
    .with_variable(valtype, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_REMOVE_KEY.to_string(),
        input_order: vec![map, key],
        output_order: vec![map, val],
    }
}

fn gen_binary_decl(
    in_type_: Type,
    out_type_: Type,
    name: &'static str,
    docs: &str,
) -> (Name, FunctionDeclaration) {
    let a = Label::symbol("a");
    let b = Label::symbol("b");

    let typescheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(a, in_type_.clone());
        t.add_input(b, in_type_);
        t.add_output(Label::value(), out_type_);
        t
    });

    let decl = FunctionDeclaration {
        type_scheme: typescheme,
        description: docs.into(),
        input_order: vec![a, b],
        output_order: vec![Label::value()],
    };

    (Name::symbol(name), decl)
}

/// Declaration for the `"int_to_float"` function
pub fn builtin_int_to_float() -> FunctionDeclaration {
    let int = Label::symbol("int");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(int, Type::Int);
        t.add_output(Label::value(), Type::Float);
        t
    });

    FunctionDeclaration {
        type_scheme,
        description: "Convert an integer to a float".into(),
        input_order: vec![int],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `"float_to_int"` function
pub fn builtin_float_to_int() -> FunctionDeclaration {
    let float = Label::symbol("float");

    let type_scheme = TypeScheme::from({
        let mut t = GraphType::new();
        t.add_input(float, Type::Float);
        t.add_output(Label::value(), Type::Int);
        t
    });

    FunctionDeclaration {
        type_scheme,
        description: "Convert a float to an integer".into(),
        input_order: vec![float],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `"parallel"` function, see [DOCS_PARALLEL].
pub fn builtin_parallel() -> FunctionDeclaration {
    let left_in = TypeVar::symbol("left_in");
    let right_in = TypeVar::symbol("right_in");
    let value_in = TypeVar::symbol("value_in");
    let left_out = TypeVar::symbol("left_out");
    let right_out = TypeVar::symbol("right_out");
    let value_out = TypeVar::symbol("value_out");
    let left = Label::symbol("left");
    let right = Label::symbol("right");
    let value = Label::symbol("value");

    let partition_in = Constraint::Partition {
        left: left_in.into(),
        right: right_in.into(),
        union: value_in.into(),
    };

    let partition_out = Constraint::Partition {
        left: left_out.into(),
        right: right_out.into(),
        union: value_out.into(),
    };

    let type_scheme = TypeScheme::from({
        let mut left_ty = GraphType::new();
        left_ty.inputs.rest = Some(left_in);
        left_ty.outputs.rest = Some(left_out);

        let mut right_ty = GraphType::new();
        right_ty.inputs.rest = Some(right_in);
        right_ty.outputs.rest = Some(right_out);

        let mut value_ty = GraphType::new();
        value_ty.inputs.rest = Some(value_in);
        value_ty.outputs.rest = Some(value_out);

        let mut t = GraphType::new();
        t.add_input(left, left_ty);
        t.add_input(right, right_ty);
        t.add_output(value, value_ty);
        t
    })
    .with_variable(left_in, Kind::Row)
    .with_variable(left_out, Kind::Row)
    .with_variable(right_in, Kind::Row)
    .with_variable(right_out, Kind::Row)
    .with_variable(value_in, Kind::Row)
    .with_variable(value_out, Kind::Row)
    .with_constraint(partition_in)
    .with_constraint(partition_out);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_PARALLEL.to_string(),
        input_order: vec![left, right],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `"partial"` function i.e. that partially-applies a
/// [Value::Graph] to some of its arguments
///
/// [Value::Graph]: crate::graph::Value::Graph
pub fn builtin_partial() -> FunctionDeclaration {
    let in_given = TypeVar::symbol("in_given");
    let in_rest = TypeVar::symbol("in_rest");
    let inv = TypeVar::symbol("in");
    let outv = TypeVar::symbol("outv");

    let partition_in = Constraint::Partition {
        left: Type::Var(in_given),
        right: Type::Var(in_rest),
        union: Type::Var(inv),
    };

    let type_scheme = TypeScheme::from({
        let mut thunk = GraphType::new();
        thunk.inputs.rest = Some(inv);
        thunk.outputs.rest = Some(outv);

        let mut value = GraphType::new();
        value.inputs.rest = Some(in_rest);
        value.outputs.rest = Some(outv);

        let mut t = GraphType::new();
        t.add_input(Label::thunk(), thunk);
        t.inputs.rest = Some(in_given);
        t.add_output(Label::value(), value);
        t
    })
    .with_variable(in_given, Kind::Row)
    .with_variable(in_rest, Kind::Row)
    .with_variable(inv, Kind::Row)
    .with_variable(outv, Kind::Row)
    .with_constraint(partition_in);

    FunctionDeclaration {
        type_scheme,
        description:
            "Partial application; output a new graph with some input values injected as constants"
                .to_string(),
        input_order: vec![Label::thunk()],
        output_order: vec![Label::value()],
    }
}

/// Declaration for the `map` function, see [DOCS_MAP].
pub fn builtin_map() -> FunctionDeclaration {
    let a = TypeVar::symbol("a");
    let b = TypeVar::symbol("b");

    let type_scheme = TypeScheme::from({
        let mut thunk = GraphType::new();
        thunk.add_input(Label::value(), a);
        thunk.add_output(Label::value(), b);

        let mut t = GraphType::new();
        t.add_input(Label::value(), Type::Vec(Box::new(Type::Var(a))));
        t.add_input(Label::thunk(), Type::Graph(thunk));
        t.add_output(Label::value(), Type::Vec(Box::new(Type::Var(b))));
        t
    })
    .with_variable(a, Kind::Star)
    .with_variable(b, Kind::Star);

    FunctionDeclaration {
        type_scheme,
        description: DOCS_MAP.to_string(),
        input_order: vec![Label::thunk(), Label::value()],
        output_order: vec![Label::value()],
    }
}

/// The namespace containing a [FunctionDeclaration] for each builtin function
pub fn namespace() -> Namespace<FunctionDeclaration> {
    let decs = HashMap::from([
        (Name::symbol("id"), builtin_id()),
        (Name::symbol("sleep"), builtin_sleep()),
        (Name::symbol("eval"), builtin_eval()),
        (Name::symbol("make_pair"), builtin_make_pair()),
        (Name::symbol("unpack_pair"), builtin_unpack_pair()),
        (Name::symbol("switch"), builtin_switch()),
        (Name::symbol("copy"), builtin_copy()),
        (Name::symbol("discard"), builtin_discard()),
        (Name::symbol("eq"), builtin_equality()),
        (Name::symbol("neq"), builtin_not_equality()),
        (Name::symbol("push"), builtin_push()),
        (Name::symbol("pop"), builtin_pop()),
        (Name::symbol("loop"), builtin_loop()),
        (Name::symbol("sequence"), builtin_sequence()),
        (Name::symbol("make_struct"), builtin_make_struct()),
        (Name::symbol("unpack_struct"), builtin_unpack_struct()),
        (Name::symbol("insert_key"), builtin_insert_key()),
        (Name::symbol("remove_key"), builtin_remove_key()),
        (Name::symbol("int_to_float"), builtin_int_to_float()),
        (Name::symbol("float_to_int"), builtin_float_to_int()),
        (Name::symbol("partial"), builtin_partial()),
        (Name::symbol("parallel"), builtin_parallel()),
        (Name::symbol("map"), builtin_map()),
        gen_binary_decl(
            Type::Int,
            Type::Int,
            "iadd",
            "Add integers a and b together; a + b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Int,
            "isub",
            "Subtract integer b from integer a; a - b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Int,
            "imul",
            "Multiply integers a and b together; a * b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Int,
            "idiv",
            "Integer division of a by b; a / b",
        ),
        gen_binary_decl(Type::Int, Type::Int, "imod", "Modulo of a by b; a % b"),
        gen_binary_decl(
            Type::Int,
            Type::Int,
            "ipow",
            "Exponentiate a by power b; a ^ b. b must be a positive integer.",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Float,
            "fadd",
            "Add floats a and b together; a + b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Float,
            "fsub",
            "Subtract float b from float a; a - b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Float,
            "fmul",
            "Multiply floats a and b together; a * b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Float,
            "fdiv",
            "float division of a by b; a / b",
        ),
        gen_binary_decl(Type::Float, Type::Float, "fmod", "Modulo of a by b; a % b"),
        gen_binary_decl(
            Type::Float,
            Type::Float,
            "fpow",
            "Exponentiate a by power b; a ^ b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Bool,
            "ilt",
            "Check if a is less than b; a < b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Bool,
            "ileq",
            "Check if a is less than or equal to b; a <= b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Bool,
            "igt",
            "Check if a is greater than b; a > b",
        ),
        gen_binary_decl(
            Type::Int,
            Type::Bool,
            "igeq",
            "Check if a is greater than or equal to b; a >= b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Bool,
            "flt",
            "Check if a is less than b; a < b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Bool,
            "fleq",
            "Check if a is less than or equal to b; a <= b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Bool,
            "fgt",
            "Check if a is greater than b; a > b",
        ),
        gen_binary_decl(
            Type::Float,
            Type::Bool,
            "fgeq",
            "Check if a is greater than or equal to b; a >= b",
        ),
        gen_binary_decl(
            Type::Bool,
            Type::Bool,
            "and",
            "Check a and b are true; a && b",
        ),
        gen_binary_decl(
            Type::Bool,
            Type::Bool,
            "or",
            "Check a or b are true; a || b",
        ),
        gen_binary_decl(
            Type::Bool,
            Type::Bool,
            "xor",
            "Check either a or b are true; a ^ b",
        ),
    ]);

    Namespace {
        functions: decs,
        subspaces: HashMap::new(),
    }
}
