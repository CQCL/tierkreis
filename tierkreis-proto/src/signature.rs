//! Crate versions of structs in [ListFunctions] with conversion routines.
//!
//! [ListFunctions]: crate::protos_gen::v1alpha1::signature::signature_server::Signature::list_functions
use crate::ConvertError;
use std::collections::HashMap;
use std::collections::HashSet;
use tierkreis_core::graph as core_graph;
use tierkreis_core::namespace as core_namespace;
use tierkreis_core::prelude::{TryFrom, TryInto};
use tierkreis_core::type_checker as core_tc;

use crate::protos_gen::v1alpha1::signature::*;
impl From<core_namespace::FunctionDeclaration> for FunctionDeclaration {
    fn from(entry: core_namespace::FunctionDeclaration) -> Self {
        Self {
            type_scheme: Some(entry.type_scheme.into()),
            description: entry.description,
            input_order: entry
                .input_order
                .into_iter()
                .map(|k| k.to_string())
                .collect(),
            output_order: entry
                .output_order
                .into_iter()
                .map(|k| k.to_string())
                .collect(),
        }
    }
}

impl TryFrom<FunctionDeclaration> for core_namespace::FunctionDeclaration {
    type Error = ConvertError;

    fn try_from(entry: FunctionDeclaration) -> Result<Self, Self::Error> {
        Ok(Self {
            type_scheme: TryInto::try_into(entry.type_scheme.ok_or(ConvertError::ProtoError)?)?,
            description: entry.description,
            input_order: entry
                .input_order
                .into_iter()
                .map(TryInto::try_into)
                .collect::<Result<Vec<_>, _>>()?,
            output_order: entry
                .output_order
                .into_iter()
                .map(TryInto::try_into)
                .collect::<Result<Vec<_>, _>>()?,
        })
    }
}

impl From<core_namespace::NamespaceItem> for NamespaceItem {
    fn from(val: core_namespace::NamespaceItem) -> Self {
        NamespaceItem {
            decl: Some(val.decl.into()),
            locations: val.locations.into_iter().map(|x| x.into()).collect(),
        }
    }
}

impl TryFrom<NamespaceItem> for core_namespace::NamespaceItem {
    type Error = ConvertError;

    fn try_from(value: NamespaceItem) -> Result<Self, Self::Error> {
        Ok(core_namespace::NamespaceItem {
            decl: TryInto::try_into(value.decl.ok_or(ConvertError::ProtoError)?)?,
            locations: value
                .locations
                .into_iter()
                .map(TryInto::try_into)
                .collect::<Result<Vec<_>, _>>()?,
        })
    }
}

impl From<core_namespace::Namespace<core_namespace::NamespaceItem>> for Namespace {
    fn from(contents: core_namespace::Namespace<core_namespace::NamespaceItem>) -> Self {
        Self {
            functions: contents
                .functions
                .into_iter()
                .map(|(name, entry)| (name.to_string(), entry.into()))
                .collect(),
            subspaces: contents
                .subspaces
                .into_iter()
                .map(|(name, ns)| (name.to_string(), ns.into()))
                .collect(),
        }
    }
}

impl TryFrom<Namespace> for core_namespace::Namespace<core_namespace::NamespaceItem> {
    type Error = ConvertError;

    fn try_from(ns: Namespace) -> Result<Self, Self::Error> {
        Ok(Self {
            functions: ns
                .functions
                .into_iter()
                .map(|(name, entry)| Ok((TryInto::try_into(name)?, TryInto::try_into(entry)?)))
                .collect::<Result<_, ConvertError>>()?,
            subspaces: ns
                .subspaces
                .into_iter()
                .map(|(name, ns)| Ok((TryInto::try_into(name)?, TryInto::try_into(ns)?)))
                .collect::<Result<_, ConvertError>>()?,
        })
    }
}

