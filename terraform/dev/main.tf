terraform {
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.37.1"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "3.0.0-pre2"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.6.1"
    }
  }
}

provider "kubernetes" {
  config_path    = "~/.kube/config"
  config_context = "docker-desktop"
}
provider "helm" {
  kubernetes = { config_path = "~/.kube/config" }
}
provider "docker" {}

resource "docker_image" "tkr_builtins" {
  name         = "tkr_builtins"
  force_remove = true
  build {
    builder    = "default"
    tag        = ["tkr_builtins:4"]
    context    = "${path.cwd}/../../../tierkreis/tierkreis"
    dockerfile = "${path.cwd}/../../../tierkreis/tierkreis/tierkreis/controller/builtins/Dockerfile"
  }
}

module "kqueue" {
  source = "../kqueue"
}
