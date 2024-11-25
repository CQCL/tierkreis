//! Crate versions of graph protobufs, plus [GraphBuilder]
use super::portgraph::graph::{ConnectError, Direction};
use crate::prelude::{TryFrom, TryInto};
use crate::symbol::{FunctionName, Label, Location, SymbolError, TypeVar};
use indexmap::{IndexMap, IndexSet};

use std::collections::{BTreeMap, HashMap, HashSet};
use std::convert::Infallible;
use std::hash::{Hash, Hasher};
use thiserror::Error;

pub use super::portgraph::graph::{EdgeIndex, NodeIndex};

/// A value that can be passed around a Tierkreis graph.
/// A strict (no optional fields), crate version of protobuf `tierkreis.v1alpha.graph.Value`.
#[derive(Clone, Debug)]
pub enum Value {
    /// Boolean value (true or false)
    Bool(bool),
    /// Signed integer
    Int(i64),
    /// String
    Str(String),
    /// Double-precision (64-bit) float
    Float(f64),
    /// A Tierkreis graph
    Graph(Graph),
    /// A pair of two other [Value]s
    Pair(Box<(Value, Value)>),
    /// A map from keys to values. Keys must be hashable, i.e. must not be or contain
    /// [Value::Graph], [Value::Map], [Value::Struct] or [Value::Float].
    Map(HashMap<Value, Value>),
    /// List of [Value]s.
    Vec(Vec<Value>),
    /// A struct or record type with string-named fields (themselves [Value]s)
    Struct(HashMap<Label, Value>),
    /// A [Value] tagged with a string to make a disjoint union of component types
    Variant(Label, Box<Value>),
}

impl PartialEq for Value {
    fn eq(&self, other: &Value) -> bool {
        match (self, other) {
            (Value::Bool(x), Value::Bool(y)) => x == y,
            (Value::Int(x), Value::Int(y)) => x == y,
            (Value::Str(x), Value::Str(y)) => x == y,
            (Value::Float(x), Value::Float(y)) => x == y,
            (Value::Pair(x), Value::Pair(y)) => x == y,
            (Value::Map(x), Value::Map(y)) => x == y,
            (Value::Struct(f1), Value::Struct(f2)) => f1 == f2,
            (Value::Vec(ar1), Value::Vec(ar2)) => ar1 == ar2,
            (Value::Graph(x), Value::Graph(y)) => x == y,
            (Value::Variant(t1, v1), Value::Variant(t2, v2)) => (t1 == t2) && (v1 == v2),
            _ => false,
        }
    }
}

// Required since we use Value's as the *keys* of HashMap's
impl Eq for Value {}

impl Hash for Value {
    fn hash<H: Hasher>(&self, state: &mut H) {
        match self {
            Value::Graph(_) | Value::Map(_) | Value::Struct(_) | Value::Float(_) => {
                panic!("Value is not hashable: {:?}", self)
            }
            Value::Bool(x) => x.hash(state),
            Value::Int(x) => x.hash(state),
            Value::Str(x) => x.hash(state),
            Value::Pair(x) => x.hash(state),
            Value::Vec(x) => x.hash(state),
            Value::Variant(tag, value) => {
                tag.hash(state);
                value.hash(state);
            }
        }
    }
}

