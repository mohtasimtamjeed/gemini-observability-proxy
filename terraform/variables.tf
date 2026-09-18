variable "gemini_api_key" {
  description = "Google Gemini API key required for LLM generation"
  type        = string
  sensitive   = true # Prevents the key from being printed in plain text during terraform plan/apply
}

variable "default_model" {
  description = "Default Gemini model targeted by the gateway"
  type        = string
  default     = "gemini-3.6-flash"
}

variable "proxy_port" {
  description = "Host port mapped to the FastAPI gateway"
  type        = number
  default     = 8000
}

variable "prometheus_port" {
  description = "Host port mapped to the Prometheus Web UI & API"
  type        = number
  default     = 9090
}