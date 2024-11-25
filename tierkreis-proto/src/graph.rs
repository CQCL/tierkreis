//! Conversions of core Tierkreis structures between [protobuf] and [core_graph] equivalents
//!
//! [protobuf]: super::protos_gen::v1alpha1::graph

use crate::ConvertError;
use indexmap::IndexMap;
use std::collections::{BTreeMap, HashMap};
use tierkreis_core::graph as core_graph;
use tierkreis_core::prelude::{TryFrom, TryInto};
use tierkreis_core::symbol as core_symbol;
use tierkreis_core::symbol::{Label, TypeVar};

pub use super::protos_gen::v1alpha1::graph::*;
fn convert_list(proto_list: VecValue) -> Result<core_graph::Value, ConvertError> {
    Ok(core_graph::Value::Vec(
        proto_list
            .vec
            .into_iter()
            .map(TryInto::try_into)
            .collect::<Result<Vec<_>, ConvertError>>()?,
    ))
}

impl From<core_symbol::Location> for Location {
    fn from(val: core_symbol::Location) -> Self {
        Location {
            location: val.0.into_iter().map(|x| x.to_string()).collect(),
        }
    }
}

impl TryFrom<Location> for core_symbol::Location {
    type Error = ConvertError;

    fn try_from(value: Location) -> Result<Self, Self::Error> {
        let x: Result<Vec<_>, _> = value.location.into_iter().map(TryInto::try_into).collect();
        Ok(core_symbol::Location(x?))
    }
}

impl TryFrom<Value> for core_graph::Value {
    type Error = ConvertError;

    fn try_from(value: Value) -> Result<Self, Self::Error> {
        match value.value {
            Some(value::Value::Graph(graph)) => {
                Ok(core_graph::Value::Graph(TryInto::try_into(graph)?))
            }
            Some(value::Value::Struct(struc)) => Ok(core_graph::Value::Struct(
                struc
                    .map
                    .into_iter()
                    .map(|(k, v)| Ok((TryInto::try_into(k)?, TryInto::try_into(v)?)))
                    .collect::<Result<HashMap<_, _>, Self::Error>>()?,
            )),
            Some(value::Value::Integer(n)) => Ok(core_graph::Value::Int(n)),
            Some(value::Value::Boolean(b)) => Ok(core_graph::Value::Bool(b)),
            Some(value::Value::Str(s)) => Ok(core_graph::Value::Str(s)),
            Some(value::Value::Flt(f)) => Ok(core_graph::Value::Float(f)),
            Some(value::Value::Pair(pair)) => Ok(core_graph::Value::Pair(Box::new((
                TryInto::try_into(*pair.first.unwrap())?,
                TryInto::try_into(*pair.second.unwrap())?,
            )))),
            Some(value::Value::Map(MapValue { pairs })) => Ok(core_graph::Value::Map(
                pairs
                    .into_iter()
                    .map(|pair| {
                        (
                            TryInto::try_into(*pair.first.unwrap()).unwrap(),
                            TryInto::try_into(*pair.second.unwrap()).unwrap(),
                        )
                    })
                    .collect::<HashMap<core_graph::Value, core_graph::Value>>(),
            )),
            Some(value::Value::Vec(proto_list)) => convert_list(proto_list),
            Some(value::Value::Variant(variant)) => {
                let tag = TryInto::try_into(variant.tag)?;
                let value = Box::new(TryInto::try_into(
                    *variant.value.ok_or(ConvertError::ProtoError)?,
                )?);
                Ok(core_graph::Value::Variant(tag, value))
            }
            None => Err(ConvertError::ProtoError),
        }
    }
}

