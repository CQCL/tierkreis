terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.10.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.6.1"
    }
  }
}

provider "aws" {}
provider "docker" {}

module "compute_environment" {
  source = "./compute_environment"
}


# module "jobs" {
#   source = "./jobs"
# }