/// Crate version of protobuf `tierkreis.v1alpha1.graph.Type`.
/// A type of values (or [Row](Type::Row)s) that can be passed around a Tierkreis [Graph].
#[derive(Clone, PartialEq, Eq, Hash)]
pub enum Type {
    /// Type ([Kind::Star]) of Booleans, i.e. with two values `true` and `false`
    Bool,
    /// Type ([Kind::Star]) of signed integers
    Int,
    /// Type ([Kind::Star]) of strings
    Str,
    /// Type ([Kind::Star]) of floating-point numbers (double-precision)
    Float,
    /// Type ([Kind::Star]) identifying the set of graphs with the specified
    /// row of named inputs and row of named outputs
    Graph(GraphType),
    /// Type ([Kind::Star]) of pairs (where the first value has one type, and
    /// the second another); each component must also be a [Kind::Star].
    Pair(Box<Type>, Box<Type>),
    /// Type ([Kind::Star]) of lists of elements all of the same type (given,
    /// also [Kind::Star]).
    Vec(Box<Type>),
    /// Type variable, used (in types) inside polymorphic [TypeScheme]s only.
    /// Can be a [Kind::Row] or a [Kind::Star].
    Var(TypeVar),
    /// A named row of types. Unlike the other variants (except possibly [Type::Var]),
    /// this is a ([Kind::Row])), *not* a type of values, so cannot be used as a member
    /// of any other [Type] (e.g. [Type::Pair], [Type::Vec]), or as the type of a field
    /// in a [RowType].
    /// However, can appear in [Constraint::Lacks::row] or [Constraint::Partition],
    /// and can be returned in [TypeError::Unify]
    ///
    /// [TypeError::Unify]: super::type_checker::TypeError::Unify
    Row(RowType),
    /// Type ([Kind::Star]) of maps from a key type to value type (both [Kind::Star]).
    // We do nothing to rule out key *types* that are not hashable, only values
    Map(Box<Type>, Box<Type>),
    /// Struct type (i.e. [Kind::Star]): made up of an unordered collection of named
    /// fields each with a type ([Kind::Star]). Optionally, the type itself may have
    /// a name.
    Struct(RowType, Option<String>),
    /// A disjoint (tagged) union of other types, given as a row.
    /// May be open, for the output of a Tag operation, or closed,
    /// for the input to match (where the handlers are known).
    Variant(RowType),
}

impl Type {
    /// Makes an unnamed [Type::Struct] given a row of fields
    pub fn struct_from_row(row: RowType) -> Self {
        Self::Struct(row, None)
    }
}

impl std::fmt::Debug for Type {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Type::Bool => f.debug_struct("Bool").finish(),
            Type::Int => f.debug_struct("Int").finish(),
            Type::Str => f.debug_struct("Str").finish(),
            Type::Float => f.debug_struct("Float").finish(),
            Type::Graph(graph) => std::fmt::Debug::fmt(graph, f),
            Type::Pair(first, second) => f.debug_tuple("Pair").field(first).field(second).finish(),
            Type::Vec(element) => f.debug_tuple("Vector").field(element).finish(),
            Type::Var(var) => std::fmt::Debug::fmt(var, f),
            Type::Row(row) => f.debug_tuple("Row").field(row).finish(),
            Type::Map(key, value) => f.debug_tuple("Map").field(key).field(value).finish(),
            Type::Struct(row, name) => match name {
                Some(name) => f.debug_struct(name).finish(),
                None => f.debug_tuple("Struct").field(row).finish(),
            },
            Type::Variant(row) => f.debug_tuple("Variant").field(row).finish(),
        }
    }
}

impl From<GraphType> for Type {
    fn from(t: GraphType) -> Self {
        Type::Graph(t)
    }
}

impl From<TypeVar> for Type {
    fn from(t: TypeVar) -> Self {
        Type::Var(t)
    }
}

impl Type {
    /// Iterator over the type variables in the type in the order they occur.
    /// Each variable is returned only once.
    pub fn type_vars(&self) -> impl Iterator<Item = TypeVar> + '_ {
        let mut vars = IndexSet::new();
        self.type_vars_impl(&mut vars);
        vars.into_iter()
    }

    fn type_vars_impl(&self, vars: &mut IndexSet<TypeVar>) {
        match self {
            Type::Bool => {}
            Type::Int => {}
            Type::Str => {}
            Type::Float => {}
            Type::Graph(graph) => {
                graph.type_vars_impl(vars);
            }
            Type::Pair(left, right) => {
                left.type_vars_impl(vars);
                right.type_vars_impl(vars);
            }
            Type::Vec(element) => {
                element.type_vars_impl(vars);
            }
            Type::Var(var) => {
                vars.insert(*var);
            }
            Type::Row(row) => {
                row.type_vars_impl(vars);
            }
            Type::Map(key, value) => {
                key.type_vars_impl(vars);
                value.type_vars_impl(vars);
            }
            Type::Struct(row, _) => {
                row.type_vars_impl(vars);
            }
            Type::Variant(row) => {
                row.type_vars_impl(vars);
            }
        }
    }
}

