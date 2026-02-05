"""
Blender Script to Animate Empty Object with Curve Path and Rotation

This script reads a trajectory file (timestamp tx ty tz qx qy qz qw format) and creates:
- A curve following the tx, ty, tz positions
- An empty object with a Follow Path constraint following that curve
- Quaternion rotations (qx, qy, qz, qw) keyframed on the empty object, synchronized with the curve

Usage:
1. In Blender, go to Scripting workspace
2. Open this script: File → Open → select this script
3. Modify the TRAJECTORY_FILE path at the top, or pass as command-line argument
4. Run the script (Alt+P or click Run button)

Alternatively, run from command line:
blender --background --python blender_curve_pos_rot.py -- pred_traj.txt

The script will:
- Create a NURBS curve following the trajectory positions
- Create an empty object (or use existing one named "CurveFollower")
- Add a Follow Path constraint to the empty object
- Keyframe rotations (qx, qy, qz, qw) on the empty object synchronized with curve movement
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

# Name for the curve object
CURVE_OBJECT_NAME = "TrajectoryCurve"

# Name for the empty object
EMPTY_OBJECT_NAME = "CurveFollower"

# Empty object display type (options: 'PLAIN_AXES', 'ARROWS', 'SINGLE_ARROW', 'CIRCLE', 'CUBE', 'SPHERE', 'CONE')
EMPTY_DISPLAY_TYPE = 'ARROWS'  # ARROWS shows orientation better than PLAIN_AXES

# Empty object size
EMPTY_SIZE = 0.1

# Curve resolution (number of points per segment)
CURVE_RESOLUTION = 64

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
# CURVE CREATION FUNCTIONS
# ============================================================================

def create_or_get_curve(name):
    """Create or get a NURBS curve object
    
    Args:
        name: Name of the curve object
        
    Returns:
        bpy.types.Object: The curve object
    """
    # Check if curve already exists
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        # Clear existing curve data
        if obj.type == 'CURVE':
            bpy.data.curves.remove(obj.data, do_unlink=True)
        else:
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Create new curve
    curve_data = bpy.data.curves.new(name=name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = CURVE_RESOLUTION
    
    # Create spline
    spline = curve_data.splines.new(type='NURBS')
    spline.use_endpoint_u = True  # Make curve pass through first and last points
    
    # Create curve object
    curve_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    print(f"Created curve object: {name}")
    return curve_obj

def set_curve_points(curve_obj, positions):
    """Set curve control points from positions
    
    Args:
        curve_obj: Curve object
        positions: List of (tx, ty, tz) tuples
    """
    curve_data = curve_obj.data
    spline = curve_data.splines[0]
    
    # Set number of points
    num_points = len(positions)
    spline.points.add(num_points - 1)  # Spline starts with 1 point
    
    # Set point coordinates
    for i, (tx, ty, tz) in enumerate(positions):
        spline.points[i].co = (tx, ty, tz, 1.0)  # 4D coordinate (x, y, z, weight)
    
    print(f"Set {num_points} points on curve")

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

def add_follow_path_constraint(obj, target_curve):
    """Add Follow Path constraint to object
    
    Args:
        obj: Object to add constraint to
        target_curve: Curve object to follow
        
    Returns:
        bpy.types.Constraint: The constraint object
    """
    # Remove existing Follow Path constraints
    constraints_to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH']
    for c in constraints_to_remove:
        obj.constraints.remove(c)
    
    # Add new Follow Path constraint
    constraint = obj.constraints.new(type='FOLLOW_PATH')
    constraint.name = "FollowPath"  # Set a name for easier reference
    constraint.target = target_curve
    constraint.use_curve_follow = True  # Follow curve direction
    # Note: Adjust forward_axis and up_axis based on coordinate system
    # MonST3R uses OpenCV convention (+X right, +Y down, +Z forward)
    # Blender uses (+X right, +Y forward, +Z up)
    # You may need to adjust these axes to match your coordinate system
    constraint.forward_axis = 'FORWARD_X'  # Adjust based on coordinate system
    constraint.up_axis = 'UP_Z'
    
    print(f"Added Follow Path constraint '{constraint.name}' to {obj.name}")
    return constraint

def animate_curve_and_rotations(curve_obj, empty_obj, trajectories, follow_constraint):
    """Animate curve offset and rotations
    
    Args:
        curve_obj: Curve object
        empty_obj: Empty object with Follow Path constraint
        trajectories: List of (timestamp, tx, ty, tz, qx, qy, qz, qw) tuples
        follow_constraint: Follow Path constraint object
        
    Returns:
        tuple: (min_frame, max_frame) - frame range of animation
    """
    if not trajectories:
        print("Error: No trajectories to animate")
        return None, None
    
    # Ensure objects are set up
    bpy.context.view_layer.objects.active = empty_obj
    empty_obj.select_set(True)
    
    # Set empty object to use quaternion rotation mode
    empty_obj.rotation_mode = 'QUATERNION'
    
    # Create animation data
    empty_obj.animation_data_create()
    empty_obj.animation_data.action = bpy.data.actions.new(name=f"{empty_obj.name}_Action")
    
    # Find constraint index once for keyframing
    constraint_index = list(empty_obj.constraints).index(follow_constraint)
    constraint_path = f'constraints[{constraint_index}].offset_factor'
    
    # Calculate frame range
    timestamps = [t[0] for t in trajectories]
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)
    duration = max_timestamp - min_timestamp
    
    # Normalize timestamps to 0-1 range for offset_factor
    normalized_timestamps = [(t[0] - min_timestamp) / duration if duration > 0 else 0.0 for t in trajectories]
    
    # Add keyframes
    min_frame = None
    max_frame = None
    
    for i, (timestamp, tx, ty, tz, qx, qy, qz, qw) in enumerate(trajectories):
        # Convert timestamp to frame number (assuming 1 unit = 1 frame, or use timestamp directly)
        frame = int(timestamp) + 1  # Blender frames start at 1
        
        # Set frame
        bpy.context.scene.frame_set(frame)
        
        # Set offset_factor for Follow Path constraint (0.0 = start, 1.0 = end)
        offset_factor = normalized_timestamps[i]
        follow_constraint.offset_factor = offset_factor
        
        # Keyframe the offset_factor (constraint properties are keyframed on the object)
        empty_obj.keyframe_insert(data_path=constraint_path, frame=frame)
        
        # Convert TUM quaternion (qx, qy, qz, qw) to Blender quaternion (w, x, y, z)
        quat_blender = tum_quaternion_to_blender(qx, qy, qz, qw)
        empty_obj.rotation_quaternion = quat_blender
        
        # Insert keyframes for rotation (quaternion)
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=0)  # W
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=1)  # X
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=2)  # Y
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=3)  # Z
        
        if min_frame is None or frame < min_frame:
            min_frame = frame
        if max_frame is None or frame > max_frame:
            max_frame = frame
    
    print(f"Added {len(trajectories)} keyframes (path offset + rotation)")
    print(f"Frame range: {min_frame} to {max_frame}")
    
    return min_frame, max_frame

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to create curve path animation"""
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
    
    # Extract positions and quaternions
    positions = [(tx, ty, tz) for _, tx, ty, tz, _, _, _, _ in trajectories]
    
    # Show first and last trajectories
    first_timestamp, first_tx, first_ty, first_tz, first_qx, first_qy, first_qz, first_qw = trajectories[0]
    last_timestamp, last_tx, last_ty, last_tz, last_qx, last_qy, last_qz, last_qw = trajectories[-1]
    print(f"First trajectory (t={first_timestamp}):")
    print(f"  Position: [{first_tx:.6f}, {first_ty:.6f}, {first_tz:.6f}]")
    print(f"  Quaternion (TUM): [{first_qx:.6f}, {first_qy:.6f}, {first_qz:.6f}, {first_qw:.6f}]")
    print(f"Last trajectory (t={last_timestamp}):")
    print(f"  Position: [{last_tx:.6f}, {last_ty:.6f}, {last_tz:.6f}]")
    print(f"  Quaternion (TUM): [{last_qx:.6f}, {last_qy:.6f}, {last_qz:.6f}, {last_qw:.6f}]")
    
    # Create curve from positions
    print("\nCreating curve from positions...")
    curve_obj = create_or_get_curve(CURVE_OBJECT_NAME)
    set_curve_points(curve_obj, positions)
    
    # Create or get empty object
    empty_obj = create_or_get_empty_object(EMPTY_OBJECT_NAME, EMPTY_DISPLAY_TYPE, EMPTY_SIZE)
    
    # Add Follow Path constraint
    print("\nAdding Follow Path constraint...")
    follow_constraint = add_follow_path_constraint(empty_obj, curve_obj)
    
    # Animate curve offset and rotations
    print("\nAnimating path offset and rotations...")
    min_frame, max_frame = animate_curve_and_rotations(curve_obj, empty_obj, trajectories, follow_constraint)
    
    if min_frame is not None and max_frame is not None:
        # Set scene frame range
        bpy.context.scene.frame_start = min_frame
        bpy.context.scene.frame_end = max_frame
        bpy.context.scene.frame_set(min_frame)
        
        print(f"\n✓ Animation created successfully!")
        print(f"  Curve: {curve_obj.name}")
        print(f"  Empty object: {empty_obj.name}")
        print(f"  Constraint: Follow Path")
        print(f"  Frame range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
        print(f"  Keyframes: {len(trajectories)} (path offset + rotation)")
        print(f"  Rotation mode: QUATERNION")
        print(f"\nPress Space to play animation, or scrub timeline to see movement")
        print(f"The empty object will follow the curve path and rotate according to the trajectory")
        
        # Select both objects
        bpy.context.view_layer.objects.active = empty_obj
        empty_obj.select_set(True)
        curve_obj.select_set(True)
    else:
        print("\n✗ Failed to create animation")

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    main()
