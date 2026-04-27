variable "do_token" {
  type        = string
  description = "DigitalOcean API token"
  sensitive   = true
}

variable "project_name" {
  type        = string
  description = "Project identifier"
  default     = "connect-core"
}

variable "ssh_key_fingerprints" {
  type        = list(string)
  description = "SSH key fingerprints already added to DigitalOcean"
  default     = []
}

variable "control_node_name" {
  type    = string
  default = "connect-control-1"
}

variable "control_node_region" {
  type    = string
  default = "lon1"
}

variable "control_node_size" {
  type    = string
  default = "s-1vcpu-2gb"
}

variable "control_node_image" {
  type    = string
  default = "ubuntu-24-04-x64"
}

variable "worker_node_name" {
  type    = string
  default = "connect-worker-uk-1"
}

variable "worker_node_region" {
  type    = string
  default = "lon1"
}

variable "worker_node_size" {
  type    = string
  default = "s-1vcpu-1gb"
}

variable "worker_node_image" {
  type    = string
  default = "ubuntu-24-04-x64"
}

variable "allowed_admin_cidrs" {
  type        = list(string)
  description = "CIDRs allowed for SSH and admin endpoints"
  default     = ["0.0.0.0/0", "::/0"]
}