impl From<core_graph::Value> for Value {
    fn from(value: core_graph::Value) -> Self {
        match value {
            core_graph::Value::Graph(graph) => Value {
                value: Some(value::Value::Graph(graph.into())),
            },
            core_graph::Value::Int(n) => Value {
                value: Some(value::Value::Integer(n)),
            },
            core_graph::Value::Bool(b) => Value {
                value: Some(value::Value::Boolean(b)),
            },
            core_graph::Value::Str(s) => Value {
                value: Some(value::Value::Str(s)),
            },
            core_graph::Value::Float(f) => Value {
                value: Some(value::Value::Flt(f)),
            },
            core_graph::Value::Pair(pair) => Value {
                value: Some(value::Value::Pair(Box::new(PairValue {
                    first: Some(Box::new(pair.0.into())),
                    second: Some(Box::new(pair.1.into())),
                }))),
            },
            core_graph::Value::Map(map) => Value {
                value: Some(value::Value::Map(MapValue {
                    pairs: map
                        .into_iter()
                        .map(|(k, v)| PairValue {
                            first: Some(Box::new(k.into())),
                            second: Some(Box::new(v.into())),
                        })
                        .collect(),
                })),
            },
            core_graph::Value::Vec(core_list) => Value {
                value: Some(value::Value::Vec(VecValue {
                    vec: core_list.into_iter().map(Into::into).collect(),
                })),
            },
            core_graph::Value::Struct(fields) => Value {
                value: Some(value::Value::Struct(StructValue {
                    map: fields
                        .into_iter()
                        .map(|(k, v)| (k.to_string(), v.into()))
                        .collect(),
                })),
            },
            core_graph::Value::Variant(tag, value) => Value {
                value: Some(value::Value::Variant(Box::new(VariantValue {
                    tag: tag.to_string(),
                    value: Some(Box::new((*value).into())),
                }))),
            },
        }
    }
}

impl From<HashMap<Label, core_graph::Value>> for StructValue {
    fn from(struc: HashMap<Label, core_graph::Value>) -> Self {
        StructValue {
            map: struc
                .into_iter()
                .map(|(k, v)| (k.to_string(), v.into()))
                .collect(),
        }
    }
}

impl TryFrom<StructValue> for HashMap<Label, core_graph::Value> {
    type Error = ConvertError;

    fn try_from(value_map: StructValue) -> Result<Self, Self::Error> {
        value_map
            .map
            .into_iter()
            .map(|(k, v)| Ok((TryInto::try_into(k)?, TryInto::try_into(v)?)))
            .collect::<Result<_, Self::Error>>()
    }
}

impl TryFrom<FunctionName> for core_symbol::FunctionName {
    type Error = ConvertError;

    fn try_from(function_name: FunctionName) -> Result<Self, Self::Error> {
        Ok(core_symbol::FunctionName {
            prefixes: function_name
                .namespaces
                .into_iter()
                .map(TryInto::try_into)
                .collect::<Result<_, _>>()?,
            name: TryInto::try_into(function_name.name)?,
        })
    }
}

impl TryFrom<Node> for core_graph::Node {
    type Error = ConvertError;

    fn try_from(node: Node) -> Result<Self, Self::Error> {
        let node = node.node.ok_or(ConvertError::ProtoError)?;

        let node = match node {
            node::Node::Input(Empty {}) => core_graph::Node::Input,
            node::Node::Output(Empty {}) => core_graph::Node::Output,
            node::Node::Const(value) => core_graph::Node::Const(TryInto::try_into(value)?),
            node::Node::Box(box_node) => core_graph::Node::Box(
                TryInto::try_into(box_node.loc.ok_or(ConvertError::ProtoError)?)?,
                TryInto::try_into(box_node.graph.ok_or(ConvertError::ProtoError)?)?,
            ),
            node::Node::Function(function) => core_graph::Node::Function(
                TryInto::try_into(function.name.ok_or(ConvertError::ProtoError)?)?,
                function.retry_secs,
            ),
            node::Node::Match(Empty {}) => core_graph::Node::Match,
            node::Node::Tag(tag) => core_graph::Node::Tag(TryInto::try_into(tag)?),
        };

        Ok(node)
    }
}

impl TryFrom<Type> for core_graph::Type {
    type Error = ConvertError;

