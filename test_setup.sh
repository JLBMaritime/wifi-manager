#!/bin/bash

# JLBMaritime Wi-Fi Manager Test Setup Script
# This script sets up a test environment for the Wi-Fi Manager

# Exit on error
set -e

echo "====================================================="
echo "  JLBMaritime Wi-Fi Manager Test Setup"
echo "====================================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3."
    exit 1
fi

# Check for required Python packages
echo "Checking for required Python packages..."
python3 -c "import flask" 2>/dev/null || { 
    echo "Flask is required. Install with: sudo apt install python3-flask"; 
    exit 1; 
}
python3 -c "import PIL" 2>/dev/null || { 
    echo "Pillow is required. Install with: sudo apt install python3-pil"; 
    exit 1; 
}

# Create placeholder logo
echo "Creating placeholder logo..."
python3 create_placeholder_logo.py

echo "====================================================="
echo "Test setup complete!"
echo "====================================================="
echo "To test the web interface (requires root):"
echo "sudo python3 web_interface.py"
echo ""
echo "To test the terminal interface (requires root):"
echo "sudo python3 wifi_manager.py --terminal"
echo ""
echo "Note: This is a test setup only. For production use,"
echo "run the install.sh script to properly install the service."
echo "====================================================="