impl From<core_namespace::Signature> for ListFunctionsResponse {
    fn from(core_resp: core_namespace::Signature) -> Self {
        Self {
            root: Some(core_resp.root.into()),
            aliases: core_resp
                .aliases
                .into_iter()
                .map(|(name, type_)| (name, type_.into()))
                .collect(),
            scopes: core_resp.scopes.into_iter().map(Into::into).collect(),
        }
    }
}

impl TryFrom<ListFunctionsResponse> for core_namespace::Signature {
    type Error = ConvertError;

    fn try_from(value: ListFunctionsResponse) -> Result<Self, Self::Error> {
        let root = TryInto::try_into(value.root.ok_or(ConvertError::ProtoError)?)?;
        let aliases = value
            .aliases
            .into_iter()
            .map(|(name, type_)| Ok((name, TryInto::try_into(type_)?)))
            .collect::<Result<HashMap<String, core_graph::TypeScheme>, Self::Error>>()?;
        let scopes = value
            .scopes
            .into_iter()
            .map(TryInto::try_into)
            .collect::<Result<HashSet<_>, _>>()?;

        Ok(Self {
            root,
            aliases,
            scopes,
        })
    }
}

impl From<core_tc::TypeErrors> for TypeErrors {
    fn from(errors: core_tc::TypeErrors) -> Self {
        Self {
            errors: errors.errors().map(|error| error.clone().into()).collect(),
        }
    }
}

impl From<core_tc::Location> for GraphLocation {
    fn from(loc: core_tc::Location) -> Self {
        use crate::graph;
        use core_tc::Location as cl;
        use graph_location::Location::*;
        GraphLocation {
            location: Some(match loc {
                cl::VecIndex(idx) => VecIndex(idx as u32),
                cl::FunctionNode(idx, _)
                | cl::BoxNode(idx)
                | cl::ConstNode(idx)
                | cl::MatchNode(idx)
                | cl::TagNode(idx) => NodeIdx(idx.index() as u32),
                cl::GraphEdge(source, target) => Edge(graph::Edge {
                    port_from: source.port.to_string(),
                    port_to: target.port.to_string(),
                    node_from: source.node.index() as u32,
                    node_to: target.node.index() as u32,
                    edge_type: None,
                }),
                cl::InputNode => Input(Empty {}),
                cl::OutputNode => Output(Empty {}),
                cl::StructField(field) => StructField(field.to_string()),
                cl::PairFirst => PairFirst(Empty {}),
                cl::PairSecond => PairSecond(Empty {}),
                cl::MapKey => MapKey(Empty {}),
                cl::MapValue => MapValue(Empty {}),
                cl::InputValue(input) => InputValue(input.to_string()),
            }),
        }
    }
}

impl From<core_tc::TypeError> for TierkreisTypeError {
    fn from(error: core_tc::TypeError) -> Self {
        use error_variant::Error::*;
        Self {
            location: error
                .context()
                .iter()
                .map(|loc| loc.clone().into())
                .collect(),
            variant: Some(ErrorVariant {
                error: Some(match error {
                    core_tc::TypeError::Unify {
                        expected,
                        found,
                        context: _,
                    } => Unify(UnifyError {
                        expected: Some(expected.into()),
                        found: Some(found.into()),
                    }),
                    core_tc::TypeError::UnknownFunction {
                        function,
                        context: _,
                    } => UnknownFunction(function.into()),
                    core_tc::TypeError::UnknownTypeVar {
                        variable,
                        type_scheme,
                        context: _,
                    } => UnknownTypeVar(TypeVarError {
                        variable: Some(
                            (variable, *type_scheme.variables.get(&variable).unwrap()).into(),
                        ),
                        type_scheme: Some(type_scheme.into()),
                    }),
                    core_tc::TypeError::Kind { .. } => Kind(error.to_string()),
                    core_tc::TypeError::Bound { .. } => Bound(error.to_string()),
                }),
            }),
        }
    }
}