    fn try_from(type_message: Type) -> Result<Self, Self::Error> {
        use r#type::Type;

        let out_type = match type_message.r#type.ok_or(ConvertError::ProtoError)? {
            Type::Bool(Empty {}) => core_graph::Type::Bool,
            Type::Int(Empty {}) => core_graph::Type::Int,
            Type::Str(Empty {}) => core_graph::Type::Str,
            Type::Flt(Empty {}) => core_graph::Type::Float,
            Type::Pair(pair) => {
                let first = TryInto::try_into(*pair.first.ok_or(ConvertError::ProtoError)?)?;
                let second = TryInto::try_into(*pair.second.ok_or(ConvertError::ProtoError)?)?;
                core_graph::Type::Pair(Box::new(first), Box::new(second))
            }
            Type::Map(pair) => {
                let first = TryInto::try_into(*pair.first.ok_or(ConvertError::ProtoError)?)?;
                let second = TryInto::try_into(*pair.second.ok_or(ConvertError::ProtoError)?)?;
                core_graph::Type::Map(Box::new(first), Box::new(second))
            }
            Type::Vec(element) => {
                let element = TryInto::try_into(*element)?;
                core_graph::Type::Vec(Box::new(element))
            }
            Type::Graph(graph) => {
                let inputs = TryInto::try_into(graph.inputs.ok_or(ConvertError::ProtoError)?)?;
                let outputs = TryInto::try_into(graph.outputs.ok_or(ConvertError::ProtoError)?)?;

                core_graph::Type::Graph(core_graph::GraphType { inputs, outputs })
            }
            Type::Var(name) => core_graph::Type::Var(TryInto::try_into(name)?),
            Type::Row(row) => core_graph::Type::Row(TryInto::try_into(row)?),
            Type::Struct(StructType { shape, name_opt }) => core_graph::Type::Struct(
                TryInto::try_into(shape.ok_or(ConvertError::ProtoError)?)?,
                name_opt.map(|struct_type::NameOpt::Name(name)| name),
            ),
            Type::Variant(row) => {
                let row = TryInto::try_into(row)?;
                core_graph::Type::Variant(row)
            }
        };

        Ok(out_type)
    }
}

impl From<core_graph::Type> for Type {
    fn from(typ: core_graph::Type) -> Self {
        use r#type::Type;

        let typ = match typ {
            core_graph::Type::Bool => Type::Bool(Empty {}),
            core_graph::Type::Int => Type::Int(Empty {}),
            core_graph::Type::Str => Type::Str(Empty {}),
            core_graph::Type::Float => Type::Flt(Empty {}),
            core_graph::Type::Pair(first, second) => {
                let first = Some(Box::new((*first).into()));
                let second = Some(Box::new((*second).into()));
                Type::Pair(Box::new(PairType { first, second }))
            }
            core_graph::Type::Map(first, second) => {
                let first = Some(Box::new((*first).into()));
                let second = Some(Box::new((*second).into()));
                Type::Map(Box::new(PairType { first, second }))
            }
            core_graph::Type::Vec(element) => {
                let element = Box::new((*element).into());
                Type::Vec(element)
            }
            core_graph::Type::Graph(graph) => {
                let inputs = Some(graph.inputs.into());
                let outputs = Some(graph.outputs.into());
                Type::Graph(GraphType { inputs, outputs })
            }
            core_graph::Type::Var(name) => Type::Var(name.to_string()),
            core_graph::Type::Row(row) => Type::Row(row.into()),
            core_graph::Type::Struct(row, name) => Type::Struct(StructType {
                shape: Some(row.into()),
                name_opt: name.map(struct_type::NameOpt::Name),
            }),
            core_graph::Type::Variant(row) => {
                let row = row.into();
                Type::Variant(row)
            }
        };

        self::Type { r#type: Some(typ) }
    }
}

impl TryFrom<RowType> for core_graph::RowType {
    type Error = ConvertError;

    fn try_from(row: RowType) -> Result<Self, Self::Error> {
        let rest = if row.rest.is_empty() {
            None
        } else {
            Some(TryInto::try_into(row.rest)?)
        };

        let content = row
            .content
            .into_iter()
            .map(|(label, typ)| Ok((TryInto::try_into(label)?, TryInto::try_into(typ)?)))
            .collect::<Result<BTreeMap<Label, core_graph::Type>, Self::Error>>()?;

        Ok(core_graph::RowType { content, rest })
    }
}

impl From<core_graph::RowType> for RowType {
    fn from(row: core_graph::RowType) -> Self {
        let content = row
            .content
            .into_iter()
            .map(|(label, typ)| (label.to_string(), typ.into()))
            .collect();
        let rest = row.rest.map(|var| var.to_string()).unwrap_or_default();
        RowType { content, rest }
    }
}

impl TryFrom<Edge> for core_graph::Edge {
    type Error = ConvertError;

