terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.6.1"
    }
  }
}

resource "docker_image" "tkr_pytket_worker" {
  name         = "tkr_pytket_worker"
  force_remove = true
  build {
    builder    = "default"
    tag        = ["tkr_pytket_worker:4"]
    context    = "${path.cwd}/../../"
    dockerfile = "${path.cwd}/../../tierkreis_workers/pytket_worker/Dockerfile"
  }
}

resource "docker_image" "tkr_controller" {
  name         = "tkr_controller"
  force_remove = true
  build {
    builder    = "default"
    tag        = ["tkr_controller:4"]
    context    = "${path.cwd}/../../"
    dockerfile = "${path.cwd}/../../tierkreis/tiekreis"
  }
}
