use std::collections::{HashMap, HashSet};

use indexmap::{IndexMap, IndexSet};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyDict, PyIterator, PyType},
};
use pythonize::{depythonize, pythonize};
use serde::{Deserialize, Serialize};

// #[pyclass(eq, str, frozen)]
// #[derive(PartialEq, Eq, Hash, Clone)]
// pub struct PortID(pub String);

// impl std::fmt::Display for PortID {
//     fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
//         write!(f, "PortID({})", self.0)?;
//         Ok(())
//     }
// }

// impl From<String> for PortID {
//     fn from(value: String) -> Self {
//         Self(value)
//     }
// }

// impl From<&str> for PortID {
//     fn from(value: &str) -> Self {
//         Self(value.to_string())
//     }
// }
//
type PortID = String;

#[pyclass(eq, str, frozen)]
#[derive(Clone, PartialEq, Serialize, Deserialize)]
pub struct NodeIndex(pub usize);

impl std::fmt::Display for NodeIndex {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "NodeIndex({})", self.0)?;
        Ok(())
    }
}

#[pymethods]
impl NodeIndex {
    #[new]
    pub fn new(val: usize) -> Self {
        Self(val)
    }
}

/// A reference to a potential value.
#[pyclass(eq, str, frozen, generic)]
#[derive(Clone, PartialEq, Serialize, Deserialize)]
pub struct ValueRef(pub usize, pub String);

impl std::fmt::Display for ValueRef {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ValueRef({}, '{}')", self.0, self.1)?;
        Ok(())
    }
}

#[pymethods]
impl ValueRef {
    #[new]
    pub fn new(node_index: NodeIndex, port_id: PortID) -> Self {
        Self(node_index.0, port_id)
    }

    #[getter]
    pub fn node_index(&self) -> NodeIndex {
        NodeIndex(self.0)
    }

    #[getter]
    pub fn port_id(&self) -> PortID {
        self.1.clone()
    }

    pub fn __iter__<'py>(&self, py: Python<'py>) -> Bound<'py, PyIterator> {
        PyIterator::from_object(
            &(NodeIndex(self.0), self.1.clone())
                .into_pyobject(py)
                .unwrap(),
        )
        .unwrap()
    }
}

#[derive(Clone, PartialEq, Serialize, Deserialize)]
pub enum NodeDef {
    Func {
        name: String,
        inputs: IndexMap<PortID, ValueRef>,
    },
    Eval {
        body: ValueRef,
        inputs: IndexMap<PortID, ValueRef>,
    },
    Loop {
        body: ValueRef,
        inputs: IndexMap<PortID, ValueRef>,
        continue_port: PortID,
    },
    Map {
        body: ValueRef,
        inputs: IndexMap<PortID, ValueRef>,
    },
    Const {
        value: Value,
    },
    IfElse {
        pred: ValueRef,
        if_true: ValueRef,
        if_false: ValueRef,
    },
    EagerIfElse {
        pred: ValueRef,
        if_true: ValueRef,
        if_false: ValueRef,
    },
    Input {
        name: String,
    },
    Output {
        inputs: IndexMap<PortID, ValueRef>,
    },
}

#[derive(Clone, PartialEq, Serialize, Deserialize, FromPyObject)]
pub enum Value {
    Bool(bool),
    Int(usize),
    Float(f64),
    Str(String),
    List(Vec<Value>),
    Map(HashMap<String, Value>),
    Bytes(Vec<u8>),
    Graph(GraphData),
}

#[pyclass]
pub struct CurriedNodeIndex {
    node_index: NodeIndex,
}

#[pymethods]
impl CurriedNodeIndex {
    fn __call__(&self, port: PortID) -> ValueRef {
        ValueRef(self.node_index.0, port)
    }
}

#[pyclass(eq)]
#[derive(Default, Serialize, Deserialize, Clone, PartialEq)]
pub struct GraphData {
    // First argument is the node definition, followed
    // by a set of which of the output ports have been
    // connected to other ports.
    //
    // TODO: swap this out for portgraph?
    nodes: Vec<(NodeDef, IndexSet<PortID>)>,
    fixed_inputs: IndexMap<PortID, ()>,
    graph_inputs: IndexSet<PortID>,
    graph_outputs: Option<NodeIndex>,
}

#[pymethods]
impl GraphData {
    #[new]
    pub fn new() -> Result<Self, pyo3::PyErr> {
        Ok(Self {
            ..Default::default()
        })
    }

    #[getter]
    pub fn fixed_inputs(&self) -> IndexMap<PortID, ()> {
        self.fixed_inputs.clone()
    }

    // TODO: This isn't a getter for some reason
    pub fn output_idx(&self) -> Option<NodeIndex> {
        self.graph_outputs.clone()
    }

    pub fn input(&mut self, name: &str) -> ValueRef {
        let idx = self.add_node(NodeDef::Input {
            name: name.to_string(),
        });
        self.graph_inputs.insert(name.to_string());

        ValueRef(idx, name.to_string())
    }

    pub fn r#const(&mut self, value: Value) -> ValueRef {
        let idx = self.add_node(NodeDef::Const { value });