    fn try_from(edge_weight: Edge) -> Result<Self, Self::Error> {
        Ok(core_graph::Edge {
            source: TryInto::try_into((edge_weight.node_from, edge_weight.port_from))?,
            target: TryInto::try_into((edge_weight.node_to, edge_weight.port_to))?,
            edge_type: match edge_weight.edge_type {
                Some(edge_type) => Some(TryInto::try_into(edge_type)?),
                None => None,
            },
        })
    }
}

impl TryFrom<Graph> for core_graph::Graph {
    type Error = ConvertError;

    fn try_from(proto_graph: Graph) -> Result<Self, Self::Error> {
        // TODO: add a new method for constructing graphs and use it
        // once we have a better idea of what graph serialisation
        // looks like.

        let mut builder = core_graph::GraphBuilder::new();

        for node in proto_graph.nodes {
            let node: core_graph::Node = TryInto::try_into(node)?;
            if !matches!(node, core_graph::Node::Input | core_graph::Node::Output) {
                builder.add_node(node)?;
            }
        }

        for edge in proto_graph.edges {
            let edge: core_graph::Edge = TryInto::try_into(edge)?;
            builder.add_edge(edge.source, edge.target, edge.edge_type)?;
        }
        builder.set_name(proto_graph.name);
        let [io, oo] = [proto_graph.input_order, proto_graph.output_order].map(|v| {
            v.into_iter()
                .map(TryInto::try_into)
                .collect::<Result<Vec<_>, _>>()
        });
        let io_order = [io?, oo?];
        builder.set_io_order(io_order);
        Ok(builder.build()?)
    }
}

impl From<core_symbol::FunctionName> for FunctionName {
    fn from(function_name: core_symbol::FunctionName) -> Self {
        FunctionName {
            namespaces: function_name
                .prefixes
                .iter()
                .map(|n| n.to_string())
                .collect(),
            name: function_name.name.to_string(),
        }
    }
}

impl From<core_graph::Node> for Node {
    fn from(node: core_graph::Node) -> Self {
        let node = match node {
            core_graph::Node::Input => node::Node::Input(Empty {}),
            core_graph::Node::Output => node::Node::Output(Empty {}),
            core_graph::Node::Const(value) => node::Node::Const(value.into()),
            core_graph::Node::Box(loc, graph) => node::Node::Box(BoxNode {
                loc: Some(loc.into()),
                graph: Some(graph.into()),
            }),
            core_graph::Node::Function(function, retry_secs) => {
                node::Node::Function(FunctionNode {
                    name: Some(function.into()),
                    retry_secs,
                })
            }
            core_graph::Node::Match => node::Node::Match(Empty {}),
            core_graph::Node::Tag(tag) => node::Node::Tag(tag.to_string()),
        };
        Node { node: Some(node) }
    }
}

impl From<core_graph::Graph> for Graph {
    fn from(graph: core_graph::Graph) -> Self {
        Graph {
            nodes: graph.nodes().cloned().map(Into::into).collect(),
            edges: graph
                .edges()
                .map(|edge| Edge {
                    port_from: edge.source.port.to_string(),
                    port_to: edge.target.port.to_string(),
                    node_from: edge.source.node.index() as u32,
                    node_to: edge.target.node.index() as u32,
                    edge_type: edge.edge_type.clone().map(Into::into),
                })
                .collect(),
            name: graph.name().clone(),
            input_order: graph.inputs().map(|l| l.to_string()).collect(),
            output_order: graph.outputs().map(|l| l.to_string()).collect(),
        }
    }
}

impl From<core_graph::Constraint> for Constraint {
    fn from(constraint: core_graph::Constraint) -> Self {
        let constraint = match constraint {
            core_graph::Constraint::Lacks { row, label } => {
                constraint::Constraint::Lacks(LacksConstraint {
                    row: Some(row.into()),
                    label: label.to_string(),
                })
            }
            core_graph::Constraint::Partition { left, right, union } => {
                constraint::Constraint::Partition(PartitionConstraint {
                    left: Some(left.into()),
                    right: Some(right.into()),
                    union: Some(union.into()),
                })
            }
        };

        Constraint {
            constraint: Some(constraint),
        }
    }
}

impl TryFrom<Constraint> for core_graph::Constraint {
    type Error = ConvertError;