/// Type of a Graph, i.e. a higher-order function value, with input and output rows.
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct GraphType {
    /// The inputs to the graph (known and/or variable)
    pub inputs: RowType,
    /// The outputs from the graph (known and/or variable)
    pub outputs: RowType,
}

impl GraphType {
    /// Creates a new instance with closed empty input and output rows
    pub fn new() -> Self {
        Self {
            inputs: Default::default(),
            outputs: Default::default(),
        }
    }

    /// Adds a new input given a label and type
    pub fn add_input(&mut self, port: impl Into<Label>, type_: impl Into<Type>) {
        self.inputs.content.insert(port.into(), type_.into());
    }

    /// Adds a new output given a label and type
    pub fn add_output(&mut self, port: impl Into<Label>, type_: impl Into<Type>) {
        self.outputs.content.insert(port.into(), type_.into());
    }

    fn type_vars_impl(&self, vars: &mut IndexSet<TypeVar>) {
        self.inputs.type_vars_impl(vars);
        self.outputs.type_vars_impl(vars);
    }
}

impl Default for GraphType {
    fn default() -> Self {
        Self::new()
    }
}

impl std::fmt::Debug for GraphType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Graph")
            .field("inputs", &self.inputs)
            .field("outputs", &self.outputs)
            .finish()
    }
}

/// A row of named types, possibly including a variable for an unknown portion
#[derive(Clone, PartialEq, Eq, Hash, Default)]
pub struct RowType {
    /// Known labels, and types for each (of course these may contain variables)
    pub content: BTreeMap<Label, Type>,
    /// Either `Some` (of a variable whose [Kind] is [Kind::Row]), in which case
    /// the [RowType] is an "open row" that may contain any number of other fields;
    /// or `None` for a "closed row" i.e. exactly/only the fields in [Self::content]
    pub rest: Option<TypeVar>,
}

impl std::fmt::Debug for RowType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_map()
            .entries(self.content.iter())
            .entries(self.rest.iter().map(|rest| ("#", rest)))
            .finish()
    }
}

impl From<TypeVar> for RowType {
    fn from(var: TypeVar) -> Self {
        Self {
            content: BTreeMap::new(),
            rest: Some(var),
        }
    }
}

impl RowType {
    fn type_vars_impl(&self, vars: &mut IndexSet<TypeVar>) {
        for type_ in self.content.values() {
            type_.type_vars_impl(vars);
        }

        if let Some(var) = self.rest {
            vars.insert(var);
        }
    }
}

/// The kind of a type variable - i.e. whether the "type" variable stands for
/// a single type, or (some part of) a row.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Kind {
    /// A single type
    Star,
    /// A row of named types
    Row,
}

/// A polymorphic type scheme. Usually (but not necessarily) for a function.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypeScheme {
    /// Variables over which the scheme is polymorphic, each with its [Kind].
    /// A concrete type (usable for a port or edge) is obtained by supplying
    /// a type or row (according to the [Kind]) for each.
    pub variables: IndexMap<TypeVar, Kind>,
    /// Constraints restricting the legal instantiations of the [Self::variables]
    pub constraints: Vec<Constraint>,
    /// The body of the type scheme, i.e. potentially containing occurrences
    /// of the [Self::variables], into which values for the variables are
    /// substituted when the scheme is instantiated to a concrete type.
    pub body: Type,
}

