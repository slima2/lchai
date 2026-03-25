variable "project" {
  default = "lchai"
}

variable "environment" {
  default = "prod"
}

variable "region" {
  default = "us-east-1"
}

variable "domain_name" {
  description = "Domain for the application (e.g., lchai.example.com)"
  type        = string
}

variable "db_password" {
  description = "RDS PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for LLM explanations"
  type        = string
  sensitive   = true
  default     = ""
}

variable "eks_cpu_instance" {
  default = "t3.xlarge"
}

variable "eks_cpu_min" {
  default = 2
}

variable "eks_cpu_max" {
  default = 4
}

variable "eks_gpu_instance" {
  default = "g4dn.xlarge"
}

variable "eks_gpu_min" {
  default = 0
}

variable "eks_gpu_max" {
  default = 1
}

variable "rds_instance" {
  default = "db.t3.medium"
}

variable "redis_instance" {
  default = "cache.t3.micro"
}