    fn try_from(constraint: Constraint) -> Result<Self, Self::Error> {
        let constraint = constraint.constraint.ok_or(ConvertError::ProtoError)?;

        match constraint {
            constraint::Constraint::Lacks(lacks) => Ok(core_graph::Constraint::Lacks {
                row: TryInto::try_into(lacks.row.ok_or(ConvertError::ProtoError)?)?,
                label: TryInto::try_into(lacks.label)?,
            }),
            constraint::Constraint::Partition(partition) => Ok(core_graph::Constraint::Partition {
                left: TryInto::try_into(partition.left.ok_or(ConvertError::ProtoError)?)?,
                right: TryInto::try_into(partition.right.ok_or(ConvertError::ProtoError)?)?,
                union: TryInto::try_into(partition.union.ok_or(ConvertError::ProtoError)?)?,
            }),
        }
    }
}

impl From<core_graph::Kind> for Kind {
    fn from(kind: core_graph::Kind) -> Self {
        let kind = match kind {
            core_graph::Kind::Star => kind::Kind::Star(Empty {}),
            core_graph::Kind::Row => kind::Kind::Row(Empty {}),
        };

        Kind { kind: Some(kind) }
    }
}

impl TryFrom<Kind> for core_graph::Kind {
    type Error = ConvertError;

    fn try_from(kind: Kind) -> Result<Self, Self::Error> {
        Ok(match kind.kind.ok_or(ConvertError::ProtoError)? {
            kind::Kind::Star(Empty {}) => core_graph::Kind::Star,
            kind::Kind::Row(Empty {}) => core_graph::Kind::Row,
        })
    }
}

impl From<(TypeVar, core_graph::Kind)> for TypeSchemeVar {
    fn from((name, kind): (TypeVar, core_graph::Kind)) -> Self {
        TypeSchemeVar {
            name: name.to_string(),
            kind: Some(kind.into()),
        }
    }
}

impl TryFrom<TypeSchemeVar> for (TypeVar, core_graph::Kind) {
    type Error = ConvertError;

    fn try_from(var: TypeSchemeVar) -> Result<Self, Self::Error> {
        let name = TryInto::try_into(var.name)?;
        let kind = TryInto::try_into(var.kind.ok_or(ConvertError::ProtoError)?)?;
        Ok((name, kind))
    }
}

impl From<core_graph::TypeScheme> for TypeScheme {
    fn from(scheme: core_graph::TypeScheme) -> Self {
        let variables = scheme
            .variables
            .iter()
            .map(|(var, kind)| (*var, *kind).into())
            .collect();

        let constraints = scheme
            .constraints
            .iter()
            .map(|constraint| constraint.clone().into())
            .collect();

        let body = Some(scheme.body.into());

        TypeScheme {
            variables,
            constraints,
            body,
        }
    }
}

impl TryFrom<TypeScheme> for core_graph::TypeScheme {
    type Error = ConvertError;

    fn try_from(scheme: TypeScheme) -> Result<Self, Self::Error> {
        let variables = scheme
            .variables
            .into_iter()
            .map(TryInto::try_into)
            .collect::<Result<IndexMap<_, _>, Self::Error>>()?;

        let constraints = scheme
            .constraints
            .into_iter()
            .map(TryInto::try_into)
            .collect::<Result<Vec<_>, Self::Error>>()?;

        let body = TryInto::try_into(scheme.body.ok_or(ConvertError::ProtoError)?)?;

        Ok(core_graph::TypeScheme {
            variables,
            constraints,
            body,
        })
    }
}
