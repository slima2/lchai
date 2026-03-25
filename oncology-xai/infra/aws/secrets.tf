resource "aws_secretsmanager_secret" "app_secrets" {
  name = "${local.name}/app-secrets"
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    POSTGRES_PASSWORD = var.db_password
    OPENAI_API_KEY    = var.openai_api_key
    S3_ACCESS_KEY     = "use-irsa"
    S3_SECRET_KEY     = "use-irsa"
  })
}
