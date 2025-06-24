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

resource "docker_image" "tkr_visualization" {
  name         = "tkr_visualization"
  force_remove = true
  build {
    builder    = "default"
    tag        = ["tkr_visualization:9"]
    context    = "${path.cwd}/../../../tierkreis"
    dockerfile = "${path.cwd}/../../../tierkreis/tierkreis_visualization/Dockerfile"
  }
}


resource "kubernetes_persistent_volume_claim" "tierkreis_directory_claim" {
  metadata {
    name      = "tierkreis-persistent-volume-claim"
    namespace = "tierkreis-kueue"
  }
  spec {
    access_modes = ["ReadWriteMany"]
    resources { requests = { "storage" = "1Gi" } }
  }
}

module "kqueue" {
  source = "../kqueue"
}

resource "kubernetes_service" "visualizer" {
  metadata {
    name = "visualizer"
  }
  spec {
    selector = { app = kubernetes_pod.visualizer.metadata.0.labels.app }
    port { port = 800 }
  }
}

resource "kubernetes_pod" "visualizer" {
  metadata {
    name   = "visualizer"
    labels = { app = "TKRVisualizer" }
  }
  spec {
    container {
      image = docker_image.tkr_visualization.image_id
      name  = "tkr-visualization"
    }
  }
}
