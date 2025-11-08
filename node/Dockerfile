# Stage 1: System dependencies
FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y \
    gcc \
    iptables \
    curl \
    unzip \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Install rathole (cached layer)
FROM base AS rathole-bin
RUN set -eux; \
    ARCH_RAW="$(uname -m)"; \
    case "$ARCH_RAW" in \
        x86_64) ARCH="x86_64" ;; \
        aarch64) ARCH="aarch64" ;; \
        *) ARCH="x86_64" ;; \
    esac; \
    echo "Fetching rathole for $ARCH_RAW"; \
    RATHOLE_JSON="$(curl -fsSL https://api.github.com/repos/rapiz1/rathole/releases/latest)"; \
    RATHOLE_URL="$(printf '%s' "$RATHOLE_JSON" | jq -r --arg arch "$ARCH" '.assets[] | select(.name | test($arch) and test("linux")) | .browser_download_url' | head -n1)"; \
    if [ -z "$RATHOLE_URL" ] || [ "$RATHOLE_URL" = "null" ]; then \
        echo "Unable to find rathole release for arch=$ARCH_RAW"; \
        exit 1; \
    fi; \
    RATHOLE_TMP="$(mktemp -d)"; \
    curl -fsSL "$RATHOLE_URL" -o "$RATHOLE_TMP/asset"; \
    case "$RATHOLE_URL" in \
        *.tar.gz|*.tgz) tar -xzf "$RATHOLE_TMP/asset" -C "$RATHOLE_TMP" ;; \
        *.zip) unzip -q "$RATHOLE_TMP/asset" -d "$RATHOLE_TMP" ;; \
        *) mv "$RATHOLE_TMP/asset" "$RATHOLE_TMP/rathole-bin" ;; \
    esac; \
    RATHOLE_BIN="$(find "$RATHOLE_TMP" -type f -name 'rathole*' | head -n1)"; \
    if [ -z "$RATHOLE_BIN" ]; then \
        echo "Rathole binary missing after extracting $RATHOLE_URL"; \
        ls -R "$RATHOLE_TMP"; \
        exit 1; \
    fi; \
    install -Dm755 "$RATHOLE_BIN" /usr/local/bin/rathole; \
    rm -rf "$RATHOLE_TMP"; \
    /usr/local/bin/rathole --version || true

# Stage 3: Install backhaul (cached layer)
FROM base AS backhaul-bin
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir -p /opt/backhaul; \
    ARCH="$(uname -m)"; \
    case "$ARCH" in \
        x86_64|amd64) PLATFORM="amd64" ;; \
        aarch64|arm64) PLATFORM="arm64" ;; \
        *) echo "Unsupported architecture: $ARCH"; exit 1 ;; \
    esac; \
    RELEASE_JSON="$(curl -fsSL https://api.github.com/repos/Musixal/Backhaul/releases/latest)"; \
    ASSET_URL="$(printf '%s' "$RELEASE_JSON" | jq -r --arg platform "$PLATFORM" '.assets[] | select(.name | test("linux_" + $platform)) | .browser_download_url' | head -n1)"; \
    if [ -z "$ASSET_URL" ] || [ "$ASSET_URL" = "null" ]; then \
        echo "Unable to find Backhaul release asset for platform: $PLATFORM"; \
        exit 1; \
    fi; \
    TMP_FILE="$(mktemp)"; \
    curl -fsSL "$ASSET_URL" -o "$TMP_FILE"; \
    FILE_NAME="$(basename "$ASSET_URL")"; \
    case "$FILE_NAME" in \
        *.tar.gz|*.tgz) \
            tar -xzf "$TMP_FILE" -C /opt/backhaul; \
            ;; \
        *.zip) \
            unzip -q "$TMP_FILE" -d /opt/backhaul; \
            ;; \
        *) \
            mv "$TMP_FILE" /opt/backhaul/backhaul-download; \
            ;; \
    esac; \
    if [ -f /opt/backhaul/backhaul-download ]; then \
        mv /opt/backhaul/backhaul-download /opt/backhaul/backhaul; \
    else \
        BIN_PATH="$(find /opt/backhaul -maxdepth 1 -type f -name 'backhaul*' | head -n1)"; \
        if [ -z "$BIN_PATH" ]; then \
            echo "Backhaul binary not found after extracting $FILE_NAME"; \
            ls -R /opt/backhaul; \
            exit 1; \
        fi; \
        mv "$BIN_PATH" /opt/backhaul/backhaul; \
    fi; \
    chmod +x /opt/backhaul/backhaul; \
    rm -f "$TMP_FILE" 2>/dev/null || true; \
    /opt/backhaul/backhaul --version || true

# Stage 4: Python dependencies (cached layer)
FROM base AS deps
WORKDIR /app
COPY requirements.txt .
# Use pip cache if available
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Stage 5: Final image
FROM base
WORKDIR /app

# Copy binaries from binary stages
COPY --from=rathole-bin /usr/local/bin/rathole /usr/local/bin/rathole
COPY --from=backhaul-bin /opt/backhaul/backhaul /usr/local/bin/backhaul

# Copy Python dependencies from deps stage
COPY --from=deps /usr/local /usr/local

# Copy application code (changes most frequently)
COPY . .

EXPOSE 8888

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888", "--log-level", "info", "--access-log"]
