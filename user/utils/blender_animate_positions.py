"""
Blender Script to Animate Empty Object from Position File

This script reads a position file (timestamp tx ty tz format) and creates
an empty object that animates through the positions at the specified timestamps.

Usage:
1. In Blender, go to Scripting workspace
2. Open this script: File → Open → select this script
3. Modify the POSITION_FILE path at the top, or pass as command-line argument
4. Run the script (Alt+P or click Run button)

Alternatively, run from command line:
blender --background --python animate_positions.py -- position_openCV.txt

The script will:
- Create an empty object (or use existing one named "PositionAnimator")
- Read position data from the specified file
- Set location keyframes at each timestamp
- Set the scene frame range to match the animation
"""

import bpy
import os
import sys
from mathutils import Vector

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default position file path (will be overridden by command-line argument if provided)
POSITION_FILE = r"D:\ProgramData\monst3r\demo_tmp\lady-running\position_openCV.txt"

# Name for the empty object
EMPTY_OBJECT_NAME = "PositionAnimator"

# Empty object display type (options: 'PLAIN_AXES', 'ARROWS', 'SINGLE_ARROW', 'CIRCLE', 'CUBE', 'SPHERE', 'CONE')
EMPTY_DISPLAY_TYPE = 'PLAIN_AXES'

# Empty object size
EMPTY_SIZE = 0.1

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_position_file(filepath):
    """Parse position file with format: timestamp tx ty tz
    
    Args:
        filepath: Path to the position file
        
    Returns:
        list of tuples: [(timestamp, tx, ty, tz), ...]
    """
    positions = []
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Position file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) >= 4:
                try:
                    timestamp = float(parts[0])
                    tx = float(parts[1])
                    ty = float(parts[2])
                    tz = float(parts[3])
                    positions.append((timestamp, tx, ty, tz))
                except ValueError as e:
                    print(f"Warning: Skipping line {line_num}: {line}")
                    print(f"  Error: {e}")
                    continue
            else:
                print(f"Warning: Skipping line {line_num} (insufficient columns): {line}")
    
    return positions

# ============================================================================
# ANIMATION FUNCTIONS
# ============================================================================

def create_or_get_empty_object(name, display_type='PLAIN_AXES', size=0.1):
    """Create or get an empty object
    
    Args:
        name: Name of the empty object
        display_type: Display type for the empty object
        size: Size of the empty object
        
    Returns:
        bpy.types.Object: The empty object
    """
    # Check if object already exists
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        print(f"Using existing object: {name}")
    else:
        # Create new empty object
        bpy.ops.object.empty_add(type=display_type, location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = name
        obj.empty_display_size = size
        print(f"Created new empty object: {name}")
    
    return obj

def animate_object_positions(obj, positions):
    """Animate object positions from position data
    
    Args:
        obj: Blender object to animate
        positions: List of (timestamp, tx, ty, tz) tuples
        
    Returns:
        tuple: (min_frame, max_frame) - frame range of animation
    """
    if not positions:
        print("Error: No positions to animate")
        return None, None
    
    # Ensure object is selected and active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Set object to use location keyframes
    obj.animation_data_create()
    obj.animation_data.action = bpy.data.actions.new(name=f"{obj.name}_Action")
    
    # Add keyframes
    min_frame = None
    max_frame = None
    
    for timestamp, tx, ty, tz in positions:
        # Convert timestamp to frame number (assuming 1 unit = 1 frame, or use timestamp directly)
        frame = int(timestamp) + 1  # Blender frames start at 1
        
        # Set object location
        obj.location = Vector((tx, ty, tz))
        
        # Insert keyframes for location
        obj.keyframe_insert(data_path="location", frame=frame, index=0)  # X
        obj.keyframe_insert(data_path="location", frame=frame, index=1)  # Y
        obj.keyframe_insert(data_path="location", frame=frame, index=2)  # Z
        
        if min_frame is None or frame < min_frame:
            min_frame = frame
        if max_frame is None or frame > max_frame:
            max_frame = frame
    
    print(f"Added {len(positions)} keyframes")
    print(f"Frame range: {min_frame} to {max_frame}")
    
    return min_frame, max_frame

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to animate positions"""
    # Get position file path from command-line argument or use default
    position_file = POSITION_FILE
    
    # Check for command-line arguments
    if '--' in sys.argv:
        argv = sys.argv[sys.argv.index('--') + 1:]
        if len(argv) > 0:
            position_file = argv[0]
            print(f"Using position file from command-line: {position_file}")
    
    if not position_file:
        print("ERROR: No position file specified!")
        print("Please set POSITION_FILE in the script or pass as command-line argument")
        return
    
    # Parse position file
    print(f"Reading positions from: {position_file}")
    try:
        positions = parse_position_file(position_file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return
    
    if len(positions) == 0:
        print("ERROR: No positions found in file")
        return
    
    print(f"Found {len(positions)} positions")
    
    # Show first and last positions
    first_timestamp, first_tx, first_ty, first_tz = positions[0]
    last_timestamp, last_tx, last_ty, last_tz = positions[-1]
    print(f"First position (t={first_timestamp}): [{first_tx:.6f}, {first_ty:.6f}, {first_tz:.6f}]")
    print(f"Last position (t={last_timestamp}): [{last_tx:.6f}, {last_ty:.6f}, {last_tz:.6f}]")
    
    # Create or get empty object
    empty_obj = create_or_get_empty_object(EMPTY_OBJECT_NAME, EMPTY_DISPLAY_TYPE, EMPTY_SIZE)
    
    # Animate positions
    print("\nAnimating positions...")
    min_frame, max_frame = animate_object_positions(empty_obj, positions)
    
    if min_frame is not None and max_frame is not None:
        # Set scene frame range
        bpy.context.scene.frame_start = min_frame
        bpy.context.scene.frame_end = max_frame
        bpy.context.scene.frame_set(min_frame)
        
        print(f"\n✓ Animation created successfully!")
        print(f"  Object: {empty_obj.name}")
        print(f"  Frame range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
        print(f"  Keyframes: {len(positions)}")
        print(f"\nPress Space to play animation, or scrub timeline to see movement")
        
        # Select the object
        bpy.context.view_layer.objects.active = empty_obj
        empty_obj.select_set(True)
    else:
        print("\n✗ Failed to create animation")

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    main()
