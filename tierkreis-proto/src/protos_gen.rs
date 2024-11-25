//! Code generated from tierkreis protobuf definitions
#![allow(clippy::all)]
/// Code-generated from `tierkreis/v1alpha` protobufs
pub mod v1alpha1 {
    /// Code-generated from `tierkreis/v1alpha/runtime.proto`
    pub mod runtime {
        include!(concat!(env!("OUT_DIR"), "/tierkreis.v1alpha1.runtime.rs"));
    }

    /// Code-generated from `tierkreis/v1alpha/jobs.proto` (Nexus internal)
    #[allow(missing_docs)]
    pub mod jobs {
        include!(concat!(env!("OUT_DIR"), "/tierkreis.v1alpha1.jobs.rs"));
    }

    /// Code-generated from `tierkreis/v1alpha/graph.proto`
    pub mod graph {
        include!(concat!(env!("OUT_DIR"), "/tierkreis.v1alpha1.graph.rs"));
    }

    /// Code-generated from `tierkreis/v1alpha/worker.proto`
    pub mod worker {
        include!(concat!(env!("OUT_DIR"), "/tierkreis.v1alpha1.worker.rs"));
    }

    /// Code-generated from `tierkreis/v1alpha/signature.proto`
    pub mod signature {
        include!(concat!(env!("OUT_DIR"), "/tierkreis.v1alpha1.signature.rs"));
    }

    /// Code-generated from `tierkreis/v1alpha/controller`
    #[allow(missing_docs)]
    pub mod controller {
        include!(concat!(
            env!("OUT_DIR"),
            "/tierkreis.v1alpha1.controller.rs"
        ));
    }
}
