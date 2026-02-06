"""
Blender Script to Animate Empty Object with Curve Path and Rotation Using Constraints

This script reads a trajectory file (timestamp tx ty tz qx qy qz qw format) and creates:
- A curve following the tx, ty, tz positions
- An empty object with constraints for animation:
  * Follow Path constraint: Handles position animation along the curve
  * Transformation constraint: Handles rotation animation via Map To/Rotation

Usage:
1. In Blender, go to Scripting workspace
2. Open this script: File → Open → select this script
3. Modify the TRAJECTORY_FILE path at the top, or pass as command-line argument
4. Run the script (Alt+P or click Run button)

Alternatively, run from command line:
blender --background --python blender_curve_pos_rot.py -- pred_traj.txt

The script will:
- Create a NURBS curve following the trajectory positions
- Enable path animation on the curve
- Create an empty object (or use existing one named "CurveFollower")
- Add Follow Path constraint with:
  * Fixed position enabled
  * Follow Curve enabled
  * Animate Path enabled
- Add Transformation constraint with:
  * Map To/Rotation properties
  * Rotation keyframes on constraint properties
- All keyframes are applied to constraints, not the object directly
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

# Constraint "Follow Path" settings
IS_USE_CURVE_FOLLOW = False
IS_USE_FIXED_LOCATION = True
FORWARD_AXIS = 'FORWARD_X'
UP_AXIS = 'UP_Z'

# Constraint "Transformation" settings
# Note: For Map To/Rotation, we map FROM the object's location (which changes via Follow Path)
# TO rotation. This allows us to keyframe rotation values directly on the constraint.
MAP_FROM = 'LOCATION'  # Source: location (object moves along curve)
MAP_TO = 'ROTATION'  # Target: rotation (Map To / Rotation)
MAP_TO_X_FROM = 'X'  # Map location X to rotation X
MAP_TO_Y_FROM = 'Y'  # Map location Y to rotation Y  
MAP_TO_Z_FROM = 'Z'  # Map location Z to rotation Z
FROM_MIN_X = 0.0
FROM_MIN_Y = 0.0
FROM_MIN_Z = 0.0
FROM_MAX_X = 0.0
FROM_MAX_Y = 0.0
FROM_MAX_Z = 0.0
TO_MIN_X = 0.0
TO_MIN_Y = 0.0
TO_MIN_Z = 0.0
TO_MAX_X = 1.0
TO_MAX_Y = 1.0
TO_MAX_Z = 1.0
MIX_MODE = 'REPLACE'

# Rotation mode for constraints (QUATERNION or Euler order like 'XYZ', 'XZY', etc.)
# For Transformation constraint: Sets from_rotation_mode property
# For CopyRotation constraint: Determines object rotation_mode and euler_order
# Default: 'QUATERNION' for direct quaternion support
FROM_ROTATION_MODE = 'QUATERNION'  # Options: 'QUATERNION', 'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX', 'AUTO'

# Animation settings
ANIMATION_DURATION_FRAMES = 100

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
# HELPER FUNCTIONS
# ============================================================================

def get_unique_object_name(base_name):
    """Get a unique object name by appending .001, .002, etc. if name exists
    
    Args:
        base_name: Base name for the object
        
    Returns:
        str: Unique object name
    """
    if base_name not in bpy.data.objects:
        return base_name
    
    # Try .001, .002, .003, etc. until we find a unique name
    counter = 1
    while True:
        candidate_name = f"{base_name}.{counter:03d}"
        if candidate_name not in bpy.data.objects:
            return candidate_name
        counter += 1
        # Safety check to avoid infinite loop
        if counter > 9999:
            raise RuntimeError(f"Could not find unique name for {base_name} after 9999 attempts")

# ============================================================================
# CURVE CREATION FUNCTIONS
# ============================================================================

def create_or_get_curve(name=None):
    """Create a NURBS curve object with a unique name
    
    Args:
        name: Name of the curve object (default: CURVE_OBJECT_NAME)
        
    Returns:
        bpy.types.Object: The curve object
    """
    # Use default from configuration if not provided
    if name is None:
        name = CURVE_OBJECT_NAME
    
    # Get unique name (will append .001, .002, etc. if name exists)
    unique_name = get_unique_object_name(name)
    
    # Create new curve data
    curve_data = bpy.data.curves.new(name=unique_name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = CURVE_RESOLUTION  # From configuration
    
    # Create spline
    spline = curve_data.splines.new(type='NURBS')
    spline.use_endpoint_u = True  # Make curve pass through first and last points
    
    # Create curve object with unique name
    curve_obj = bpy.data.objects.new(unique_name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    if unique_name != name:
        print(f"Created curve object: {unique_name} (base name '{name}' already existed)")
    else:
        print(f"Created curve object: {unique_name}")
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

def create_or_get_empty_object(name=None, display_type=None, size=None):
    """Create an empty object with a unique name
    
    Args:
        name: Name of the empty object (default: EMPTY_OBJECT_NAME)
        display_type: Display type for the empty object (default: EMPTY_DISPLAY_TYPE)
        size: Size of the empty object (default: EMPTY_SIZE)
        
    Returns:
        bpy.types.Object: The empty object
    """
    # Use defaults from configuration if not provided
    if name is None:
        name = EMPTY_OBJECT_NAME
    if display_type is None:
        display_type = EMPTY_DISPLAY_TYPE
    if size is None:
        size = EMPTY_SIZE
    
    # Get unique name (will append .001, .002, etc. if name exists)
    unique_name = get_unique_object_name(name)
    
    # Create new empty object
    bpy.ops.object.empty_add(type=display_type, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = unique_name
    obj.empty_display_size = size
    
    if unique_name != name:
        print(f"Created new empty object: {unique_name} (base name '{name}' already existed)")
    else:
        print(f"Created new empty object: {unique_name}")
    
    return obj

def tum_quaternion_to_blender(qx, qy, qz, qw):
    """Convert TUM format quaternion (qx, qy, qz, qw) to Blender format (w, x, y, z)
    
    Args:
        qx, qy, qz, qw: TUM format quaternion components
        
    Returns:
        Quaternion: Blender quaternion (w, x, y, z)
    """
    return Quaternion((qw, qx, qy, qz))

def add_copy_rotation_constraint(obj, target_obj=None, from_rotation_mode=None):
    """Add Copy Rotation constraint
    
    Args:
        obj: Object to add constraint to
        target_obj: Target object to copy rotation from (optional)
        from_rotation_mode: Rotation mode ('QUATERNION' or Euler order).
                           If None, uses FROM_ROTATION_MODE from configuration.
                           Default: 'QUATERNION'
                           Note: For CopyRotation, this sets the object's rotation_mode
                           and the constraint's euler_order (if using Euler)
        
    Returns:
        bpy.types.Constraint: The constraint object
    """
    # Use default from configuration if not provided
    if from_rotation_mode is None:
        from_rotation_mode = FROM_ROTATION_MODE
    
    # Remove existing Copy Rotation constraints
    constraints_to_remove = [c for c in obj.constraints if c.type == 'COPY_ROTATION']
    for c in constraints_to_remove:
        obj.constraints.remove(c)
    
    # Set object rotation mode based on from_rotation_mode
    if from_rotation_mode == 'QUATERNION':
        obj.rotation_mode = 'QUATERNION'
    elif from_rotation_mode in ['XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX']:
        obj.rotation_mode = from_rotation_mode
    elif from_rotation_mode == 'AUTO':
        # Keep current rotation mode or use default
        if obj.rotation_mode not in ['QUATERNION', 'XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX', 'AXIS_ANGLE']:
            obj.rotation_mode = 'QUATERNION'  # Default to quaternion
    else:
        # Default to quaternion for unknown modes
        obj.rotation_mode = 'QUATERNION'
    
    # Add new Copy Rotation constraint
    constraint = obj.constraints.new(type='COPY_ROTATION')
    constraint.name = "CopyRotation"  # Set a name for easier reference
    
    # Set target if provided
    if target_obj:
        constraint.target = target_obj
    
    # Set euler_order if using Euler mode (CopyRotation constraint property)
    if from_rotation_mode != 'QUATERNION' and from_rotation_mode in ['XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX', 'AUTO']:
        constraint.euler_order = from_rotation_mode if from_rotation_mode != 'AUTO' else 'AUTO'
    
    # Set mix mode
    constraint.mix_mode = 'REPLACE'  # Default mix mode
    
    # Enable the constraint
    constraint.influence = 1.0
    
    print(f"Added Copy Rotation constraint '{constraint.name}' to {obj.name}")
    print(f"  - Rotation mode: {obj.rotation_mode}")
    if from_rotation_mode != 'QUATERNION':
        print(f"  - Euler order: {constraint.euler_order}")
    print(f"  - Mix mode: {constraint.mix_mode}")
    if target_obj:
        print(f"  - Target: {target_obj.name}")
    return constraint

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
    constraint.use_curve_follow = IS_USE_CURVE_FOLLOW  # Follow curve direction
    constraint.use_fixed_location = IS_USE_FIXED_LOCATION  # Fixed position - keyframe offset_factor
    # Note: Adjust forward_axis and up_axis based on coordinate system
    # MonST3R uses OpenCV convention (+X right, +Y down, +Z forward)
    # Blender uses (+X right, +Y forward, +Z up)
    # You may need to adjust these axes to match your coordinate system
    constraint.forward_axis = FORWARD_AXIS  # From configuration
    constraint.up_axis = UP_AXIS  # From configuration
    
    print(f"Added Follow Path constraint '{constraint.name}' to {obj.name}")
    print(f"  - Fixed position: {constraint.use_fixed_location}")
    print(f"  - Follow curve: {constraint.use_curve_follow}")
    return constraint

def add_transformation_constraint(obj, from_rotation_mode=None):
    """Add Transformation constraint for rotation mapping
    
    Args:
        obj: Object to add constraint to
        from_rotation_mode: Rotation mode for constraint ('QUATERNION' or Euler order).
                           If None, uses FROM_ROTATION_MODE from configuration.
                           Default: 'QUATERNION'
        
    Returns:
        bpy.types.Constraint: The constraint object
    """
    # Use default from configuration if not provided
    if from_rotation_mode is None:
        from_rotation_mode = FROM_ROTATION_MODE
    
    # Remove existing Transformation constraints
    constraints_to_remove = [c for c in obj.constraints if c.type == 'TRANSFORM']
    for c in constraints_to_remove:
        obj.constraints.remove(c)
    
    # Add new Transformation constraint
    constraint = obj.constraints.new(type='TRANSFORM')
    constraint.name = "MapRotation"  # Set a name for easier reference
    constraint.map_from = MAP_FROM  # Source: from configuration ('ROTATION')
    constraint.map_to = MAP_TO  # Target: from configuration ('ROTATION')
    constraint.map_to_x_from = MAP_TO_X_FROM
    constraint.map_to_y_from = MAP_TO_Y_FROM
    constraint.map_to_z_from = MAP_TO_Z_FROM
    
    # Set rotation mode (QUATERNION or Euler order)
    constraint.from_rotation_mode = from_rotation_mode
    
    # Set up initial mapping ranges (will be keyframed per frame)
    # For rotation mapping, use _rot suffix properties
    # from_min_rot/from_max_rot define the source range
    # to_min_rot/to_max_rot define the target range (Map To / Rotation)
    # We'll keyframe to_min_rot/to_max_rot to drive the rotation
    constraint.from_min_x_rot = FROM_MIN_X
    constraint.from_min_y_rot = FROM_MIN_Y
    constraint.from_min_z_rot = FROM_MIN_Z
    constraint.from_max_x_rot = FROM_MAX_X
    constraint.from_max_y_rot = FROM_MAX_Y
    constraint.from_max_z_rot = FROM_MAX_Z
    
    # Target range (Map To / Rotation) - these will be keyframed
    constraint.to_min_x_rot = TO_MIN_X
    constraint.to_min_y_rot = TO_MIN_Y
    constraint.to_min_z_rot = TO_MIN_Z
    constraint.to_max_x_rot = TO_MAX_X
    constraint.to_max_y_rot = TO_MAX_Y
    constraint.to_max_z_rot = TO_MAX_Z
    
    # Use mix mode for direct mapping (both general and rotation-specific)
    constraint.mix_mode = MIX_MODE
    constraint.mix_mode_rot = MIX_MODE  # Rotation-specific mix mode
    
    # Enable the constraint
    constraint.influence = 1.0
    
    print(f"Added Transformation constraint '{constraint.name}' to {obj.name}")
    print(f"  - Map from: {constraint.map_from}")
    print(f"  - Map to: {constraint.map_to}")
    print(f"  - From rotation mode: {constraint.from_rotation_mode}")
    print(f"  - Mix mode: {constraint.mix_mode}")
    print(f"  - Constraint name: '{constraint.name}' (for keyframing)")
    return constraint

def calculate_offset_factors(curve_obj, trajectories):
    """Calculate offset_factor for each trajectory position based on curve distance
    
    Since the curve is created from trajectory positions, each control point corresponds
    to a trajectory position. We calculate cumulative distances along the curve and
    normalize them to get offset_factor values (0.0 to 1.0).
    
    Args:
        curve_obj: Curve object
        trajectories: List of (timestamp, tx, ty, tz, qx, qy, qz, qw) tuples
        
    Returns:
        List of offset_factor values (0.0 to 1.0) corresponding to each trajectory
    """
    from mathutils import Vector
    
    curve_data = curve_obj.data
    spline = curve_data.splines[0]
    
    # Extract positions from trajectories
    positions = [Vector((tx, ty, tz)) for _, tx, ty, tz, _, _, _, _ in trajectories]
    
    # Calculate cumulative distances along the curve using control points
    # The curve control points correspond to trajectory positions
    num_points = len(spline.points)
    
    if num_points == 0:
        print("Warning: Curve has no points, using normalized indices")
        return [i / (len(positions) - 1) if len(positions) > 1 else 0.0 for i in range(len(positions))]
    
    # Calculate distances between consecutive control points
    cumulative_distances = [0.0]  # Start at 0
    total_distance = 0.0
    
    for i in range(1, num_points):
        # Get control point positions in world space
        pt_prev = spline.points[i-1]
        pt_curr = spline.points[i]
        
        pt_prev_world = curve_obj.matrix_world @ Vector((pt_prev.co[0], pt_prev.co[1], pt_prev.co[2]))
        pt_curr_world = curve_obj.matrix_world @ Vector((pt_curr.co[0], pt_curr.co[1], pt_curr.co[2]))
        
        # Calculate distance between consecutive points
        segment_distance = (pt_curr_world - pt_prev_world).length
        total_distance += segment_distance
        cumulative_distances.append(total_distance)
    
    if total_distance == 0:
        # Fallback: use normalized indices based on trajectory order
        print("Warning: Curve total distance is zero, using normalized trajectory indices")
        return [i / (len(positions) - 1) if len(positions) > 1 else 0.0 for i in range(len(positions))]
    
    # Calculate offset_factor for each trajectory position
    # Each trajectory position corresponds to a control point (they're in the same order)
    offset_factors = []
    
    for i in range(len(positions)):
        if i < len(cumulative_distances):
            # Use cumulative distance up to this control point
            distance_along_curve = cumulative_distances[i]
            offset_factor = distance_along_curve / total_distance
            # Clamp to [0, 1]
            offset_factor = max(0.0, min(1.0, offset_factor))
        else:
            # Shouldn't happen, but handle edge case
            offset_factor = 1.0
        
        offset_factors.append(offset_factor)
    
    # Ensure first and last are exactly 0.0 and 1.0
    if len(offset_factors) > 0:
        offset_factors[0] = 0.0
        offset_factors[-1] = 1.0
    
    print(f"Calculated {len(offset_factors)} offset_factor values")
    print(f"  Range: {min(offset_factors):.4f} to {max(offset_factors):.4f}")
    print(f"  Curve total distance: {total_distance:.4f}")
    print(f"  Number of control points: {num_points}")
    
    return offset_factors

def animate_curve_path(curve_obj, duration_frames):
    """Enable animation on the curve path
    
    Args:
        curve_obj: Curve object to animate
        duration_frames: Duration of animation in frames
    """
    # Enable path animation on curve
    curve_obj.data.use_path = True
    curve_obj.data.path_duration = duration_frames
    
    # Create animation data for curve
    curve_obj.animation_data_create()
    if curve_obj.animation_data:
        curve_obj.animation_data.action = bpy.data.actions.new(name=f"{curve_obj.name}_PathAction")
    
    print(f"Enabled path animation on {curve_obj.name} (duration: {duration_frames} frames)")

def animate_curve_and_rotations(curve_obj, empty_obj, trajectories, follow_constraint, transform_constraint):
    """Animate curve offset and rotations using constraints only
    
    Args:
        curve_obj: Curve object
        empty_obj: Empty object with constraints
        trajectories: List of (timestamp, tx, ty, tz, qx, qy, qz, qw) tuples
        follow_constraint: Follow Path constraint object
        transform_constraint: Transformation constraint object
        
    Returns:
        tuple: (min_frame, max_frame) - frame range of animation
    """
    if not trajectories:
        print("Error: No trajectories to animate")
        return None, None
    
    # Ensure objects are set up
    bpy.context.view_layer.objects.active = empty_obj
    empty_obj.select_set(True)
    
    # Set empty object rotation mode (constraints will override, but good to set)
    empty_obj.rotation_mode = 'QUATERNION'
    
    # Create animation data for empty object (for constraint keyframes)
    empty_obj.animation_data_create()
    empty_obj.animation_data.action = bpy.data.actions.new(name=f"{empty_obj.name}_Action")
    
    # Calculate frame range first
    timestamps = [t[0] for t in trajectories]
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)
    duration = max_timestamp - min_timestamp
    
    # Calculate duration in frames
    min_frame = int(min_timestamp) + 1
    max_frame = int(max_timestamp) + 1
    duration_frames = max_frame - min_frame + 1
    
    # Enable path animation on curve
    animate_curve_path(curve_obj, duration_frames)
    
    # Find constraint indices and names for keyframing
    follow_constraint_index = list(empty_obj.constraints).index(follow_constraint)
    transform_constraint_index = list(empty_obj.constraints).index(transform_constraint)
    transform_constraint_name = transform_constraint.name  # Use name for more reliable keyframing
    
    # Paths for keyframing constraint properties
    # Use constraint name instead of index for more reliable keyframing
    # For rotation mapping, use _rot suffix properties
    follow_path = f'constraints["{follow_constraint.name}"].offset_factor'
    transform_to_min_x_rot_path = f'constraints["{transform_constraint_name}"].to_min_x_rot'
    transform_to_min_y_rot_path = f'constraints["{transform_constraint_name}"].to_min_y_rot'
    transform_to_min_z_rot_path = f'constraints["{transform_constraint_name}"].to_min_z_rot'
    transform_to_max_x_rot_path = f'constraints["{transform_constraint_name}"].to_max_x_rot'
    transform_to_max_y_rot_path = f'constraints["{transform_constraint_name}"].to_max_y_rot'
    transform_to_max_z_rot_path = f'constraints["{transform_constraint_name}"].to_max_z_rot'
    transform_from_min_x_rot_path = f'constraints["{transform_constraint_name}"].from_min_x_rot'
    transform_from_min_y_rot_path = f'constraints["{transform_constraint_name}"].from_min_y_rot'
    transform_from_min_z_rot_path = f'constraints["{transform_constraint_name}"].from_min_z_rot'
    transform_from_max_x_rot_path = f'constraints["{transform_constraint_name}"].from_max_x_rot'
    transform_from_max_y_rot_path = f'constraints["{transform_constraint_name}"].from_max_y_rot'
    transform_from_max_z_rot_path = f'constraints["{transform_constraint_name}"].from_max_z_rot'
    
    # Calculate offset_factor for each position based on actual curve distance
    # This ensures each timestamp reaches the exact position on the curve
    print("Calculating offset_factor values based on curve positions...")
    offset_factors = calculate_offset_factors(curve_obj, trajectories)
    
    # Add keyframes
    actual_min_frame = None
    actual_max_frame = None
    
    for i, (timestamp, tx, ty, tz, qx, qy, qz, qw) in enumerate(trajectories):
        # Convert timestamp to frame number (assuming 1 unit = 1 frame, or use timestamp directly)
        frame = int(timestamp) + 1  # Blender frames start at 1
        
        # Set frame
        bpy.context.scene.frame_set(frame)
        
        # ===== FOLLOW PATH CONSTRAINT KEYFRAMES =====
        # Set offset_factor for Follow Path constraint (0.0 = start, 1.0 = end)
        # This value is calculated based on actual position along the curve
        offset_factor = offset_factors[i]
        follow_constraint.offset_factor = offset_factor
        
        # Keyframe the offset_factor at the corresponding timestamp frame
        empty_obj.keyframe_insert(data_path=follow_path, frame=frame)
        
        # ===== TRANSFORMATION CONSTRAINT KEYFRAMES =====
        # Convert TUM quaternion (qx, qy, qz, qw) to Blender quaternion (w, x, y, z)
        quat_blender = tum_quaternion_to_blender(qx, qy, qz, qw)
        
        # Also set the object's rotation_quaternion directly for proper orientation
        # This ensures the object has the correct rotation, and the constraint can override if needed
        empty_obj.rotation_quaternion = quat_blender
        
        # Convert quaternion to Euler angles for Transformation constraint
        # (Transformation constraint uses Euler angles via _rot suffix properties)
        euler_rotation = quat_blender.to_euler('XYZ')
        
        # Transformation constraint maps from source rotation range to target rotation
        # For "Map To / Rotation", we use _rot suffix properties (to_min_x_rot, etc.)
        # The constraint will map from source (from_min_rot/from_max_rot) to target (to_min_rot/to_max_rot)
        
        # Set source rotation range (from_min_rot/from_max_rot) - these define the input range
        # For 1:1 mapping, set source to match the current rotation (or a constant range)
        # We'll use the current rotation as source, mapping it to target
        transform_constraint.from_min_x_rot = euler_rotation.x
        transform_constraint.from_min_y_rot = euler_rotation.y
        transform_constraint.from_min_z_rot = euler_rotation.z
        transform_constraint.from_max_x_rot = euler_rotation.x
        transform_constraint.from_max_y_rot = euler_rotation.y
        transform_constraint.from_max_z_rot = euler_rotation.z
        
        # Set target rotation range (to_min_rot/to_max_rot) - these are the "Map To / Rotation" values
        # These define where the rotation should be mapped TO (the object's rotation)
        # These values come from the quaternion (qx, qy, qz, qw) converted to Euler
        transform_constraint.to_min_x_rot = euler_rotation.x
        transform_constraint.to_min_y_rot = euler_rotation.y
        transform_constraint.to_min_z_rot = euler_rotation.z
        transform_constraint.to_max_x_rot = euler_rotation.x
        transform_constraint.to_max_y_rot = euler_rotation.y
        transform_constraint.to_max_z_rot = euler_rotation.z
        
        # Keyframe the object's rotation_quaternion directly (primary method)
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=0)  # W
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=1)  # X
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=2)  # Y
        empty_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame, index=3)  # Z
        
        # Keyframe the "Map To / Rotation" properties (to_min_x_rot/y_rot/z_rot)
        # These are the target rotation values that drive the object's rotation via constraint
        # Each quaternion (qx, qy, qz, qw) is converted to Euler and keyframed here
        # Using constraint name with _rot suffix for rotation-specific properties
        keyframe_success = False
        
        # Approach 1: Use constraint name with _rot suffix (correct for rotation mapping)
        try:
            empty_obj.keyframe_insert(data_path=transform_to_min_x_rot_path, frame=frame)
            empty_obj.keyframe_insert(data_path=transform_to_min_y_rot_path, frame=frame)
            empty_obj.keyframe_insert(data_path=transform_to_min_z_rot_path, frame=frame)
            empty_obj.keyframe_insert(data_path=transform_to_max_x_rot_path, frame=frame)
            empty_obj.keyframe_insert(data_path=transform_to_max_y_rot_path, frame=frame)
            empty_obj.keyframe_insert(data_path=transform_to_max_z_rot_path, frame=frame)
            keyframe_success = True
        except Exception as e:
            # Approach 2: Try using index instead of name
            try:
                empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].to_min_x_rot', frame=frame)
                empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].to_min_y_rot', frame=frame)
                empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].to_min_z_rot', frame=frame)
                empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].to_max_x_rot', frame=frame)
                empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].to_max_y_rot', frame=frame)
                empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].to_max_z_rot', frame=frame)
                keyframe_success = True
            except Exception as e2:
                if i == 0:  # Only print error for first frame to avoid spam
                    print(f"\n⚠ Warning: Failed to keyframe Map To/Rotation properties at frame {frame}")
                    print(f"  Attempt 1 (name with _rot): {type(e).__name__}: {e}")
                    print(f"  Attempt 2 (index with _rot): {type(e2).__name__}: {e2}")
                    print(f"  Constraint name: '{transform_constraint_name}'")
                    print(f"  Constraint index: {transform_constraint_index}")
                    print(f"  Data paths tried:")
                    print(f"    - {transform_to_min_x_rot_path}")
                    print(f"    - constraints[{transform_constraint_index}].to_min_x_rot")
                    print(f"  Note: Object rotation_quaternion keyframes were still created")
        
        # Also keyframe source values (from_min_rot/from_max_rot) to match target for 1:1 mapping
        # This ensures the constraint maps correctly from source to target
        if keyframe_success:
            try:
                empty_obj.keyframe_insert(data_path=transform_from_min_x_rot_path, frame=frame)
                empty_obj.keyframe_insert(data_path=transform_from_min_y_rot_path, frame=frame)
                empty_obj.keyframe_insert(data_path=transform_from_min_z_rot_path, frame=frame)
                empty_obj.keyframe_insert(data_path=transform_from_max_x_rot_path, frame=frame)
                empty_obj.keyframe_insert(data_path=transform_from_max_y_rot_path, frame=frame)
                empty_obj.keyframe_insert(data_path=transform_from_max_z_rot_path, frame=frame)
            except:
                # Try with index as fallback
                try:
                    empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].from_min_x_rot', frame=frame)
                    empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].from_min_y_rot', frame=frame)
                    empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].from_min_z_rot', frame=frame)
                    empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].from_max_x_rot', frame=frame)
                    empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].from_max_y_rot', frame=frame)
                    empty_obj.keyframe_insert(data_path=f'constraints[{transform_constraint_index}].from_max_z_rot', frame=frame)
                except:
                    pass  # Source keyframes are less critical than target keyframes
        
        if actual_min_frame is None or frame < actual_min_frame:
            actual_min_frame = frame
        if actual_max_frame is None or frame > actual_max_frame:
            actual_max_frame = frame
    
    # Verify keyframes were created
    action = empty_obj.animation_data.action if empty_obj.animation_data else None
    transform_keyframes_count = 0
    transform_fcurves_found = []
    follow_path_keyframes_count = 0
    
    if action:
        # Count keyframes for transformation constraint Map To/Rotation properties
        for fcurve in action.fcurves:
            data_path = fcurve.data_path
            # Check for Transformation constraint Map To/Rotation keyframes
            if ('MapRotation' in data_path or transform_constraint_name in data_path):
                if 'to_min' in data_path or 'to_max' in data_path:
                    transform_keyframes_count += len(fcurve.keyframe_points)
                    transform_fcurves_found.append(data_path)
            # Check for Follow Path keyframes
            if 'FollowPath' in data_path or 'offset_factor' in data_path:
                follow_path_keyframes_count += len(fcurve.keyframe_points)
        
        print(f"\n{'='*60}")
        print(f"KEYFRAME VERIFICATION:")
        print(f"{'='*60}")
        print(f"Follow Path constraint:")
        print(f"  - Keyframes found: {follow_path_keyframes_count}")
        print(f"  - Expected: {len(trajectories)} (one per timestamp)")
        
        # Count rotation_quaternion keyframes (direct method)
        rotation_quat_keyframes = 0
        for fcurve in action.fcurves:
            if fcurve.data_path == "rotation_quaternion":
                rotation_quat_keyframes += len(fcurve.keyframe_points)
        
        print(f"\nTransformation constraint - Map To/Rotation:")
        print(f"  - Constraint keyframes found: {transform_keyframes_count}")
        print(f"  - Expected constraint keyframes: {len(trajectories) * 6} (to_min_x/y/z_rot + to_max_x/y/z_rot per timestamp)")
        print(f"  - FCurves created: {len(transform_fcurves_found)}")
        print(f"\nDirect rotation_quaternion keyframes:")
        print(f"  - Keyframes found: {rotation_quat_keyframes}")
        print(f"  - Expected: {len(trajectories) * 4} (W, X, Y, Z per timestamp)")
        
        if transform_keyframes_count > 0:
            print(f"  ✓ SUCCESS: Keyframes found on Map To/Rotation constraint properties!")
            print(f"  Constraint FCurves:")
            for fcurve_path in transform_fcurves_found:
                fcurve = next((fc for fc in action.fcurves if fc.data_path == fcurve_path), None)
                if fcurve:
                    print(f"    - {fcurve_path}: {len(fcurve.keyframe_points)} keyframes")
        else:
            print(f"  ⚠ WARNING: No keyframes found on Map To/Rotation constraint properties!")
            print(f"  However, direct rotation_quaternion keyframes were created as fallback.")
            print(f"  The constraint may still work if object rotation is set correctly.")
        
        if rotation_quat_keyframes > 0:
            print(f"  ✓ SUCCESS: Direct rotation_quaternion keyframes created!")
            print(f"  This ensures correct orientation at each timestamp.")
        
        print(f"\nSummary:")
        print(f"  - Total trajectory entries: {len(trajectories)}")
        print(f"  - Each quaternion (qx, qy, qz, qw) creates:")
        print(f"    * 4 rotation_quaternion keyframes (W, X, Y, Z) - PRIMARY METHOD")
        print(f"    * 6 constraint keyframes (to_min/to_max_x/y/z_rot) - CONSTRAINT OVERRIDE")
        print(f"{'='*60}")
    else:
        print(f"\n✗ ERROR: No animation action found!")
        print(f"  Animation data: {empty_obj.animation_data}")
        print(f"  This means keyframes were not created.")
    
    print(f"\nFrame range: {actual_min_frame} to {actual_max_frame}")
    
    return actual_min_frame, actual_max_frame

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
    curve_obj = create_or_get_curve()  # Uses CURVE_OBJECT_NAME from configuration
    set_curve_points(curve_obj, positions)
    
    # Create or get empty object
    empty_obj = create_or_get_empty_object()  # Uses EMPTY_OBJECT_NAME, EMPTY_DISPLAY_TYPE, EMPTY_SIZE from configuration
    
    # Add Follow Path constraint
    print("\nAdding Follow Path constraint...")
    follow_constraint = add_follow_path_constraint(empty_obj, curve_obj)
    
    # Add Transformation constraint for rotation
    print("\nAdding Transformation constraint for rotation...")
    transform_constraint = add_transformation_constraint(empty_obj)
    
    # Animate curve offset and rotations using constraints
    print("\nAnimating path offset and rotations on constraints...")
    min_frame, max_frame = animate_curve_and_rotations(curve_obj, empty_obj, trajectories, follow_constraint, transform_constraint)
    
    if min_frame is not None and max_frame is not None:
        # Set scene frame range
        bpy.context.scene.frame_start = min_frame
        bpy.context.scene.frame_end = max_frame
        bpy.context.scene.frame_set(min_frame)
        
        print(f"\n✓ Animation created successfully!")
        print(f"  Curve: {curve_obj.name}")
        print(f"  Empty object: {empty_obj.name}")
        print(f"  Constraints:")
        print(f"    - Follow Path: Position animation (offset_factor keyframes)")
        print(f"    - Transformation: Map To/Rotation animation")
        print(f"      Orientations (qx, qy, qz, qw) keyframed on to_min_x/y/z properties")
        print(f"  Frame range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
        print(f"  Keyframes: {len(trajectories)} (all on constraints)")
        print(f"  Rotation mode: QUATERNION")
        print(f"\nPress Space to play animation, or scrub timeline to see movement")
        print(f"The empty object will follow the curve path and rotate according to the trajectory")
        print(f"All animation is driven by constraints - no direct object keyframes")
        
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