        ValueRef(idx, "value".to_string())
    }

    pub fn func(
        &mut self,
        function_name: &str,
        inputs: IndexMap<PortID, ValueRef>,
    ) -> CurriedNodeIndex {
        self.connect_inputs(&inputs);

        let idx = self.add_node(NodeDef::Func {
            name: function_name.to_string(),
            inputs: inputs.into_iter().collect(),
        });

        CurriedNodeIndex {
            node_index: NodeIndex(idx),
        }
    }

    pub fn eval(
        &mut self,
        graph: ValueRef,
        inputs: IndexMap<PortID, ValueRef>,
    ) -> CurriedNodeIndex {
        self.connect_inputs(&inputs);

        let idx = self.add_node(NodeDef::Eval {
            body: graph,
            inputs: inputs.into_iter().collect(),
        });

        CurriedNodeIndex {
            node_index: NodeIndex(idx),
        }
    }

    pub fn r#loop(
        &mut self,
        graph: ValueRef,
        inputs: IndexMap<PortID, ValueRef>,
        continue_port: PortID,
    ) -> CurriedNodeIndex {
        self.connect_inputs(&inputs);

        let idx = self.add_node(NodeDef::Loop {
            body: graph,
            inputs: inputs.into_iter().collect(),
            continue_port,
        });

        CurriedNodeIndex {
            node_index: NodeIndex(idx),
        }
    }

    pub fn map(&mut self, graph: ValueRef, inputs: IndexMap<PortID, ValueRef>) -> CurriedNodeIndex {
        self.connect_inputs(&inputs);

        let idx = self.add_node(NodeDef::Map {
            body: graph,
            inputs: inputs.into_iter().collect(),
        });

        CurriedNodeIndex {
            node_index: NodeIndex(idx),
        }
    }

    pub fn if_else(
        &mut self,
        pred: ValueRef,
        if_true: ValueRef,
        if_false: ValueRef,
    ) -> CurriedNodeIndex {
        let idx = self.add_node(NodeDef::IfElse {
            pred: pred.clone(),
            if_true: if_true.clone(),
            if_false: if_false.clone(),
        });

        self.nodes[pred.0].1.insert(pred.1.clone());
        self.nodes[if_true.0].1.insert(if_false.1.clone());
        self.nodes[if_false.0].1.insert(if_false.1.clone());

        CurriedNodeIndex {
            node_index: NodeIndex(idx),
        }
    }

    pub fn eager_if_else(
        &mut self,
        pred: ValueRef,
        if_true: ValueRef,
        if_false: ValueRef,
    ) -> CurriedNodeIndex {
        let idx = self.add_node(NodeDef::IfElse {
            pred: pred.clone(),
            if_true: if_true.clone(),
            if_false: if_false.clone(),
        });

        self.nodes[pred.0].1.insert(pred.1.clone());
        self.nodes[if_true.0].1.insert(if_false.1.clone());
        self.nodes[if_false.0].1.insert(if_false.1.clone());

        CurriedNodeIndex {
            node_index: NodeIndex(idx),
        }
    }

    pub fn output(&mut self, inputs: IndexMap<PortID, ValueRef>) -> PyResult<()> {
        if self.graph_outputs.is_some() {
            return Err(PyValueError::new_err("Output already set"));
        }
        self.connect_inputs(&inputs);

        let idx = self.add_node(NodeDef::Output {
            inputs: inputs.into_iter().collect(),
        });
        self.graph_outputs = Some(NodeIndex(idx));

        Ok(())
    }

    pub fn remaining_inputs(&self, provided_inputs: HashSet<PortID>) -> HashSet<PortID> {
        let fixed_inputs: HashSet<PortID> = self.fixed_inputs.keys().cloned().collect();
        if fixed_inputs.intersection(&provided_inputs).next().is_some() {
            panic!();
        }

        let actual_inputs: IndexSet<PortID> =
            fixed_inputs.union(&provided_inputs).cloned().collect();
        self.graph_inputs
            .difference(&actual_inputs)
            .cloned()
            .collect()
    }

    pub fn to_dict<'py>(&self, py: Python<'py>) -> Bound<'py, PyDict> {
        pythonize(py, self).unwrap().extract().unwrap()
    }

    #[classmethod]
    pub fn from_dict(_cls: &Bound<'_, PyType>, obj: Bound<PyDict>) -> Self {
        dbg!("{:?}", &obj);
        depythonize(&obj).unwrap()
    }

    pub fn model_dump_json(&self) -> String {
        serde_json::to_string(self).unwrap()
    }

    #[classmethod]
    pub fn model_load_json(_cls: &Bound<'_, PyType>, s: &str) -> Self {
        serde_json::from_str(s).unwrap()
    }
}

impl GraphData {
    fn connect_inputs(&mut self, inputs: &IndexMap<PortID, ValueRef>) {
        for (_, ValueRef(idx, port)) in inputs {
            self.nodes[*idx].1.insert(port.clone());
        }
    }

    fn add_node(&mut self, node: NodeDef) -> usize {
        // Nodes are 0-indexed.
        let node_index = self.nodes.len();
        self.nodes.push((node, IndexSet::new()));
        node_index
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn tierkreis_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NodeIndex>()?;
    m.add_class::<ValueRef>()?;
    m.add_class::<GraphData>()?;
    Ok(())
}
