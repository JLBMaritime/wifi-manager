# JLBMaritime Wi-Fi Manager

A web-based Wi-Fi manager for Raspberry Pi that allows you to scan, connect to, and manage Wi-Fi networks through a responsive web interface or terminal.

## Features

- Scan for available Wi-Fi networks
- Connect to networks with a single click
- Save network credentials for easy reconnection
- Forget saved networks when no longer needed
- View current connection details including IP address
- Run network diagnostics with ping test
- Responsive design for both desktop and mobile
- Terminal interface for command-line management

## Requirements

- Raspberry Pi 4B (2GB or higher)
- Raspberry Pi OS Bookworm (64-bit)
- Internet connection for installation
- NetworkManager (installed automatically by the installation script)

## Installation

### Automatic Installation

1. Clone this repository:
   ```
   git clone https://github.com/JLBMaritime/wifi-manager.git
   cd wifi-manager
   ```

2. Make the installation script executable and run it:
   ```
   chmod +x ./install.sh
   sudo ./install.sh
   ```

### Manual Installation

1. Install dependencies:
   ```
   sudo apt-get update
   sudo apt-get install -y python3-full python3-flask python3-pil wireless-tools network-manager avahi-daemon
   sudo systemctl enable NetworkManager
   sudo systemctl start NetworkManager
   ```

2. Clone this repository:
   ```
   git clone https://github.com/JLBMaritime/wifi-manager.git
   cd wifi-manager
   ```

3. Make scripts executable:
   ```
   chmod +x ./install.sh
   chmod +x ./test_setup.sh
   chmod +x ./create_placeholder_logo.py
   chmod +x ./wifi_manager.py
   chmod +x ./web_interface.py
   ```

4. Create a placeholder logo (or add your own logo.png to static/img/):
   ```
   sudo python3 create_placeholder_logo.py
   ```

5. Set up the hostname:
   ```
   sudo echo "AIS" > /etc/hostname
   sudo sed -i 's/127.0.1.1.*/127.0.1.1\tAIS/g' /etc/hosts
   ```

6. Configure Avahi for .local domain:
   ```
   sudo bash -c 'cat > /etc/avahi/services/http.service << EOF
   <?xml version="1.0" standalone="no"?>
   <!DOCTYPE service-group SYSTEM "avahi-service.dtd">
   <service-group>
     <name replace-wildcards="yes">%h Web Server</name>
     <service>
       <type>_http._tcp</type>
       <port>80</port>
     </service>
   </service-group>
   EOF'
   sudo systemctl restart avahi-daemon
   ```

7. Set up the service:
   ```
   sudo mkdir -p /opt/jlbmaritime-wifi-manager
   sudo cp -r . /opt/jlbmaritime-wifi-manager
   sudo chmod +x /opt/jlbmaritime-wifi-manager/wifi_manager.py
   sudo chmod +x /opt/jlbmaritime-wifi-manager/web_interface.py
   
   sudo bash -c 'cat > /etc/systemd/system/wifi-manager.service << EOF
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
   EOF'
   
   sudo systemctl daemon-reload
   sudo systemctl enable wifi-manager.service
   sudo systemctl start wifi-manager.service
   ```

## Usage

### Web Interface

1. Access the web interface by navigating to http://ais.local in your browser
2. Log in with the following credentials:
   - Username: JLBMaritime
   - Password: Admin
3. Use the interface to manage your Wi-Fi connections:
   - View current connection details
   - Scan for available networks
   - Connect to networks
   - Manage saved networks
   - Run network diagnostics

### Terminal Interface

1. Run the terminal interface:
   ```
   sudo python3 /opt/jlbmaritime-wifi-manager/wifi_manager.py --terminal
   ```
2. Follow the on-screen instructions to manage your Wi-Fi connections

## Customization

### Changing the Logo

Replace the file at `/opt/jlbmaritime-wifi-manager/static/img/logo.png` with your own logo.

### Changing Authentication Credentials

Edit the `requires_auth` function in `/opt/jlbmaritime-wifi-manager/web_interface.py` to change the username and password.

## Troubleshooting

- If you cannot access ais.local, try using the Raspberry Pi's IP address instead
- Check the service status with: `sudo systemctl status wifi-manager.service`
- View logs with: `sudo journalctl -u wifi-manager.service`
- If the web interface is not loading, ensure port 80 is not being used by another service
- For permission issues, make sure the service is running as root
- If you experience connection issues:
  - Make sure your Wi-Fi adapter is properly configured
  - Verify NetworkManager is running: `sudo systemctl status NetworkManager`
  - Try restarting NetworkManager: `sudo systemctl restart NetworkManager`
  - Try restarting the Wi-Fi manager service: `sudo systemctl restart wifi-manager.service`
  - Check the NetworkManager logs: `sudo journalctl -u NetworkManager`
  - Check the Wi-Fi manager logs: `sudo journalctl -u wifi-manager.service`

## Project Structure

```
wifi-manager/
├── config.json                 # Configuration file for saved networks
├── create_placeholder_logo.py  # Script to create a placeholder logo
├── install.sh                  # Installation script
├── README.md                   # This documentation
├── static/                     # Static web assets
│   ├── css/
│   │   └── style.css           # CSS styles for the web interface
│   ├── img/
│   │   └── logo.png            # Logo image
│   └── js/
│       └── script.js           # JavaScript for the web interface
├── templates/
│   └── index.html              # HTML template for the web interface
├── web_interface.py            # Web server implementation
└── wifi_manager.py             # Core Wi-Fi management functionality
```

## License

This project is licensed under the MIT License.

## Acknowledgments

- Developed for JLBMaritime
- Uses Flask for the web server
- Uses NetworkManager for Wi-Fi management (with wpa_supplicant fallback)
