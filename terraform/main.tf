# ==========================================
# 1. Network: Isolated Bridge for Internal DNS
# ==========================================
resource "docker_network" "proxy_network" {
  name   = "gemini_proxy_network"
  driver = "bridge"
}

# ==========================================
# 2. Images: References to Local & Remote Images
# ==========================================
# Points to the image built locally in Phase 4
resource "docker_image" "proxy_image" {
  name         = "gemini-proxy:v1"
  keep_locally = true
}

# Pulls the official Prometheus image
resource "docker_image" "prometheus_image" {
  name         = "prom/prometheus:v2.54.1"
  keep_locally = true
}

# ==========================================
# 3. Gateway Container: FastAPI Proxy
# ==========================================
resource "docker_container" "gemini_proxy" {
  name  = "gemini-proxy"
  image = docker_image.proxy_image.image_id

  env = [
    "GEMINI_API_KEY=${var.gemini_api_key}",
    "DEFAULT_MODEL=${var.default_model}",
    "PORT=${var.proxy_port}"
  ]

  ports {
    internal = 8000
    external = var.proxy_port
  }

  networks_advanced {
    name = docker_network.proxy_network.name
  }

  restart = "unless-stopped"
}

# ==========================================
# 4. Observability Container: Prometheus
# ==========================================
resource "docker_container" "prometheus" {
  name  = "prometheus"
  image = docker_image.prometheus_image.image_id

  ports {
    internal = 9090
    external = var.prometheus_port
  }

  # Mount prometheus.yml into the container read-only
  volumes {
    host_path      = abspath("${path.module}/../prometheus.yml")
    container_path = "/etc/prometheus/prometheus.yml"
    read_only      = true
  }

  command = [
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus"
  ]

  networks_advanced {
    name = docker_network.proxy_network.name
  }

  # Explicit dependency ensures network and gateway are available
  depends_on = [
    docker_container.gemini_proxy
  ]

  restart = "unless-stopped"
}