use crate::protos_gen::v1alpha1::worker::*;
use std::collections::HashMap;
use tierkreis_core::graph::Value;
use tierkreis_core::symbol::Label;

impl From<HashMap<Label, Value>> for RunFunctionResponse {
    fn from(outputs: HashMap<Label, Value>) -> Self {
        RunFunctionResponse {
            outputs: Some(outputs.into()),
        }
    }
}
