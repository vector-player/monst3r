"""
Blender Script to Animate Empty Object with Position and Rotation from Trajectory File

This script reads a trajectory file (timestamp tx ty tz qx qy qz qw format) and creates
an empty object that animates through the positions and rotations at the specified timestamps.

Usage:
1. In Blender, go to Scripting workspace
2. Open this script: File → Open → select this script
3. Modify the TRAJECTORY_FILE path at the top, or pass as command-line argument
4. Run the script (Alt+P or click Run button)

Alternatively, run from command line:
blender --background --python animate_pos_rot.py -- pred_traj.txt

The script will:
- Create an empty object (or use existing one named "TrajectoryAnimator")
- Read trajectory data from the specified file
- Set location keyframes (tx, ty, tz) at each timestamp
- Set rotation keyframes (qx, qy, qz, qw converted to Blender quaternion) at each timestamp
- Set the scene frame range to match the animation

Note: The trajectory file should be in TUM format:
  timestamp tx ty tz qx qy qz qw
Where quaternion is in TUM format (qx, qy, qz, qw) and will be converted to Blender format (w, x, y, z).
"""

import bpy
import os
import sys
from mathutils import Vector, Quaternion

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default trajectory file path (will be overridden by command-line argument if provided)
TRAJECTORY_FILE = r"D:\ProgramData\monst3r\demo_tmp\lady-running\pred_traj.txt"

# Name for the empty object
EMPTY_OBJECT_NAME = "TrajectoryAnimator"

# Empty object display type (options: 'PLAIN_AXES', 'ARROWS', 'SINGLE_ARROW', 'CIRCLE', 'CUBE', 'SPHERE', 'CONE')
EMPTY_DISPLAY_TYPE = 'ARROWS'  # ARROWS shows orientation better than PLAIN_AXES

# Empty object size
EMPTY_SIZE = 0.1

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_trajectory_file(filepath):
    """Parse trajectory file with format: timestamp tx ty tz qx qy qz qw
    
    Args:
        filepath: Path to the trajectory file
        
    Returns:
        list of tuples: [(timestamp, tx, ty, tz, qx, qy, qz, qw), ...]
    """
    trajectories = []
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Trajectory file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) >= 8:
                try:
                    timestamp = float(parts[0])
                    tx = float(parts[1])
                    ty = float(parts[2])
                    tz = float(parts[3])
                    qx = float(parts[4])
                    qy = float(parts[5])
                    qz = float(parts[6])
                    qw = float(parts[7])
                    trajectories.append((timestamp, tx, ty, tz, qx, qy, qz, qw))
                except ValueError as e:
                    print(f"Warning: Skipping line {line_num}: {line}")
                    print(f"  Error: {e}")
                    continue
            else:
                print(f"Warning: Skipping line {line_num} (insufficient columns): {line}")
    
    return trajectories

# ============================================================================
# ANIMATION FUNCTIONS
# ============================================================================

def create_or_get_empty_object(name, display_type='ARROWS', size=0.1):
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

def tum_quaternion_to_blender(qx, qy, qz, qw):
    """Convert TUM format quaternion (qx, qy, qz, qw) to Blender format (w, x, y, z)
    
    Args:
        qx, qy, qz, qw: TUM format quaternion components
        
    Returns:
        Quaternion: Blender quaternion (w, x, y, z)
    """
    return Quaternion((qw, qx, qy, qz))

