output "proxy_url" {
  description = "Access URL for the FastAPI Gemini Proxy"
  value       = "http://localhost:${var.proxy_port}"
}

output "prometheus_ui" {
  description = "Access URL for the Prometheus Monitoring Dashboard"
  value       = "http://localhost:${var.prometheus_port}"
}