impl TypeScheme {
    /// Adds (binds) a new variable of a given kind (destructive update)
    pub fn with_variable(mut self, var: impl Into<TypeVar>, kind: Kind) -> Self {
        self.variables.insert(var.into(), kind);
        self
    }

    /// Adds a new constraint (destructive update). This should refer (only) to
    /// variables bound by the scheme.
    pub fn with_constraint(mut self, constraint: impl Into<Constraint>) -> Self {
        self.constraints.push(constraint.into());
        self
    }
}

impl From<Type> for TypeScheme {
    fn from(type_: Type) -> Self {
        TypeScheme {
            variables: IndexMap::new(),
            constraints: Vec::new(),
            body: type_,
        }
    }
}

impl From<GraphType> for TypeScheme {
    fn from(graph_type: GraphType) -> Self {
        Type::Graph(graph_type).into()
    }
}

/// Specifies restrictions on the instantiations of type variables in a [TypeScheme]
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Constraint {
    /// A row must *not* have a specified label
    Lacks {
        /// Either a [Type::Row] or a [Type::Var] of [Kind::Row].
        row: Type,
        /// Field name that must not be present in [Self::Lacks::row].
        label: Label,
    },
    /// A row must be the union of two other rows (which for any label in common,
    /// must have [Type]s that can be made the same).
    Partition {
        /// One input to the union - a [Type::Row] or a [Type::Var] of [Kind::Row].
        left: Type,
        /// The other input to the union - a [Type::Row] or a [Type::Var] of [Kind::Row].
        right: Type,
        /// The result, i.e. left and right merged together.
        /// Could be a [Type::Row] or a [Type::Var] of [Kind::Row].
        union: Type,
    },
}

/// A node in a [`Graph`].
#[derive(Clone, Debug, PartialEq)]
pub enum Node {
    /// The node that emits a graph's input values.
    Input,

    /// The node that receives a graph's output values.
    Output,

    /// A node that emits a constant value.
    Const(Value),

    /// A subgraph embedded as a single node. The ports of the node are the ports of the embedded
    /// graph. Box nodes can be used to conveniently compose common subgraphs.
    /// The box will be run on the specified location.
    Box(Location, Graph),

    /// A node that executes a function with a specified name. The type and runtime behavior of a
    /// function node depend on the functions provided by the environment in which the graph is
    /// interpreted.
    Function(FunctionName, Option<u32>),

    /// Perform pattern matching on a variant type.
    Match,

    /// Create a variant. Tag(tag) :: forall T. T -> Variant[tag:T|...]
    Tag(Label),
}

impl Node {
    /// Does this node run something on a machine/process outside this runtime?
    pub fn is_external(&self) -> bool {
        match self {
            Node::Function(f, _) => !f.is_builtin(),
            Node::Box(l, _) => l != &Location::local(),
            _ => false,
        }
    }

    /// Makes a [Node::Box] that runs a given graph on the same runtime
    /// as is running the node's parent (i.e. at [Location::local])
    pub fn local_box(graph: Graph) -> Self {
        Node::Box(Location::local(), graph)
    }
}

/// Convert a [`Value`] into a constant node.
impl From<Value> for Node {
    fn from(value: Value) -> Self {
        Node::Const(value)
    }
}

impl TryFrom<Value> for Node {
    type Error = Infallible;

    fn try_from(value: Value) -> Result<Self, Self::Error> {
        Ok(value.into())
    }
}

/// Convert a [`Graph`] into a box node.
impl From<Graph> for Node {
    fn from(graph: Graph) -> Self {
        Node::local_box(graph)
    }
}

impl TryFrom<Graph> for Node {
    type Error = Infallible;

    fn try_from(graph: Graph) -> Result<Self, Self::Error> {
        Ok(graph.into())
    }
}

/// Convert a [`FunctionName`] into a function node, with default timeout
impl From<FunctionName> for Node {
    fn from(function: FunctionName) -> Self {
        Node::Function(function, None)
    }
}

impl TryFrom<FunctionName> for Node {
    type Error = Infallible;