def animate_object_trajectory(obj, trajectories):
    """Animate object position and rotation from trajectory data
    
    Args:
        obj: Blender object to animate
        trajectories: List of (timestamp, tx, ty, tz, qx, qy, qz, qw) tuples
        
    Returns:
        tuple: (min_frame, max_frame) - frame range of animation
    """
    if not trajectories:
        print("Error: No trajectories to animate")
        return None, None
    
    # Ensure object is selected and active
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Set object to use quaternion rotation mode
    obj.rotation_mode = 'QUATERNION'
    
    # Set object to use location and rotation keyframes
    obj.animation_data_create()
    obj.animation_data.action = bpy.data.actions.new(name=f"{obj.name}_Action")
    
    # Add keyframes
    min_frame = None
    max_frame = None
    
    for timestamp, tx, ty, tz, qx, qy, qz, qw in trajectories:
        # Convert timestamp to frame number (assuming 1 unit = 1 frame, or use timestamp directly)
        frame = int(timestamp) + 1  # Blender frames start at 1
        
        # Set object location
        obj.location = Vector((tx, ty, tz))
        
        # Convert TUM quaternion (qx, qy, qz, qw) to Blender quaternion (w, x, y, z)
        quat_blender = tum_quaternion_to_blender(qx, qy, qz, qw)
        obj.rotation_quaternion = quat_blender
        
        # Insert keyframes for location
        obj.keyframe_insert(data_path="location", frame=frame, index=0)  # X
        obj.keyframe_insert(data_path="location", frame=frame, index=1)  # Y
        obj.keyframe_insert(data_path="location", frame=frame, index=2)  # Z
        
        # Insert keyframes for rotation (quaternion)
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=0)  # W
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=1)  # X
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=2)  # Y
        obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=3)  # Z
        
        if min_frame is None or frame < min_frame:
            min_frame = frame
        if max_frame is None or frame > max_frame:
            max_frame = frame
    
    print(f"Added {len(trajectories)} keyframes (position + rotation)")
    print(f"Frame range: {min_frame} to {max_frame}")
    
    return min_frame, max_frame

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to animate trajectory"""
    # Get trajectory file path from command-line argument or use default
    trajectory_file = TRAJECTORY_FILE
    
    # Check for command-line arguments
    if '--' in sys.argv:
        argv = sys.argv[sys.argv.index('--') + 1:]
        if len(argv) > 0:
            trajectory_file = argv[0]
            print(f"Using trajectory file from command-line: {trajectory_file}")
    
    if not trajectory_file:
        print("ERROR: No trajectory file specified!")
        print("Please set TRAJECTORY_FILE in the script or pass as command-line argument")
        return
    
    # Parse trajectory file
    print(f"Reading trajectory from: {trajectory_file}")
    try:
        trajectories = parse_trajectory_file(trajectory_file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return
    
    if len(trajectories) == 0:
        print("ERROR: No trajectories found in file")
        return
    
    print(f"Found {len(trajectories)} trajectory entries")
    
    # Show first and last trajectories
    first_timestamp, first_tx, first_ty, first_tz, first_qx, first_qy, first_qz, first_qw = trajectories[0]
    last_timestamp, last_tx, last_ty, last_tz, last_qx, last_qy, last_qz, last_qw = trajectories[-1]
    print(f"First trajectory (t={first_timestamp}):")
    print(f"  Position: [{first_tx:.6f}, {first_ty:.6f}, {first_tz:.6f}]")
    print(f"  Quaternion (TUM): [{first_qx:.6f}, {first_qy:.6f}, {first_qz:.6f}, {first_qw:.6f}]")
    print(f"Last trajectory (t={last_timestamp}):")
    print(f"  Position: [{last_tx:.6f}, {last_ty:.6f}, {last_tz:.6f}]")
    print(f"  Quaternion (TUM): [{last_qx:.6f}, {last_qy:.6f}, {last_qz:.6f}, {last_qw:.6f}]")
    
    # Create or get empty object
    empty_obj = create_or_get_empty_object(EMPTY_OBJECT_NAME, EMPTY_DISPLAY_TYPE, EMPTY_SIZE)
    
    # Animate trajectory
    print("\nAnimating trajectory (position + rotation)...")
    min_frame, max_frame = animate_object_trajectory(empty_obj, trajectories)
    
    if min_frame is not None and max_frame is not None:
        # Set scene frame range
        bpy.context.scene.frame_start = min_frame
        bpy.context.scene.frame_end = max_frame
        bpy.context.scene.frame_set(min_frame)
        
        print(f"\n✓ Animation created successfully!")
        print(f"  Object: {empty_obj.name}")
        print(f"  Frame range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
        print(f"  Keyframes: {len(trajectories)} (position + rotation)")
        print(f"  Rotation mode: QUATERNION")
        print(f"\nPress Space to play animation, or scrub timeline to see movement")
        print(f"The empty object will move and rotate according to the trajectory")
        
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
