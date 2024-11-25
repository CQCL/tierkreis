//! Custom build script to generate Rust code from protobuf definitions

fn main() -> std::io::Result<()> {
    println!("cargo:rerun-if-changed=./protos");

    tonic_build::configure()
        .protoc_arg("--experimental_allow_proto3_optional")
        .compile_protos(
            &[
                "./protos/v1alpha1/graph.proto",
                "./protos/v1alpha1/worker.proto",
                "./protos/v1alpha1/runtime.proto",
                "./protos/v1alpha1/jobs.proto",
                "./protos/v1alpha1/signature.proto",
                "./protos/v1alpha1/controller/runtime_storage_api.proto",
                "./protos/v1alpha1/controller/tierkreis.proto",
            ],
            &["./protos/"],
        )
}
