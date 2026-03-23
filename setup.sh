#!/bin/bash
# BAS Platform Setup Script
# =========================
# Run this on Kali Linux to set up the BAS platform

set -e

echo "============================================"
echo "  Adaptive BAS Platform - Setup Script"
echo "============================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}[1/8] Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

echo -e "${GREEN}[2/8] Installing Python 3.11 and dependencies...${NC}"
apt-get install -y python3 python3-venv python3-pip python3-dev
apt-get install -y python3-venv python3-full

echo -e "${GREEN}[3/8] Installing PowerShell (for remoting)...${NC}"
# Install PowerShell
apt-get install -y wget apt-transport-https software-properties-common
wget -q "https://packages.microsoft.com/config/debian/$(lsb_release -rs)/packages-microsoft-prod.deb"
dpkg -i packages-microsoft-prod.deb
apt-get update
apt-get install -y powershell
rm -f packages-microsoft-prod.deb

echo -e "${GREEN}[4/8] Installing Sliver C2...${NC}"
# Install Sliver C2
curl https://sliver.sh/install | sudo bash

# Start Sliver daemon
systemctl enable sliver
systemctl start sliver

echo -e "${GREEN}[5/8] Setting up Python virtual environment...${NC}"
cd Desktop/bas_platform
python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}[6/8] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}[7/8] Creating environment file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Created .env file. Please edit it with your configuration.${NC}"
fi

echo -e "${GREEN}[8/8] Creating necessary directories...${NC}"
mkdir -p logs
mkdir -p data
mkdir -p attacks/modules

echo ""
echo "============================================"
echo -e "${GREEN}Setup completed successfully!${NC}"
echo "============================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Configure victim Windows VM (see WINDOWS_SETUP.md)"
echo "3. Start Sliver server: sliver-server"
echo "4. Run the API: ./run.sh"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""
