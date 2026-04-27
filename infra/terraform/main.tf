provider "digitalocean" {
  token = var.do_token
}

locals {
  common_tags = [var.project_name, "connect", "core"]
}

resource "digitalocean_droplet" "control" {
  name      = var.control_node_name
  region    = var.control_node_region
  size      = var.control_node_size
  image     = var.control_node_image
  ssh_keys  = var.ssh_key_fingerprints
  monitoring = true
  tags      = concat(local.common_tags, ["role:control"])
}

resource "digitalocean_droplet" "worker_uk" {
  name      = var.worker_node_name
  region    = var.worker_node_region
  size      = var.worker_node_size
  image     = var.worker_node_image
  ssh_keys  = var.ssh_key_fingerprints
  monitoring = true
  tags      = concat(local.common_tags, ["role:worker", "country:gb"])
}

resource "digitalocean_firewall" "control" {
  name = "${var.project_name}-control-fw"

  droplet_ids = [digitalocean_droplet.control.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.allowed_admin_cidrs
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_firewall" "worker_uk" {
  name = "${var.project_name}-worker-uk-fw"

  droplet_ids = [digitalocean_droplet.worker_uk.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = var.allowed_admin_cidrs
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

output "control_node" {
  value = {
    id        = digitalocean_droplet.control.id
    name      = digitalocean_droplet.control.name
    public_ip = digitalocean_droplet.control.ipv4_address
    region    = digitalocean_droplet.control.region
  }
}

output "worker_node" {
  value = {
    id        = digitalocean_droplet.worker_uk.id
    name      = digitalocean_droplet.worker_uk.name
    public_ip = digitalocean_droplet.worker_uk.ipv4_address
    region    = digitalocean_droplet.worker_uk.region
  }
}

output "ansible_inventory" {
  value = {
    control = {
      (digitalocean_droplet.control.name) = {
        ansible_host = digitalocean_droplet.control.ipv4_address
        ansible_user = "root"
      }
    }
    workers_uk = {
      (digitalocean_droplet.worker_uk.name) = {
        ansible_host = digitalocean_droplet.worker_uk.ipv4_address
        ansible_user = "root"
      }
    }
  }
}
