# Run this ONCE per AWS account (management, log-archive, audit,
# network-hub, and each workload account) before applying any real
# environments/*/ stack in that account.
#
# It creates the S3 bucket + DynamoDB lock table that account's Terraform
# state will live in. This stack intentionally has NO remote backend of
# its own — it's what CREATES the backend, so it can't depend on one
# existing yet (the usual chicken-and-egg with Terraform state storage).
# Its own local terraform.tfstate only tracks two simple, easy-to-recreate
# resources; it isn't the state you need to worry about losing. Every
# other stack in environments/ is what actually needs durable state, and
# this is what gives them somewhere durable to put it.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "tfstate" {
  bucket = var.state_bucket_name
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled" # every past state version stays recoverable, incl. right before a destroy
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket                  = aws_s3_bucket.tfstate.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms" # AWS-managed aws/s3 key — state files can contain sensitive attributes
    }
    bucket_key_enabled = true
  }
}

# Locking prevents two people (or a person and the UI) from running
# apply/destroy against the same environment at the same time and
# corrupting state.
resource "aws_dynamodb_table" "locks" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
