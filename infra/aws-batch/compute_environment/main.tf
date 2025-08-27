# Roles
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_instance_role" {
  name               = "ecs_instance_role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_role" {
  name = "ecs_instance_role"
  role = aws_iam_role.ecs_instance_role.name
}

data "aws_iam_policy_document" "batch_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["batch.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "aws_batch_service_role" {
  name               = "aws_batch_service_role"
  assume_role_policy = data.aws_iam_policy_document.batch_assume_role.json
}

resource "aws_iam_role_policy_attachment" "aws_batch_service_role" {
  role       = aws_iam_role.aws_batch_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"
}

# Base infra

resource "aws_vpc" "tierkreis" {
  tags       = { Name = "tierkreis" }
  cidr_block = "10.1.0.0/16"
}

resource "aws_security_group" "tierkreis" {
  tags   = { Name = "tierkreis" }
  name   = "aws_batch_compute_environment_security_group"
  vpc_id = aws_vpc.tierkreis.id
}

resource "aws_subnet" "tierkreis" {
  tags       = { Name = "tierkreis" }
  vpc_id     = aws_vpc.tierkreis.id
  cidr_block = "10.1.1.0/24"
}

resource "aws_placement_group" "tierkreis" {
  tags     = { Name = "tierkreis" }
  name     = "tierkreis"
  strategy = "cluster"
}

resource "aws_batch_compute_environment" "tierkreis" {
  name = "tierkreis"

  compute_resources {
    type = "EC2"

    instance_role = aws_iam_instance_profile.ecs_instance_role.arn

    instance_type = ["m1.small"]

    max_vcpus = 16
    min_vcpus = 0

    placement_group    = aws_placement_group.tierkreis.name
    security_group_ids = [aws_security_group.tierkreis.id]
    subnets            = [aws_subnet.tierkreis.id]
  }

  service_role = aws_iam_role.aws_batch_service_role.arn
  type         = "MANAGED"
  depends_on   = [aws_iam_role_policy_attachment.aws_batch_service_role]
}

# resource "aws_batch_job_queue" "tierkreis" {
#   name     = "tierkreis"
#   state    = "ENABLED"
#   priority = 1

#   compute_environment_order {
#     order               = 1
#     compute_environment = aws_batch_compute_environment.tierkreis.arn
#   }
# }