    fn try_from(function: FunctionName) -> Result<Self, Self::Error> {
        Ok(function.into())
    }
}

/// Convert a [`FunctionName`] and timeout into a function node
impl From<(FunctionName, u32)> for Node {
    fn from(fn_t: (FunctionName, u32)) -> Self {
        Node::Function(fn_t.0, Some(fn_t.1))
    }
}

impl TryFrom<(FunctionName, u32)> for Node {
    type Error = Infallible;

    fn try_from(fn_t: (FunctionName, u32)) -> Result<Self, Self::Error> {
        Ok(fn_t.into())
    }
}

impl TryFrom<&str> for Node {
    type Error = SymbolError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        Ok(Node::Function(value.parse()?, None))
    }
}

impl TryFrom<(&str, u32)> for Node {
    type Error = SymbolError;

    fn try_from(value: (&str, u32)) -> Result<Self, Self::Error> {
        Ok(Node::Function(value.0.parse()?, Some(value.1)))
    }
}

/// An edge in a [`Graph`].
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Edge {
    /// Source (out-)port
    pub source: NodePort,
    /// Target/destination (in-)port
    pub target: NodePort,
    /// Explicit annotation of the type of the edge. May (optionally) be
    /// provided by the client; will be filled in by typechecking.
    pub edge_type: Option<Type>,
}

// uniquely identify a port in the graph by node and port of node
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
#[allow(missing_docs)]
pub struct NodePort {
    pub node: NodeIndex,
    pub port: Label,
}

impl std::fmt::Display for NodePort {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}:{}", self.node.index(), self.port)
    }
}

impl<N, P> From<(N, P)> for NodePort
where
    N: Into<NodeIndex>,
    P: Into<Label>,
{
    fn from((node, port): (N, P)) -> Self {
        Self {
            node: node.into(),
            port: port.into(),
        }
    }
}

impl<N, P> TryFrom<(N, P)> for NodePort
where
    N: Into<NodeIndex>,
    P: TryInto<Label>,
    <P as TryInto<Label>>::Error: Into<SymbolError>,
{
    type Error = SymbolError;

    fn try_from((node, port): (N, P)) -> Result<Self, Self::Error> {
        Ok(Self {
            node: node.into(),
            port: TryInto::try_into(port).map_err(|e| e.into())?,
        })
    }
}

/// Computation graph.
///
/// A computation graph is a directed acyclic port graph in which data flows along the edges and as
/// it is processed by the nodes.  Nodes in the graph are addressed by their unique names. The
/// inputs of the graph are emitted by a node named `input` and received by a node named `output`.
/// Each node has labelled input and output ports, encoded implicitly as the endpoints of the
/// graph's edges. The port labels are unique among a node's input and output ports individually,
/// but input and output ports with the same label are considered different. Any port in the graph
/// has exactly one edge connected to it. An edge can optionally be annotated with a type.
///
/// This type is immutable. The [`GraphBuilder`] can be used to construct new instances.
#[derive(Clone, Debug)]
pub struct Graph {
    internal_graph: super::portgraph::graph::Graph<Node, Edge>,
    name: String,
    input_order: Vec<Label>,
    output_order: Vec<Label>,
}

impl Graph {
    /// Gets the indices of the [Node::Input] node and [Node::Output] node.
    pub fn boundary() -> [NodeIndex; 2] {
        [NodeIndex::new(0), NodeIndex::new(1)]
    }

