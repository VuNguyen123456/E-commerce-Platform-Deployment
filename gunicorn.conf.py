# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes - adjusted for ECS Fargate resources
# With 512 CPU units (0.5 vCPU), use 2 workers max
workers = 2
worker_class = "sync"
worker_connections = 1000

# Timeouts - CRITICAL for fixing worker timeouts
timeout = 120  # Worker timeout (was causing your CRITICAL WORKER TIMEOUT errors)
keepalive = 5
graceful_timeout = 30

# Memory management
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Logging
loglevel = "info"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "checkout_service"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Worker lifecycle
max_worker_memory = 200  # MB - restart worker if it uses more memory
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance