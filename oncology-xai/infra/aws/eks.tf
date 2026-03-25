module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "${local.name}-eks"
  cluster_version = "1.29"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  enable_cluster_creator_admin_permissions = true

  cluster_addons = {
    coredns    = { most_recent = true }
    kube-proxy = { most_recent = true }
    vpc-cni    = { most_recent = true }
  }

  eks_managed_node_groups = {
    cpu = {
      name           = "cpu-nodes"
      instance_types = [var.eks_cpu_instance]
      min_size       = var.eks_cpu_min
      max_size       = var.eks_cpu_max
      desired_size   = var.eks_cpu_min

      labels = {
        workload = "general"
      }
    }

    gpu = {
      name           = "gpu-nodes"
      instance_types = [var.eks_gpu_instance]
      min_size       = var.eks_gpu_min
      max_size       = var.eks_gpu_max
      desired_size   = var.eks_gpu_min

      ami_type = "AL2_x86_64_GPU"

      capacity_type = "SPOT"

      labels = {
        workload    = "gpu"
        "nvidia.com/gpu" = "true"
      }

      taints = [{
        key    = "nvidia.com/gpu"
        value  = "true"
        effect = "NO_SCHEDULE"
      }]
    }
  }
}

resource "aws_eks_addon" "nvidia_device_plugin" {
  cluster_name = module.eks.cluster_name
  addon_name   = "nvidia-device-plugin"
  depends_on   = [module.eks]
}