    /// Iterator over the node indices of the graph
    pub fn node_indices(&self) -> impl Iterator<Item = NodeIndex> + '_ {
        self.internal_graph.node_indices()
    }

    /// Iterator over the nodes of the graph
    pub fn nodes(&self) -> impl Iterator<Item = &Node> {
        self.internal_graph.node_weights()
    }

    /// Iterator over the edges of the graph.
    pub fn edges(&self) -> impl Iterator<Item = &Edge> {
        self.internal_graph.edge_weights()
    }

    /// Returns the node with the given index.
    pub fn node(&self, node: impl Into<NodeIndex>) -> Option<&Node> {
        self.internal_graph.node_weight(node.into())
    }

    /// Returns the edge connected to an input port of the graph.
    /// This is an output port of the unique input node.
    pub fn input<E>(&self, port: impl TryInto<Label, Error = E>) -> Option<&Edge>
    where
        E: Into<SymbolError>,
    {
        self.node_output((Self::boundary()[0], port))
    }

    /// Returns the edge connected to an output port of the graph.
    /// This is an input port of the unique output node.
    pub fn output<E>(&self, port: impl TryInto<Label, Error = E>) -> Option<&Edge>
    where
        E: Into<SymbolError>,
    {
        self.node_input((Self::boundary()[1], port))
    }

    /// Iterator over the input edges for a node.
    /// An empty iterator is returned when there is no node with the given index.
    pub fn node_inputs(&self, node: NodeIndex) -> impl Iterator<Item = &Edge> + '_ {
        self.internal_graph
            .node_edges(node, Direction::Incoming)
            .map(move |edge| {
                self.internal_graph
                    .edge_weight(edge)
                    .expect("missing edge.")
            })
    }

    /// Iterator over the output edges for a node.
    /// An empty iterator is returned when there is no node with the given index.
    pub fn node_outputs(&self, node: NodeIndex) -> impl Iterator<Item = &Edge> + '_ {
        self.internal_graph
            .node_edges(node, Direction::Outgoing)
            .map(move |edge| {
                self.internal_graph
                    .edge_weight(edge)
                    .expect("missing edge.")
            })
    }

    /// Returns the edge connected to a given input port.
    /// If the node or the edge does not exist `None` is returned.
    pub fn node_input(&self, port: impl TryInto<NodePort>) -> Option<&Edge> {
        let port = TryInto::try_into(port).ok()?;
        self.node_inputs(port.node)
            .find(|edge| edge.target.port == port.port)
    }

    /// Returns the edge connected to a given output port.
    /// If the node or the edge does not exist `None` is returned.
    pub fn node_output(&self, port: impl TryInto<NodePort>) -> Option<&Edge> {
        let port = TryInto::try_into(port).ok()?;
        self.node_outputs(port.node)
            .find(|edge| edge.source.port == port.port)
    }

    /// The name of the graph, provided by the creator.
    pub fn name(&self) -> &String {
        &self.name
    }

    /// Iterator over the labels of the input ports to the graph, in the
    /// order specified for debugging/display by [GraphBuilder::set_io_order].
    /// Equivalently, the out-ports of the [Node::Input].
    pub fn inputs(&self) -> impl Iterator<Item = &Label> {
        self.input_order.iter()
    }

    /// Iterator over the labels of the input ports to the graph, in the
    /// order specified for debugging/display by [GraphBuilder::set_io_order].
    /// Equivalently, the in-ports of the [Node::Output].
    pub fn outputs(&self) -> impl Iterator<Item = &Label> {
        self.output_order.iter()
    }
}

/// Graph builder to construct [`Graph`] instances.
pub struct GraphBuilder {
    graph: Graph,
}

impl GraphBuilder {
    /// Creates a new graph builder.
    /// The input and output nodes are created automatically.
    pub fn new() -> Self {
        let mut builder = GraphBuilder {
            graph: Graph {
                internal_graph: super::portgraph::graph::Graph::new(),
                name: "".into(),
                input_order: vec![],
                output_order: vec![],
            },
        };

        builder.add_node(Node::Input).unwrap();
        builder.add_node(Node::Output).unwrap();

        builder
    }

    /// Sets the name of the Graph being built
    pub fn set_name(&mut self, name: String) {
        self.graph.name = name;
    }

