//! PyO3 module to call Tierkreis (Rust) type-checker from Python

#![allow(clippy::borrow_deref_ref)]

use prost::Message;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use tierkreis_core::builtins;
use tierkreis_core::namespace::{Namespace, NamespaceItem};
use tierkreis_core::prelude::TryInto;
use tierkreis_core::type_checker::{GraphWithInputs, Signature, Typeable};
use tierkreis_proto::protos_gen::v1alpha1::signature as ps;
use tierkreis_proto::ConvertError;

fn infer2(req: &PyBytes) -> Result<ps::infer_graph_types_response::Response, ConvertError> {
    let req =
        ps::InferGraphTypesRequest::decode(req.as_bytes()).map_err(|_| ConvertError::ProtoError)?;
    let gwi = req.gwi.ok_or(ConvertError::ProtoError)?;
    let graph = TryInto::try_into(gwi.graph.ok_or(ConvertError::ProtoError)?)?;
    // The client can pass signatures (inc builtins) from a running server if desired.
    let nmspc: Namespace<NamespaceItem> =
        TryInto::try_into(req.functions.ok_or(ConvertError::ProtoError)?)?;
    let sigs: Signature = nmspc.map(|x| x.decl.type_scheme);

    if let Some(sv) = gwi.inputs {
        let gwi = GraphWithInputs {
            graph,
            inputs: TryInto::try_into(sv)?,
        };
        Ok(match gwi.infer_type(&sigs) {
            Ok((_, typed_gwi)) => {
                ps::infer_graph_types_response::Response::Success(ps::GraphWithInputs {
                    graph: Some(typed_gwi.graph.into()),
                    inputs: Some(typed_gwi.inputs.into()),
                })
            }
            Err(errors) => ps::infer_graph_types_response::Response::Error(errors.into()),
        })
    } else {
        Ok(match graph.infer_type(&sigs) {
            Ok((_, typed_graph)) => {
                ps::infer_graph_types_response::Response::Success(ps::GraphWithInputs {
                    graph: Some(typed_graph.into()),
                    inputs: None,
                })
            }
            Err(errors) => ps::infer_graph_types_response::Response::Error(errors.into()),
        })
    }
}

#[pyfunction]
fn infer_graph_types(py: Python, req: &PyBytes) -> PyObject {
    // either a protobuf Graph, for success;
    // or a protobuf'd TypeErrors, for failure
    let res = ps::InferGraphTypesResponse {
        response: infer2(req).ok(),
    };

    // serialize protobuf response into python
    PyBytes::new(py, res.encode_to_vec().as_slice()).to_object(py)
}

#[pyfunction]
fn builtin_namespace(py: Python) -> PyObject {
    let res: ps::Namespace = builtins::namespace()
        .map(|x| NamespaceItem {
            decl: x,
            locations: vec![],
        })
        .into();

    PyBytes::new(py, res.encode_to_vec().as_slice()).to_object(py)
}

#[pymodule]
fn tierkreis_typecheck(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(infer_graph_types, m)?)?;
    m.add_function(wrap_pyfunction!(builtin_namespace, m)?)?;

    Ok(())
}
