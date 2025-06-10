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

resource "helm_release" "kueue" {
  name       = "kueue"
  repository = "oci://registry.k8s.io/kueue/charts"
  chart      = "kueue"

  version          = "0.12.2"
  namespace        = "kueue-system"
  create_namespace = true
}

