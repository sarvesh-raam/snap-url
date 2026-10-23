#!/usr/bin/env bash
# One-time VM preparation for Ubuntu 24.04 (Oracle Cloud). Safe to run again.
set -euo pipefail

echo "==> Swap (2 GB): the Micro VM has only 1 GB of RAM"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-snapurl.conf >/dev/null
sudo sysctl -q --system

echo "==> Docker"
if ! command -v docker >/dev/null; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io docker-compose-v2 >/dev/null
  sudo systemctl enable --now docker
fi
sudo usermod -aG docker "$USER"

echo "==> Firewall: open 80/443 (Oracle's Ubuntu image rejects everything but SSH by default)"
for port in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW -j ACCEPT 2>/dev/null; then
    # Insert before Oracle's final REJECT rule.
    sudo iptables -I INPUT 5 -p tcp --dport "$port" -m state --state NEW -j ACCEPT
  fi
done
sudo iptables -C INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null || sudo iptables -I INPUT 5 -p udp --dport 443 -j ACCEPT
if command -v netfilter-persistent >/dev/null; then
  sudo netfilter-persistent save >/dev/null
fi

mkdir -p ~/snapurl
echo "==> VM ready"
free -m | head -2
docker --version
