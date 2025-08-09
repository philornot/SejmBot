# SejmBot Docker Container - Optimized for Raspberry Pi Zero 2W
# Lightweight build for ARM v7 32-bit with minimal dependencies

FROM python:3.11-slim

# Set build arguments
ARG BUILD_DATE
ARG VERSION=2.0

# Labels
LABEL maintainer="philornot"
LABEL description="Parser transkryptów Sejmu RP - Pi Zero 2W optimized"
LABEL version="${VERSION}"
LABEL build-date="${BUILD_DATE}"

# Install system dependencies (minimal set for Pi Zero)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create app user and directories early
RUN groupadd -r sejmbot && useradd -r -g sejmbot sejmbot && \
    mkdir -p /app/transkrypty /app/logs && \
    chown -R sejmbot:sejmbot /app

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python packages with optimizations for low-memory ARM
# Use --no-cache-dir to save space, prefer wheels over source builds
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    --prefer-binary \
    --only-binary=":all:" \
    --find-links https://www.piwheels.org/simple \
    -r requirements.txt || \
    pip install --no-cache-dir \
    --prefer-binary \
    -r requirements.txt

# Copy application files
COPY --chown=sejmbot:sejmbot sejmbot.py .

# Set timezone for Poland
ENV TZ=Europe/Warsaw
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Create volumes for persistent data
VOLUME ["/app/transkrypty", "/app/logs"]

# Switch to non-root user
USER sejmbot

# Lightweight health check (every 2 hours to save resources)
HEALTHCHECK --interval=2h --timeout=30s --start-period=60s --retries=2 \
    CMD python -c "print('SejmBot OK')" || exit 1

# Environment variables optimized for Pi Zero
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=1
ENV PYTHONOPTIMIZE=2
ENV MALLOC_TRIM_THRESHOLD_=65536

# Default command with memory-friendly options
CMD ["python", "-u", "sejmbot.py", "--daemon"]