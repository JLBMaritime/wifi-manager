#!/usr/bin/env python3
"""
This script creates a placeholder logo file.
The actual logo should be replaced with the real logo later.
"""

import os
import sys

# Create directory if it doesn't exist
img_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'img')
os.makedirs(img_dir, exist_ok=True)

# Create a placeholder logo
logo_path = os.path.join(img_dir, 'logo.png')

try:
    # Try to use PIL to create an image
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL (Pillow) is not installed. Please install it with: sudo apt install python3-pil")
        print("Creating a text file placeholder instead...")
        with open(logo_path, 'w') as f:
            f.write("This is a placeholder for the logo.png file.\n")
            f.write("Please replace this with the actual logo image.\n")
        sys.exit(0)

    # Create a 200x100 image with the specified primary color
    img = Image.new('RGB', (200, 100), color='#1c2346')
    draw = ImageDraw.Draw(img)

    # Add text
    try:
        # Try to use a system font
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except IOError:
        # Fall back to default font
        font = ImageFont.load_default()

    draw.text((20, 40), "JLBMaritime", fill="#ffffff", font=font)

    # Save the image
    img.save(logo_path)

    print(f"Created placeholder logo at {logo_path}")
    print("Replace this with the actual logo when available.")

except Exception as e:
    print(f"Error creating logo: {e}")
    print("Creating a text file placeholder instead...")
    try:
        with open(logo_path, 'w') as f:
            f.write("This is a placeholder for the logo.png file.\n")
            f.write("Please replace this with the actual logo image.\n")
    except Exception as e2:
        print(f"Error creating text placeholder: {e2}")
