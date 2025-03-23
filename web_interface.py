#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import wifi_manager
import json
import os
import functools
import time
import threading

app = Flask(__name__)

# Path to the logo file
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img', 'logo.png')

# Authentication decorator
def requires_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != 'JLBMaritime' or auth.password != 'Admin':
            return Response('Login required', 401,
                {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

# Background scanning thread
def background_scanner():
    while True:
        try:
            # Get current connection status
            wifi_manager.get_current_connection()
            
            # Run diagnostics to update connectivity and DNS status
            wifi_manager.run_diagnostics()
            
            # Scan networks less frequently (every 2 cycles)
            if int(time.time()) % 60 < 30:  # Only scan during first 30 seconds of each minute
                wifi_manager.scan_networks()
        except Exception as e:
            print(f"Error in background scanner: {e}")
        
        # Sleep for 15 seconds between updates
        time.sleep(15)

# Start background scanner thread
scanner_thread = threading.Thread(target=background_scanner, daemon=True)
scanner_thread.start()

# Web routes
@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/scan', methods=['GET'])
@requires_auth
def scan():
    networks = wifi_manager.scan_networks()
    return jsonify(networks)

@app.route('/api/current', methods=['GET'])
@requires_auth
def current():
    connection = wifi_manager.get_current_connection()
    return jsonify(connection)

@app.route('/api/saved', methods=['GET'])
@requires_auth
def saved():
    config = wifi_manager.load_config()
    # Remove passwords from response for security
    saved_networks = []
    for network in config.get('saved_networks', []):
        network_copy = network.copy()
        if 'password' in network_copy:
            network_copy['password'] = '********'
        saved_networks.append(network_copy)
    return jsonify(saved_networks)

@app.route('/api/connect', methods=['POST'])
@requires_auth
def connect():
    data = request.json
    result = wifi_manager.connect_to_network(
        data['ssid'], 
        data.get('password'), 
        data.get('security', 'WPA2')
    )
    return jsonify(result)

@app.route('/api/save', methods=['POST'])
@requires_auth
def save():
    data = request.json
    result = wifi_manager.save_network(
        data['ssid'], 
        data['password'], 
        data.get('security', 'WPA2')
    )
    return jsonify(result)

@app.route('/api/forget', methods=['POST'])
@requires_auth
def forget():
    data = request.json
    result = wifi_manager.forget_network(data['ssid'])
    return jsonify(result)

@app.route('/api/diagnostics', methods=['GET'])
@requires_auth
def diagnostics():
    results = wifi_manager.run_diagnostics()
    return jsonify(results)

@app.route('/api/ping', methods=['POST'])
@requires_auth
def ping():
    data = request.json
    target = data.get('target', '8.8.8.8')
    count = min(int(data.get('count', 4)), 10)  # Limit to 10 pings max
    
    command = f"ping -c {count} {target}"
    output = wifi_manager.run_command(command)
    
    # Parse ping results
    ping_times = []
    for line in output.splitlines():
        if "time=" in line:
            try:
                time_str = line.split("time=")[1].split()[0]
                ping_times.append(float(time_str))
            except (IndexError, ValueError):
                pass
    
    result = {
        "success": "0% packet loss" in output,
        "output": output,
        "times": ping_times,
        "stats": {
            "min": min(ping_times) if ping_times else 0,
            "max": max(ping_times) if ping_times else 0,
            "avg": sum(ping_times) / len(ping_times) if ping_times else 0
        }
    }
    
    return jsonify(result)

if __name__ == '__main__':
    # Check if running as root
    if os.geteuid() != 0:
        print("This script must be run as root (sudo).")
        import sys
        sys.exit(1)
    
    # Ensure the logo directory exists
    os.makedirs(os.path.dirname(LOGO_PATH), exist_ok=True)
    
    # Check if logo exists and is a valid image file
    if not os.path.exists(LOGO_PATH):
        print(f"Warning: Logo file not found at {LOGO_PATH}")
        print("A logo file named 'logo.png' should be placed in the 'static/img/' directory.")
        print("Running create_placeholder_logo.py to create a placeholder...")
        try:
            # Try to create a placeholder logo
            import create_placeholder_logo
        except Exception as e:
            print(f"Error creating placeholder logo: {e}")
            # Create a simple text file as placeholder if all else fails
            try:
                with open(LOGO_PATH, 'w') as f:
                    f.write("Placeholder for logo.png")
            except Exception:
                pass
    
    print("Starting JLBMaritime Wi-Fi Manager web server...")
    print("Access the web interface at http://ais.local")
    print("Username: JLBMaritime")
    print("Password: Admin")
    
    app.run(host='0.0.0.0', port=80, debug=False)
