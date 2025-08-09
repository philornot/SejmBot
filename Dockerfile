# SejmBot Docker Container
# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=2.0

# Labels
LABEL maintainer="SejmBot Developer"
LABEL description="Parser transkryptów Sejmu RP"
LABEL version="${VERSION}"
LABEL build-date="${BUILD_DATE}"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app user and directories
RUN groupadd -r sejmbot && useradd -r -g sejmbot sejmbot && \
    mkdir -p /app/transkrypty /app/logs && \
    chown -R sejmbot:sejmbot /app

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=sejmbot:sejmbot sejmbot.py .
COPY --chown=sejmbot:sejmbot requirements.txt .

# Set timezone (można zmienić przez ENV)
ENV TZ=Europe/Warsaw
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create volumes for persistent data
VOLUME ["/app/transkrypty", "/app/logs"]

# Switch to non-root user
USER sejmbot

# Health check
HEALTHCHECK --interval=30m --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sejmbot; print('SejmBot OK')" || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=1
ENV PYTHONOPTIMIZE=1

# Default command - daemon mode
CMD ["python", "sejmbot.py", "--daemon"]

# Expose port for potential future web interface
EXPOSE 8080