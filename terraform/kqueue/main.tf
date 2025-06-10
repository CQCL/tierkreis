resource "kubernetes_namespace" "tierkreis_kueue" {
  metadata {
    name        = "tierkreis-kueue"
    annotations = { name = "tierkreis-kueue" }
  }
}

resource "kubernetes_manifest" "cpu_resource_flavor" {
  manifest = {
    apiVersion = "kueue.x-k8s.io/v1beta1"
    kind       = "ResourceFlavor"
    metadata   = { name = "cpu" }
  }
}

resource "kubernetes_manifest" "cluster_queue" {
  manifest = {

    "apiVersion" = "kueue.x-k8s.io/v1beta1"
    "kind"       = "ClusterQueue"
    "metadata"   = { "name" = "cluster-queue" }
    "spec" = {
      "namespaceSelector" = {}
      "resourceGroups" = [
        {
          "coveredResources" = ["cpu", "memory", "pods"]
          "flavors" = [
            {
              "name" = "default-flavor"
              "resources" = [
                {
                  "name"         = "cpu"
                  "nominalQuota" = 2
                },
                {
                  "name"         = "memory"
                  "nominalQuota" = "1Gi"
                },
                {
                  "name"         = "pods"
                  "nominalQuota" = 5
                },
              ]
            },
          ]
        },
      ]
    }
  }
}

resource "kubernetes_manifest" "local_queue" {
  manifest = {
    "apiVersion" = "kueue.x-k8s.io/v1beta1"
    "kind"       = "LocalQueue"
    "metadata" = {
      "name"      = "tierkreis-queue"
      "namespace" = kubernetes_namespace.tierkreis_kueue.metadata[0].name
    }
    "spec" = { "clusterQueue" = "cluster-queue" }
  }
}