    /// Add a new node to the graph with a set of incoming and outgoing edges.
    /// Most efficient way to set edge orderings.
    ///
    /// # Errors
    ///
    /// * Attempting to create an additional input or output node.
    /// * Already connected edges
    pub fn add_node_with_edges<F>(
        &mut self,
        node: impl TryInto<Node, Error = F>,
        incoming: impl IntoIterator<Item = EdgeIndex>,
        outgoing: impl IntoIterator<Item = EdgeIndex>,
    ) -> Result<NodeIndex, GraphBuilderError>
    where
        F: Into<SymbolError>,
    {
        let node = TryInto::try_into(node).map_err(|e| GraphBuilderError::SymbolError(e.into()))?;

        Ok(self
            .graph
            .internal_graph
            .add_node_with_edges(node, incoming, outgoing)?)
    }

    /// Add a new node to the graph.
    ///
    /// # Errors
    ///
    /// * Attempting to create an additional input or output node.
    pub fn add_node<F>(
        &mut self,
        node: impl TryInto<Node, Error = F>,
    ) -> Result<NodeIndex, GraphBuilderError>
    where
        F: Into<SymbolError>,
    {
        self.add_node_with_edges(node, [], [])
    }

    /// Add a new edge to the graph connecting the given input and output ports.
    /// The edge can also be optionally annotated with a type.
    ///
    /// # Errors
    ///
    /// * The source or target node does not exist.
    /// * There already is an edge connected to the source or target port.
    ///
    /// This method does not fail in the case a cycle is introduced into the graph.
    /// The check of acyclicity is deferred to [`GraphBuilder::build`] which can
    /// check the entire graph at once in linear time.
    pub fn add_edge<E, F>(
        &mut self,
        source: impl TryInto<NodePort, Error = E>,
        target: impl TryInto<NodePort, Error = F>,
        edge_type: impl Into<Option<Type>>,
    ) -> Result<(), GraphBuilderError>
    where
        E: Into<SymbolError>,
        F: Into<SymbolError>,
    {
        let source =
            TryInto::try_into(source).map_err(|e| GraphBuilderError::SymbolError(e.into()))?;
        let target =
            TryInto::try_into(target).map_err(|e| GraphBuilderError::SymbolError(e.into()))?;
        let edge_type = edge_type.into();

        if self.graph.node_input(target).is_some() {
            return Err(GraphBuilderError::OccupiedInputPort(target));
        } else if self.graph.node_output(source).is_some() {
            return Err(GraphBuilderError::OccupiedOutputPort(source));
        }

        let edge = Edge {
            source,
            target,
            edge_type,
        };

        let eidx = self.graph.internal_graph.add_edge(edge);

        self.graph
            .internal_graph
            .connect(source.node, eidx, Direction::Outgoing, None)?;
        self.graph
            .internal_graph
            .connect(target.node, eidx, Direction::Incoming, None)?;

        Ok(())
    }

    fn is_acyclic(&self) -> bool {
        let mut stack: Vec<_> = self.graph.node_indices().collect();
        let mut discovered = HashSet::new();
        let mut finished = HashSet::new();

        while let Some(node) = stack.pop() {
            if !discovered.insert(node) {
                finished.insert(node);
                continue;
            }

            stack.push(node);

            for edge in self.graph.node_outputs(node) {
                let target = edge.target.node;
                if !discovered.contains(&target) {
                    stack.push(target);
                } else if !finished.contains(&target) {
                    return false;
                }
            }
        }

        true
    }

    /// Construct the finished graph.
    ///
    /// # Errors
    ///
    /// This method fails if there is a cycle in the graph.
    pub fn build(self) -> Result<Graph, GraphBuilderError> {
        if !self.is_acyclic() {
            return Err(GraphBuilderError::CyclicGraph);
        }

        Ok(self.graph)
    }

    /// Sets the order of inputs, and of outputs, for debugging/display.
    /// (Replaces any previously-provided order.)
    pub fn set_io_order(&mut self, io_order: [Vec<Label>; 2]) {
        let [i, o] = io_order;
        self.graph.input_order = i;
        self.graph.output_order = o;
    }
}

