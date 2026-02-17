#!/usr/bin/env python3
"""
Simple icon generator for FanControl_GUI
Creates a colorful RGB fan icon
Run this once to generate app.ico
"""

from PIL import Image, ImageDraw
import os

def create_fan_icon():
    """Create a simple fan-themed icon"""
    
    # Create image
    size = 256
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # Draw background circle (dark)
    draw.ellipse([20, 20, size-20, size-20], fill='#1a1a2e', outline='#16213e', width=3)
    
    # Draw fan blades (3 colored blades)
    blade_colors = ['#FF1744', '#00E676', '#2979F0']  # Red, Green, Blue
    
    for i, color in enumerate(blade_colors):
        angle = i * 120
        # Simple blade as polygon
        blade_points = [
            (center, center - 60),
            (center - 20, center - 40),
            (center + 20, center - 40),
        ]
        draw.polygon(blade_points, fill=color, outline='#fff')
        
        # Rotate effect with overlapping
        for j in range(1, 3):
            offset = j * 10
            blade_poly = [
                (center, center - 60 + offset),
                (center - 15, center - 35 + offset),
                (center + 15, center - 35 + offset),
            ]
            draw.polygon(blade_poly, fill=color)
    
    # Draw center circle
    center_radius = 20
    draw.ellipse([center-center_radius, center-center_radius, 
                  center+center_radius, center+center_radius], 
                 fill='#FFFFFF', outline='#000', width=2)
    
    # Draw RGB text
    draw.text((center-30, center-8), "RGB", fill='#000')
    
    # Save as ICO
    ico_path = os.path.join(os.path.dirname(__file__), 'app.ico')
    img.save(ico_path, 'ICO', sizes=[(256, 256)])
    
    print(f"✅ Icon created: {ico_path}")
    print("You can now use --icon=app.ico with PyInstaller!")
    return ico_path

if __name__ == "__main__":
    try:
        create_fan_icon()
    except ImportError:
        print("❌ PIL library not found!")
        print("Install it with: pip install pillow")
        print("\nAlternatively, create app.ico manually:")
        print("1. Use any image editor to create a 256x256 pixel image")
        print("2. Save as PNG")
        print("3. Convert to ICO at: https://convertio.co/png-ico/")
        print("4. Save as 'app.ico' in this folder")
