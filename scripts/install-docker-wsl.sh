#!/usr/bin/env bash
#
# Install Docker Engine inside WSL2 (Ubuntu).
#
#   bash scripts/install-docker-wsl.sh
#
# This is the native engine, not Docker Desktop: no Windows installer, no licence
# question, and it starts with the distro because WSL here already runs systemd.
# Teammates on macOS or plain Windows want Docker Desktop instead — this script is
# only for Ubuntu under WSL2.
#
# Safe to re-run: every step checks whether it is already done.

set -euo pipefail

say()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '    \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '    \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# --- sanity checks -----------------------------------------------------------

say "Checking this machine"

[ -f /etc/os-release ] || die "No /etc/os-release; this is not a Debian/Ubuntu system."
. /etc/os-release
[ "${ID:-}" = "ubuntu" ] || die "This script targets Ubuntu; found ID=${ID:-unknown}."
ok "Ubuntu ${VERSION_ID} (${VERSION_CODENAME})"

grep -qi microsoft /proc/version || warn "Not detected as WSL — continuing anyway."
ok "kernel $(uname -r)"

if [ -d /run/systemd/system ]; then
    ok "systemd is active, so the daemon can be managed with systemctl"
else
    die "systemd is not running. Add this to /etc/wsl.conf:

    [boot]
    systemd=true

then run 'wsl.exe --shutdown' from Windows and reopen this terminal."
fi

say "You will be asked for your sudo password once"
sudo -v || die "sudo is required."

# --- repository --------------------------------------------------------------

say "Installing prerequisites"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl
ok "ca-certificates, curl"

say "Adding Docker's package signing key"
if [ -f /etc/apt/keyrings/docker.asc ]; then
    ok "key already present"
else
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    ok "key written to /etc/apt/keyrings/docker.asc"
fi

say "Adding Docker's apt repository"
ARCH="$(dpkg --print-architecture)"
REPO="deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable"
if [ -f /etc/apt/sources.list.d/docker.list ] && grep -qF "$REPO" /etc/apt/sources.list.d/docker.list; then
    ok "repository already configured"
else
    echo "$REPO" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    ok "$REPO"
fi

# --- install -----------------------------------------------------------------

say "Installing Docker Engine (this is the slow part)"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
ok "$(docker --version)"
ok "$(docker compose version)"

say "Starting the daemon and enabling it at boot"
sudo systemctl enable --now docker
sudo systemctl is-active --quiet docker || die "The docker service did not start. Try: sudo systemctl status docker"
ok "docker.service is active and enabled"

# --- run without sudo --------------------------------------------------------

say "Letting you run docker without sudo"
if id -nG "$USER" | tr ' ' '\n' | grep -qx docker; then
    ok "$USER is already in the docker group"
else
    sudo usermod -aG docker "$USER"
    ok "added $USER to the docker group"
fi

# --- verify ------------------------------------------------------------------

say "Verifying"
if docker info > /dev/null 2>&1; then
    ok "docker works in this shell already"
    VERIFIED=yes
else
    # Expected on a first install: the group change is not in this shell's
    # credentials yet. sg runs one command with the new group to prove the
    # daemon itself is fine.
    if sg docker -c 'docker info' > /dev/null 2>&1; then
        ok "daemon is healthy; this shell just needs the new group membership"
        VERIFIED=needs-newgrp
    else
        die "Docker is installed but not responding. Try: sudo systemctl status docker"
    fi
fi

printf '\n\033[1;32mDocker Engine is installed.\033[0m\n\n'
if [ "$VERIFIED" = "needs-newgrp" ]; then
    cat <<'EOF'
One more step — your current shell does not have the docker group yet:

    newgrp docker          # or just close and reopen this terminal

Then check it:

    docker compose version

EOF
else
    cat <<'EOF'
Next, from the repository root:

    docker compose up -d --wait

EOF
fi
