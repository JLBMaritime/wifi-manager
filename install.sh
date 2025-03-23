#!/bin/bash

# JLBMaritime Wi-Fi Manager Installation Script
# This script installs the Wi-Fi Manager on a Raspberry Pi

# Exit on error
set -e

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root (sudo)."
    exit 1
fi

echo "====================================================="
echo "  JLBMaritime Wi-Fi Manager Installation"
echo "====================================================="

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
INSTALL_DIR="/opt/jlbmaritime-wifi-manager"

echo "Installing dependencies..."
apt-get update
apt-get install -y python3-full python3-flask python3-pil wireless-tools network-manager avahi-daemon

# We use system packages instead of pip to avoid externally-managed-environment issues
echo "Checking Python packages..."
if ! dpkg -l | grep -q python3-flask; then
    echo "Installing Flask from apt..."
    apt-get install -y python3-flask
fi

if ! dpkg -l | grep -q python3-pil; then
    echo "Installing Pillow from apt..."
    apt-get install -y python3-pil
fi

# Check if NetworkManager is installed and running
if ! systemctl is-active --quiet NetworkManager; then
    echo "Configuring NetworkManager..."
    apt-get install -y network-manager
    systemctl enable NetworkManager
    systemctl start NetworkManager
    
    # Disable wpa_supplicant service to avoid conflicts
    systemctl disable wpa_supplicant
    systemctl stop wpa_supplicant || true
fi

echo "Setting up application directory..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR"

# Make scripts executable
chmod +x "$INSTALL_DIR/wifi_manager.py"
chmod +x "$INSTALL_DIR/web_interface.py"
chmod +x "$INSTALL_DIR/create_placeholder_logo.py"

# Create placeholder logo if it doesn't exist
if [ ! -f "$INSTALL_DIR/static/img/logo.png" ]; then
    echo "Creating placeholder logo..."
    cd "$INSTALL_DIR" && python3 create_placeholder_logo.py
fi

# Set up hostname
echo "Configuring hostname..."
echo "AIS" > /etc/hostname
sed -i 's/127.0.1.1.*/127.0.1.1\tAIS/g' /etc/hosts

# Set up Avahi for .local domain
echo "Configuring Avahi for ais.local domain..."
cat > /etc/avahi/services/http.service << EOF
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">%h Web Server</name>
  <service>
    <type>_http._tcp</type>
    <port>80</port>
  </service>
</service-group>
EOF

# Restart Avahi
systemctl restart avahi-daemon

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/wifi-manager.service << EOF
[Unit]
Description=JLBMaritime Wi-Fi Manager
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/jlbmaritime-wifi-manager/web_interface.py
WorkingDirectory=/opt/jlbmaritime-wifi-manager
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "Enabling and starting service..."
systemctl daemon-reload
systemctl enable wifi-manager.service
systemctl start wifi-manager.service

echo "====================================================="
echo "Installation complete!"
echo "====================================================="
echo "You can now access the Wi-Fi Manager at: http://ais.local"
echo "Username: JLBMaritime"
echo "Password: Admin"
echo ""
echo "To use the terminal interface:"
echo "sudo python3 /opt/jlbmaritime-wifi-manager/wifi_manager.py --terminal"
echo "====================================================="
