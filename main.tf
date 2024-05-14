provider "google" {
  credentials = file("keys/traffic-pulse-c501f1eccb68.json")
  project     = "traffic-pulse"
  region      = "us-east1"
}

resource "google_sql_database_instance" "postgres_instance" {
  name             = "postgres-instance"
  region           = "us-east1"
  database_version = "POSTGRES_12"
  deletion_protection = false

  settings {
    tier = "db-f1-micro"
  }
}

resource "google_sql_database" "default" {
  name     = "traffic-pulse-database"
  instance = google_sql_database_instance.postgres_instance.name
}

resource "google_sql_user" "default" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres_instance.name
  password = "postgres"
}

resource "google_project_service" "container_registry" {
  service            = "containerregistry.googleapis.com"
  disable_on_destroy = false
}

// Data Downloader Cluster
resource "google_container_cluster" "gke_cluster" {
  name     = "my-gke-cluster"
  location = "us-east1"

  remove_default_node_pool = true
  initial_node_count       = 1

  network           = "default"
  subnetwork        = "default"

  deletion_protection = false
}

resource "google_container_node_pool" "primary_preemptible_nodes" {
  name       = "my-node-pool"
  location   = "us-east1"
  cluster    = google_container_cluster.gke_cluster.name
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "e2-highcpu-4"
    disk_size_gb = 50

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    tags = ["gke-node", "preemptible"]
  }
}

resource "google_container_cluster" "gke_cluster2" {
  name     = "my-gke-cluster1"
  location = "us-east1"

  remove_default_node_pool = true
  initial_node_count       = 1

  network           = "default"
  subnetwork        = "default"

  deletion_protection = false
}

resource "google_container_node_pool" "primary_preemptible_nodes2" {
  name       = "my-node-pool1"
  location   = "us-east1"
  cluster    = google_container_cluster.gke_cluster2.name
  node_count = 1

  node_config {
    preemptible  = true
    machine_type = "e2-highmem-4"
    disk_size_gb = 50

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    tags = ["gke-node", "preemptible"]
  }
}