impl Default for GraphBuilder {
    fn default() -> Self {
        Self::new()
    }
}

/// Error in building a graph with a [GraphBuilder]
#[derive(Debug, Error)]
pub enum GraphBuilderError {
    /// Tried to add an edge to a in-port that already has an incoming edge.
    #[error("there already is an edge at the input port '{0}'")]
    OccupiedInputPort(NodePort),
    /// Tried to add an edge from an out-port that already has an outgoing edge.
    #[error("there already is an edge at the output port '{0}'")]
    OccupiedOutputPort(NodePort),
    /// The edges (dependencies) in a Graph contained a cycle
    #[error("the graph must be acyclic")]
    CyclicGraph,
    /// An error in a (supposed) qualified name
    #[error("encountered error importing symbols: {0}")]
    SymbolError(#[from] SymbolError),
    /// Error from [super::portgraph] library that edge could not be added,
    /// e.g. if the source or target node-indices do not exist.
    #[error("Error when connecting edges.")]
    ConnectError(#[from] ConnectError),
}

impl PartialEq for Graph {
    fn eq(&self, other: &Self) -> bool {
        if self.name != other.name {
            return false;
        }
        // Compare nodes
        let our_nodes: Vec<&Node> = self.nodes().collect();
        let other_nodes: Vec<&Node> = other.nodes().collect();

        if our_nodes != other_nodes {
            return false;
        }

        // Compare edges
        let our_edges: HashSet<&Edge> = self.edges().collect();
        let other_edges: HashSet<&Edge> = other.edges().collect();

        our_edges == other_edges
    }
}

#[cfg(test)]
mod test {
    use crate::graph::{Graph, GraphBuilder, GraphBuilderError};
    use std::error::Error;

    /// Test that graphs with a cycle between different nodes can not be constructed. The graph constructed
    /// in this test is a partial trace on the value bit of a two cnot gates wired in sequence.
    #[test]
    fn test_cyclic_graph() -> Result<(), Box<dyn Error>> {
        let mut builder = GraphBuilder::new();
        let [i, o] = Graph::boundary();
        let a = builder.add_node("cnot")?;
        let b = builder.add_node("cnot")?;

        builder.add_edge((i, "control"), (a, "control"), None)?;
        builder.add_edge((a, "control"), (b, "control"), None)?;
        builder.add_edge((a, "value"), (b, "value"), None)?;
        builder.add_edge((b, "control"), (o, "control"), None)?;
        builder.add_edge((b, "value"), (a, "value"), None)?;

        assert!(matches!(
            builder.build(),
            Err(GraphBuilderError::CyclicGraph)
        ));

        Ok(())
    }

    /// Test that graphs with a cycle on a node are rejected. The graph constructed in this test is
    /// a partial trace on the value bit of a cnot gate.
    #[test]
    fn test_cycle() -> Result<(), Box<dyn Error>> {
        let mut builder = GraphBuilder::new();

        let [i, o] = Graph::boundary();
        let a = builder.add_node("cnot")?;
        builder.add_edge((i, "control"), (a, "control"), None)?;
        builder.add_edge((a, "control"), (o, "control"), None)?;
        builder.add_edge((a, "value"), (a, "value"), None)?;

        assert!(matches!(
            builder.build(),
            Err(GraphBuilderError::CyclicGraph)
        ));

        Ok(())
    }

    /// Test that doubled edges at an input port are rejected.
    #[test]
    fn test_duplicate_node_input() -> Result<(), Box<dyn Error>> {
        let mut builder = GraphBuilder::new();
        let [i, _] = Graph::boundary();

        let d = builder.add_node("discard")?;
        builder.add_edge((i, "a"), (d, "value"), None)?;
        let result = builder.add_edge((i, "b"), (d, "value"), None);

        assert!(matches!(
            result,
            Err(GraphBuilderError::OccupiedInputPort(_))
        ));

        Ok(())
    }
}
