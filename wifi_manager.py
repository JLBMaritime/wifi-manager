#!/usr/bin/env python3
import json
import os
import subprocess
import re
import time
import datetime
import sys
import getpass
from typing import Dict, List, Optional, Any, Union

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

def load_config() -> Dict[str, Any]:
    """Load configuration from the config file."""
    if not os.path.exists(CONFIG_FILE):
        return {
            "saved_networks": [],
            "current_connection": {
                "ssid": "",
                "ip_address": "",
                "signal_strength": "",
                "connected_since": ""
            },
            "settings": {
                "auto_reconnect": True,
                "scan_interval": 30
            }
        }
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to the config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def run_command(command: str) -> str:
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error: {e.stderr}")
        return ""

def scan_networks() -> List[Dict[str, str]]:
    """Scan for available Wi-Fi networks and return a list of networks with details."""
    networks = []
    
    # Check if NetworkManager is installed
    nm_installed = run_command("which nmcli").strip() != ""
    
    if nm_installed:
        # Use NetworkManager to scan for networks
        print("Using NetworkManager to scan for networks...")
        output = run_command("sudo nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
        
        for line in output.splitlines():
            if not line.strip():
                continue
                
            parts = line.split(':')
            if len(parts) >= 3:
                ssid = parts[0]
                if not ssid:  # Skip networks with empty SSIDs
                    continue
                    
                try:
                    signal_strength = int(parts[1])
                    security = parts[2] if len(parts) > 2 and parts[2] else "Open"
                    
                    networks.append({
                        'ssid': ssid,
                        'signal_strength': f"{signal_strength}%",
                        'security': "Open" if security == "--" else "WPA/WPA2"
                    })
                except (ValueError, IndexError):
                    pass
    else:
        # Fall back to iwlist if NetworkManager is not available
        print("NetworkManager not found, falling back to iwlist...")
        output = run_command("sudo iwlist wlan0 scan | grep -E 'ESSID|Quality|Encryption'")
        
        current_network = {}
        
        for line in output.splitlines():
            line = line.strip()
            
            if "ESSID" in line:
                if current_network and 'ssid' in current_network:
                    networks.append(current_network)
                    current_network = {}
                
                ssid = re.search(r'ESSID:"(.*?)"', line)
                if ssid and ssid.group(1):
                    current_network['ssid'] = ssid.group(1)
            
            elif "Quality" in line:
                quality = re.search(r'Quality=(\d+)/(\d+)', line)
                if quality:
                    quality_value = int(quality.group(1)) / int(quality.group(2)) * 100
                    current_network['signal_strength'] = f"{quality_value:.0f}%"
                    
                signal = re.search(r'Signal level=(-\d+) dBm', line)
                if signal:
                    current_network['signal_level'] = f"{signal.group(1)} dBm"
            
            elif "Encryption" in line:
                if "on" in line:
                    current_network['security'] = "WPA/WPA2"
                else:
                    current_network['security'] = "Open"
        
        # Add the last network if it exists
        if current_network and 'ssid' in current_network:
            networks.append(current_network)
    
    # Filter out duplicate networks, keeping only the one with the highest signal strength
    unique_networks = {}
    for network in networks:
        ssid = network['ssid']
        signal_str = network.get('signal_strength', '0%')
        
        # Extract numeric signal strength
        signal_value = 0
        if signal_str:
            match = re.search(r'(\d+)', signal_str)
            if match:
                signal_value = int(match.group(1))
        
        # Keep the network with the highest signal strength
        if ssid not in unique_networks or signal_value > unique_networks[ssid]['signal_value']:
            network['signal_value'] = signal_value  # Store numeric value for sorting
            unique_networks[ssid] = network
    
    # Convert back to list and sort by signal strength
    filtered_networks = list(unique_networks.values())
    filtered_networks.sort(key=lambda x: x.get('signal_value', 0), reverse=True)
    
    # Remove the temporary signal_value field
    for network in filtered_networks:
        if 'signal_value' in network:
            del network['signal_value']
    
    # Mark saved networks
    config = load_config()
    saved_ssids = [network['ssid'] for network in config['saved_networks']]
    
    for network in filtered_networks:
        network['saved'] = network['ssid'] in saved_ssids
    
    return filtered_networks

def get_current_connection() -> Dict[str, str]:
    """Get details about the current Wi-Fi connection."""
    ssid = ""
    ip_address = ""
    signal_strength = ""
    
    # First check if we have a saved current connection in config
    config = load_config()
    if config.get('current_connection', {}).get('ssid'):
        saved_conn = config['current_connection']
        ssid = saved_conn.get('ssid', '')
        ip_address = saved_conn.get('ip_address', '')
        signal_strength = saved_conn.get('signal_strength', '')
    
    # Check if NetworkManager is installed
    nm_installed = run_command("which nmcli").strip() != ""
    
    if nm_installed:
        # Use NetworkManager to get connection details
        print("Using NetworkManager to get connection details...")
        
        # Get active connection
        connection_output = run_command("sudo nmcli -t -f NAME,DEVICE,TYPE connection show --active")
        
        # Find the Wi-Fi connection
        wifi_connection = None
        for line in connection_output.splitlines():
            if "wireless" in line or ":wifi:" in line:
                wifi_connection = line.split(':')[0]
                break
        
        if wifi_connection:
            # Get SSID
            ssid = wifi_connection
            
            # Get signal strength
            signal_output = run_command(f"sudo nmcli -f SIGNAL device wifi list | grep '{ssid}'")
            if signal_output:
                signal_match = re.search(r'(\d+)', signal_output)
                if signal_match:
                    signal_strength = f"{signal_match.group(1)}%"
            else:
                # Try to get signal strength in dBm
                signal_output = run_command("iwconfig wlan0 | grep -i signal")
                if signal_output:
                    signal_match = re.search(r'Signal level=(-\d+) dBm', signal_output)
                    if signal_match:
                        signal_strength = f"{signal_match.group(1)} dBm"
            
            # Get IP address
            ip_output = run_command("hostname -I | awk '{print $1}'")
            ip_address = ip_output.strip() if ip_output else ""
    else:
        # Fall back to iwconfig/ifconfig if NetworkManager is not available
        print("NetworkManager not found, falling back to iwconfig/ifconfig...")
        
        # Get SSID
        ssid_output = run_command("iwgetid -r")
        ssid = ssid_output.strip() if ssid_output else ""
        
        # Get IP address
        ip_output = run_command("hostname -I | awk '{print $1}'")
        ip_address = ip_output.strip() if ip_output else ""
        
        # Get signal strength
        signal_output = run_command("iwconfig wlan0 | grep -i quality")
        if signal_output:
            quality = re.search(r'Quality=(\d+)/(\d+)', signal_output)
            if quality:
                quality_value = int(quality.group(1)) / int(quality.group(2)) * 100
                signal_strength = f"{quality_value:.0f}%"
            
            signal = re.search(r'Signal level=(-\d+) dBm', signal_output)
            if signal:
                signal_strength = f"{signal.group(1)} dBm"
    
    # Update config with current connection
    if ssid:
        config = load_config()
        config['current_connection'] = {
            "ssid": ssid,
            "ip_address": ip_address,
            "signal_strength": signal_strength,
            "connected_since": datetime.datetime.now().isoformat()
        }
        save_config(config)
    
    return {
        "ssid": ssid,
        "ip_address": ip_address,
        "signal_strength": signal_strength
    }

def connect_to_network(ssid: str, password: Optional[str] = None, security: str = "WPA2") -> Dict[str, Any]:
    """Connect to a Wi-Fi network with the given SSID and password."""
    # Check if network is already saved
    config = load_config()
    saved_networks = config['saved_networks']
    
    network_config = None
    for network in saved_networks:
        if network['ssid'] == ssid:
            network_config = network
            break
    
    # If not saved and no password provided for secured network
    if not network_config and not password and security != "Open":
        return {
            "success": False,
            "message": "Password required for secured network"
        }
    
    # Check if NetworkManager is installed
    nm_installed = run_command("which nmcli").strip() != ""
    
    if nm_installed:
        # Use NetworkManager to connect
        print(f"Using NetworkManager to connect to {ssid}...")
        
        # First, ensure we have the latest scan results
        run_command("sudo nmcli device wifi rescan")
        time.sleep(2)  # Give time for the scan to complete
        
        # Escape special characters in SSID and password
        escaped_ssid = ssid.replace('"', '\\"').replace('$', '\\$')
        
        # Get the current connection before attempting to change it
        current_before = get_current_connection()
        print(f"Current connection before: {current_before['ssid']}")
        
        # Try different connection methods
        success = False
        error_message = ""
        
        try:
            # Method 1: Connect by SSID directly
            if security == "Open":
                connect_cmd = f'sudo nmcli device wifi connect "{escaped_ssid}"'
            else:
                escaped_password = (password if password else network_config["password"]).replace('"', '\\"').replace('$', '\\$')
                connect_cmd = f'sudo nmcli device wifi connect "{escaped_ssid}" password "{escaped_password}"'
            
            print(f"Trying connection method 1: {connect_cmd}")
            result = run_command(connect_cmd)
            
            # Check if connection was successful
            if "successfully activated" in result or "Connection successfully activated" in result:
                success = True
                print("Connection successful with method 1")
            else:
                error_message = result
                print(f"Method 1 failed: {error_message}")
                
                # Method 2: Delete existing connection and create a new one
                print("Trying connection method 2...")
                
                # Delete any existing connection with the same name
                run_command(f'sudo nmcli connection delete "{escaped_ssid}" 2>/dev/null || true')
                
                # Create a new connection
                if security == "Open":
                    connect_cmd = f'sudo nmcli device wifi connect "{escaped_ssid}" name "{escaped_ssid}"'
                else:
                    connect_cmd = f'sudo nmcli device wifi connect "{escaped_ssid}" password "{escaped_password}" name "{escaped_ssid}"'
                
                print(f"Connection command: {connect_cmd}")
                result = run_command(connect_cmd)
                
                if "successfully activated" in result or "Connection successfully activated" in result:
                    success = True
                    print("Connection successful with method 2")
                else:
                    error_message = result
                    print(f"Method 2 failed: {error_message}")
                    
                    # Method 3: Try connecting with specific device
                    print("Trying connection method 3...")
                    
                    # Get the Wi-Fi device name
                    device_output = run_command("sudo nmcli device | grep wifi")
                    device_match = re.search(r'(\S+)\s+wifi', device_output)
                    
                    if device_match:
                        device = device_match.group(1)
                        print(f"Found Wi-Fi device: {device}")
                        
                        if security == "Open":
                            connect_cmd = f'sudo nmcli device wifi connect "{escaped_ssid}" ifname {device}'
                        else:
                            connect_cmd = f'sudo nmcli device wifi connect "{escaped_ssid}" password "{escaped_password}" ifname {device}'
                        
                        print(f"Connection command: {connect_cmd}")
                        result = run_command(connect_cmd)
                        
                        if "successfully activated" in result or "Connection successfully activated" in result:
                            success = True
                            print("Connection successful with method 3")
                        else:
                            error_message = result
                            print(f"Method 3 failed: {error_message}")
                    else:
                        print("Could not find Wi-Fi device")
        except Exception as e:
            error_message = str(e)
            print(f"Connection error: {error_message}")
        
        # Wait for connection to establish
        time.sleep(10)
        
        # Check if connected
        current = get_current_connection()
        success = current['ssid'] == ssid
        
        # If still not connected, try one more approach - restart NetworkManager
        if not success:
            print("Connection not established. Trying to restart NetworkManager...")
            run_command("sudo systemctl restart NetworkManager")
            time.sleep(15)  # Give more time for NetworkManager to restart and connect
            
            # Check again
            current = get_current_connection()
            success = current['ssid'] == ssid
    else:
        # Fall back to wpa_supplicant if NetworkManager is not available
        print("NetworkManager not found, falling back to wpa_supplicant...")
        
        # Create wpa_supplicant configuration
        wpa_config = f"""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{ssid}"
    """
        
        if security == "Open":
            wpa_config += '    key_mgmt=NONE\n'
        else:
            wpa_config += f'    psk="{password if password else network_config["password"]}"\n'
        
        wpa_config += '}\n'
        
        # Write temporary wpa_supplicant configuration
        temp_config_path = "/tmp/wpa_supplicant.conf"
        with open(temp_config_path, 'w') as f:
            f.write(wpa_config)
        
        # Apply configuration
        run_command(f"sudo cp {temp_config_path} /etc/wpa_supplicant/wpa_supplicant.conf")
        
        # Restart networking with more robust approach
        run_command("sudo wpa_cli -i wlan0 reconfigure")
        run_command("sudo ip link set wlan0 down")
        run_command("sudo ip link set wlan0 up")
        run_command("sudo systemctl restart dhcpcd")
        
        # Wait for connection
        time.sleep(10)
        
        # Check if connected
        current = get_current_connection()
        success = current['ssid'] == ssid
    
    # Wait longer for connection to establish
    time.sleep(5)
    
    # Check if connected
    current = get_current_connection()
    success = current['ssid'] == ssid
    
    # Save network if connection successful and not already saved
    if success and not network_config and password:
        save_network(ssid, password, security)
    
    return {
        "success": success,
        "message": "Connected successfully" if success else "Failed to connect",
        "connection": current if success else {}
    }

def save_network(ssid: str, password: str, security: str = "WPA2") -> Dict[str, Any]:
    """Save a network's credentials to the configuration file."""
    config = load_config()
    
    # Check if network already saved
    for network in config['saved_networks']:
        if network['ssid'] == ssid:
            network['password'] = password
            network['security'] = security
            save_config(config)
            return {
                "success": True,
                "message": f"Updated saved network: {ssid}"
            }
    
    # Add new network
    config['saved_networks'].append({
        "ssid": ssid,
        "password": password,
        "security": security,
        "priority": len(config['saved_networks']) + 1
    })
    
    save_config(config)
    
    return {
        "success": True,
        "message": f"Saved network: {ssid}"
    }

def forget_network(ssid: str) -> Dict[str, Any]:
    """Remove a saved network from the configuration file."""
    config = load_config()
    
    # Check if this is the current connection
    current = get_current_connection()
    if current['ssid'] == ssid:
        return {
            "success": False,
            "message": "Cannot forget the current connection"
        }
    
    # Find and remove the network
    initial_count = len(config['saved_networks'])
    config['saved_networks'] = [n for n in config['saved_networks'] if n['ssid'] != ssid]
    
    if len(config['saved_networks']) < initial_count:
        save_config(config)
        return {
            "success": True,
            "message": f"Forgot network: {ssid}"
        }
    else:
        return {
            "success": False,
            "message": f"Network not found: {ssid}"
        }

def run_diagnostics() -> Dict[str, Any]:
    """Run network diagnostics and return results."""
    results = {
        "connectivity": False,
        "ping_results": {},
        "dns_resolution": False
    }
    
    # Check current connection
    current = get_current_connection()
    if not current['ssid']:
        return {
            "success": False,
            "message": "Not connected to any network",
            "results": results
        }
    
    # Check internet connectivity (ping google.com)
    ping_output = run_command("ping -c 4 8.8.8.8")
    results["connectivity"] = "0% packet loss" in ping_output or "64 bytes from" in ping_output
    
    # Parse ping results
    ping_times = re.findall(r'time=(\d+\.\d+) ms', ping_output)
    if ping_times:
        results["ping_results"] = {
            "min": min(float(t) for t in ping_times),
            "max": max(float(t) for t in ping_times),
            "avg": sum(float(t) for t in ping_times) / len(ping_times)
        }
    
    # Check DNS resolution - try multiple methods
    dns_resolution = False
    
    # Method 1: nslookup
    dns_output = run_command("nslookup google.com")
    if "Address:" in dns_output:
        dns_resolution = True
    
    # Method 2: host command
    if not dns_resolution:
        host_output = run_command("host google.com")
        if "has address" in host_output:
            dns_resolution = True
    
    # Method 3: dig command
    if not dns_resolution:
        dig_output = run_command("dig +short google.com")
        if dig_output.strip():
            dns_resolution = True
    
    # Method 4: ping with hostname
    if not dns_resolution:
        ping_dns_output = run_command("ping -c 1 google.com")
        if "64 bytes from" in ping_dns_output:
            dns_resolution = True
    
    results["dns_resolution"] = dns_resolution
    
    return {
        "success": True,
        "message": "Diagnostics completed",
        "results": results
    }

def terminal_interface() -> None:
    """Run the terminal-based interface for the Wi-Fi manager."""
    while True:
        os.system('clear')
        print("=" * 50)
        print("JLBMaritime Wi-Fi Manager - Terminal Interface")
        print("=" * 50)
        
        # Show current connection
        current = get_current_connection()
        if current['ssid']:
            print(f"\nCurrent Connection: {current['ssid']}")
            print(f"IP Address: {current['ip_address']}")
            print(f"Signal Strength: {current['signal_strength']}")
        else:
            print("\nNot connected to any network")
        
        print("\nOptions:")
        print("1. Scan for networks")
        print("2. Connect to a network")
        print("3. View saved networks")
        print("4. Forget a saved network")
        print("5. Run diagnostics")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == '1':
            print("\nScanning for networks...")
            networks = scan_networks()
            print(f"\nFound {len(networks)} networks:")
            for i, network in enumerate(networks, 1):
                saved = " (Saved)" if network.get('saved') else ""
                print(f"{i}. {network['ssid']} - Signal: {network['signal_strength']} - Security: {network['security']}{saved}")
            input("\nPress Enter to continue...")
        
        elif choice == '2':
            networks = scan_networks()
            print("\nAvailable networks:")
            for i, network in enumerate(networks, 1):
                saved = " (Saved)" if network.get('saved') else ""
                print(f"{i}. {network['ssid']} - Signal: {network['signal_strength']} - Security: {network['security']}{saved}")
            
            try:
                network_idx = int(input("\nEnter network number to connect: ")) - 1
                if 0 <= network_idx < len(networks):
                    selected = networks[network_idx]
                    if selected.get('saved'):
                        print(f"\nConnecting to saved network: {selected['ssid']}...")
                        result = connect_to_network(selected['ssid'])
                    elif selected['security'] == "Open":
                        print(f"\nConnecting to open network: {selected['ssid']}...")
                        result = connect_to_network(selected['ssid'], security="Open")
                    else:
                        password = getpass.getpass(f"\nEnter password for {selected['ssid']}: ")
                        print(f"\nConnecting to {selected['ssid']}...")
                        result = connect_to_network(selected['ssid'], password)
                    
                    print(result['message'])
                else:
                    print("\nInvalid selection")
            except ValueError:
                print("\nInvalid input")
            
            input("\nPress Enter to continue...")
        
        elif choice == '3':
            config = load_config()
            saved_networks = config['saved_networks']
            
            if not saved_networks:
                print("\nNo saved networks")
            else:
                print(f"\nSaved networks ({len(saved_networks)}):")
                for i, network in enumerate(saved_networks, 1):
                    print(f"{i}. {network['ssid']} - Security: {network['security']}")
            
            input("\nPress Enter to continue...")
        
        elif choice == '4':
            config = load_config()
            saved_networks = config['saved_networks']
            
            if not saved_networks:
                print("\nNo saved networks")
            else:
                print(f"\nSaved networks ({len(saved_networks)}):")
                for i, network in enumerate(saved_networks, 1):
                    print(f"{i}. {network['ssid']} - Security: {network['security']}")
                
                try:
                    network_idx = int(input("\nEnter network number to forget: ")) - 1
                    if 0 <= network_idx < len(saved_networks):
                        selected = saved_networks[network_idx]
                        confirm = input(f"Are you sure you want to forget {selected['ssid']}? (y/n): ")
                        
                        if confirm.lower() == 'y':
                            result = forget_network(selected['ssid'])
                            print(result['message'])
                    else:
                        print("\nInvalid selection")
                except ValueError:
                    print("\nInvalid input")
            
            input("\nPress Enter to continue...")
        
        elif choice == '5':
            print("\nRunning diagnostics...")
            results = run_diagnostics()
            
            if results['success']:
                r = results['results']
                print("\nDiagnostic Results:")
                print(f"Internet Connectivity: {'Yes' if r['connectivity'] else 'No'}")
                print(f"DNS Resolution: {'Yes' if r['dns_resolution'] else 'No'}")
                
                if r['ping_results']:
                    print("\nPing Results (8.8.8.8):")
                    print(f"Min: {r['ping_results']['min']:.2f} ms")
                    print(f"Max: {r['ping_results']['max']:.2f} ms")
                    print(f"Avg: {r['ping_results']['avg']:.2f} ms")
            else:
                print(f"\nError: {results['message']}")
            
            input("\nPress Enter to continue...")
        
        elif choice == '6':
            print("\nExiting Wi-Fi Manager...")
            break
        
        else:
            print("\nInvalid choice. Please try again.")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print("This script must be run as root (sudo).")
        sys.exit(1)
    
    # Check if terminal interface is requested
    if len(sys.argv) > 1 and sys.argv[1] == "--terminal":
        terminal_interface()
    else:
        # Print usage
        print("Usage:")
        print("  sudo python3 wifi_manager.py --terminal  # Run terminal interface")
        print("  (Web interface is provided by web_interface.py)")
