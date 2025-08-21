# # Use Python 3.9 slim image (keeping your version)
# FROM python:3.9-slim

# # Set working directory
# WORKDIR /app

# # Install system dependencies including SSL certificates
# RUN apt-get update && apt-get install -y \
#     gcc \
#     libpq-dev \
#     curl \
#     ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

# # Download RDS CA certificates for SSL support
# # RUN curl -o /opt/rds-ca-2019-root.pem https://s3.amazonaws.com/rds-downloads/rds-ca-2019-root.pem
# # RUN curl -o /opt/rds-combined-ca-bundle.pem https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem
# RUN mkdir -p /opt && \
#     curl -sS https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem \
#     -o /opt/rds-combined-ca-bundle.pem && \
#     chmod 644 /opt/rds-combined-ca-bundle.pem && \
#     openssl x509 -in /opt/rds-combined-ca-bundle.pem -noout -text | head -n 10

# # Update CA certificates
# RUN update-ca-certificates

# # Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application files
# COPY checkout_service.py ./checkout_service.py
# COPY static/ /app/static/
# COPY templates/ /app/templates/

# # Set permissions
# RUN chmod -R 755 /app/static

# # Set environment variables for SSL certificates
# ENV SSL_CERT_FILE=/opt/rds-combined-ca-bundle.pem
# ENV REQUESTS_CA_BUNDLE=/opt/rds-combined-ca-bundle.pem

# # Create non-root user
# RUN adduser --disabled-password --gecos '' appuser
# RUN chown -R appuser:appuser /app

# # Make SSL certificates readable by appuser
# RUN chown appuser:appuser /opt/rds-*.pem
# RUN chmod 644 /opt/rds-*.pem

# # Download RDS certificate
# RUN mkdir -p /etc/ssl/certs && \
#     curl -o /etc/ssl/certs/rds-ca-2019-root.pem \
#     https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem

# # Switch to non-root user
# USER appuser

# # Expose port
# EXPOSE 8080

# # Health check (runs as appuser)
# HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
#   CMD curl -f http://localhost:8080/health || exit 1

# # Use gunicorn to run the app - FIXED: Added missing closing quote and bracket
# CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--pythonpath", "/app", "checkout_service:app"]

# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Download and validate RDS CA bundle (single consolidated step)
RUN mkdir -p /opt && \
    curl -sS https://truststore.pki.rds.amazonaws.com/us-east-1/us-east-1-bundle.pem \
    -o /opt/rds-combined-ca-bundle.pem && \
    chmod 644 /opt/rds-combined-ca-bundle.pem && \
    openssl x509 -in /opt/rds-combined-ca-bundle.pem -noout -text | head -n 5 && \
    ln -s /opt/rds-combined-ca-bundle.pem /etc/ssl/certs/rds-ca-bundle.pem

# Update CA certificates
RUN update-ca-certificates --fresh

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY checkout_service.py .
COPY static/ /app/static/
COPY templates/ /app/templates/

# Set permissions
RUN chmod -R 755 /app/static

# Environment variables
ENV SSL_CERT_FILE=/opt/rds-combined-ca-bundle.pem \
    REQUESTS_CA_BUNDLE=/opt/rds-combined-ca-bundle.pem \
    PGSSLROOTCERT=/opt/rds-combined-ca-bundle.pem

# Create non-root user and set permissions
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app && \
    chown appuser:appuser /opt/rds-combined-ca-bundle.pem

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--pythonpath", "/app", "checkout_service:app"]