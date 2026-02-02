"""
Blender Script to Compute Expected Camera Transforms Step-by-Step

This script computes camera transforms step-by-step matching the GLB export process.
It reads pred_traj.txt and pred_intrinsics.txt, then computes transformations at
each step to compare with ground truth from GLB geometry.

Usage:
1. Set MONST3R_OUTPUT_DIR at the top of the script
2. Open Blender Scripting workspace
3. Open this script: File → Open → select this script
4. Run the script (Alt+P or click Run button)

The script will:
- Read camera poses from pred_traj.txt
- Read intrinsics from pred_intrinsics.txt
- Compute transforms at each step:
  1. Build c2w from TUM pose
  2. Apply OPENGL
  3. Apply aspect_ratio
  4. Apply rot45
  5. Apply scene normalization
- Save intermediate results to JSON: computed_transforms.json
"""

import bpy
import os
import json
from mathutils import Vector, Matrix, Quaternion, Euler
import math

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to MonST3R output directory (where pred_traj.txt is located)
MONST3R_OUTPUT_DIR = None  # e.g., "/root/monst3r/demo_tmp/lady-running"

OUTPUT_FILE = "computed_transforms.json"  # Output JSON file path
SCREEN_WIDTH = 0.03  # Camera frustum size (should match GLB export, default 0.03)

# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_tum_trajectory(filepath):
    """Parse TUM format trajectory file
    
    Format: timestamp tx ty tz qx qy qz qw
    Returns: list of (timestamp, position, quaternion) tuples
    """
    poses = []
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Trajectory file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 8:
                try:
                    timestamp = float(parts[0])
                    pos = [float(parts[1]), float(parts[2]), float(parts[3])]
                    # TUM format: qx qy qz qw
                    quat = [float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])]
                    poses.append((timestamp, pos, quat))
                except ValueError:
                    continue
    return poses

def parse_intrinsics(filepath):
    """Parse intrinsics file
    
    Format: fx 0 cx 0 fy cy 0 0 1 (3x3 matrix flattened)
    Returns: list of (fx, fy, cx, cy) tuples
    """
    intrinsics = []
    if not os.path.exists(filepath):
        return intrinsics
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 9:
                try:
                    fx = float(parts[0])
                    fy = float(parts[4])
                    cx = float(parts[2])
                    cy = float(parts[5])
                    intrinsics.append((fx, fy, cx, cy))
                except ValueError:
                    continue
    return intrinsics

# ============================================================================
# TRANSFORMATION FUNCTIONS
# ============================================================================

def matrix_to_list(matrix):
    """Convert Blender Matrix to list of lists"""
    if hasattr(matrix, 'to_4x4'):
        matrix = matrix.to_4x4()
    return [[matrix[i][j] for j in range(len(matrix[0]))] for i in range(len(matrix))]

def compute_transform_step_by_step(pos, quat, focal=None, image_size=None, first_c2w=None, screen_width=0.03):
    """Compute transform at each step matching GLB export process
    
    Returns dict with intermediate transforms at each step
    """
    # OPENGL transformation matrix (inverts Y and Z)
    OPENGL = Matrix([
        [1, 0, 0, 0],
        [0, -1, 0, 0],
        [0, 0, -1, 0],
        [0, 0, 0, 1]
    ])
    
    # Y-axis 180 rotation (as used in GLB export)
    rot_y180 = Euler((0, math.radians(180), 0), 'XYZ').to_matrix().to_4x4()
    
    # Convert TUM quaternion (qx, qy, qz, qw) to Blender format (w, x, y, z)
    quat_blender = Quaternion([quat[3], quat[0], quat[1], quat[2]])
    
    # Step 1: Build c2w from TUM pose
    c2w = Matrix.Translation(Vector(pos))
    c2w = c2w @ quat_blender.to_matrix().to_4x4()
    
    # Step 2: Apply OPENGL
    c2w_opengl = c2w @ OPENGL
    
    # Step 3: Apply aspect_ratio (if we have image info)
    aspect_ratio = Matrix.Identity(4)
    if image_size:
        W, H = image_size[0], image_size[1]
        aspect_ratio[0][0] = W / H
    
    c2w_opengl_aspect = c2w_opengl @ aspect_ratio
    
    # Step 4: Apply rot45
    rot45 = Matrix.Identity(4)
    height = screen_width / 10.0  # Default height
    if focal and image_size:
        W, H = image_size[0], image_size[1]
        fx = focal[0] if isinstance(focal, (list, tuple)) else focal
        height = max(screen_width / 10.0, fx * screen_width / H)
    
    rot45_z = Euler((0, 0, math.radians(45)), 'XYZ').to_matrix().to_4x4()
    rot45 = rot45_z.copy()
    rot45[2][3] = -height  # Translate -height along Z
    
    geometry_transform = c2w_opengl_aspect @ rot45
    
    # Step 5: Apply scene normalization
    if first_c2w is None:
        # This is the first camera - compute scene transform
        first_c2w_opengl = c2w @ OPENGL
        scene_transform_inv = (first_c2w_opengl @ rot_y180).inverted()
    else:
        # Use provided scene transform
        scene_transform_inv = first_c2w
    
    final_transform = scene_transform_inv @ geometry_transform
    
    # Extract position and rotation
    pos_final = Vector(final_transform.translation)
    rot_final = final_transform.to_3x3()
    quat_final = rot_final.to_quaternion()
    euler_final = rot_final.to_euler('XYZ')
    
    return {
        'step1_c2w': matrix_to_list(c2w),
        'step2_c2w_opengl': matrix_to_list(c2w_opengl),
        'step3_c2w_opengl_aspect': matrix_to_list(c2w_opengl_aspect),
        'step4_geometry_transform': matrix_to_list(geometry_transform),
        'step5_final_transform': matrix_to_list(final_transform),
        'scene_transform_inv': matrix_to_list(scene_transform_inv),
        'position': [pos_final.x, pos_final.y, pos_final.z],
        'rotation_quaternion': [quat_final.w, quat_final.x, quat_final.y, quat_final.z],
        'rotation_euler': [euler_final.x, euler_final.y, euler_final.z],
        'matrix_world': matrix_to_list(final_transform),
        'matrix_world_3x3': [[rot_final[i][j] for j in range(3)] for i in range(3)],
        'height': height,
        'aspect_ratio': aspect_ratio[0][0],
    }

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def compute_expected_transforms():
    """Compute expected transforms step-by-step"""
    print("=" * 60)
    print("Computing Expected Camera Transforms")
    print("=" * 60)
    
    # Determine MonST3R output directory
    if not MONST3R_OUTPUT_DIR:
        # Try to detect from imported GLB file
        blend_file_path = bpy.data.filepath
        if blend_file_path:
            possible_dirs = [
                os.path.join(os.path.dirname(blend_file_path), "demo_tmp", "lady-running"),
                os.path.dirname(blend_file_path),
            ]
            for dir_path in possible_dirs:
                traj_file = os.path.join(dir_path, "pred_traj.txt")
                if os.path.exists(traj_file):
                    output_dir = dir_path
                    break
            else:
                print("ERROR: Could not detect MonST3R output directory.")
                print("Please set MONST3R_OUTPUT_DIR in the script.")
                return None
        else:
            print("ERROR: Could not detect MonST3R output directory.")
            print("Please set MONST3R_OUTPUT_DIR in the script.")
            return None
    else:
        output_dir = MONST3R_OUTPUT_DIR
    
    traj_file = os.path.join(output_dir, "pred_traj.txt")
    if not os.path.exists(traj_file):
        print(f"ERROR: Trajectory file not found: {traj_file}")
        return None
    
    print(f"Reading camera poses from: {traj_file}")
    
    # Parse trajectory
    poses = parse_tum_trajectory(traj_file)
    print(f"Found {len(poses)} camera poses")
    
    if len(poses) == 0:
        print("ERROR: No camera poses found in trajectory file")
        return None
    
    # Parse intrinsics
    intrinsics_file = os.path.join(output_dir, "pred_intrinsics.txt")
    intrinsics = []
    if os.path.exists(intrinsics_file):
        intrinsics = parse_intrinsics(intrinsics_file)
        print(f"Found {len(intrinsics)} camera intrinsics")
        if len(intrinsics) != len(poses):
            print(f"Warning: Number of intrinsics ({len(intrinsics)}) != poses ({len(poses)})")
            intrinsics = intrinsics[:len(poses)] if len(intrinsics) > len(poses) else intrinsics + [(433.7, 433.7, 256, 144)] * (len(poses) - len(intrinsics))
    else:
        print("Warning: Intrinsics file not found, using default focal length")
        intrinsics = [(433.7, 433.7, 256, 144)] * len(poses)
    
    # Get image size
    image_size = (512, 288)  # Default
    rgb_dir = os.path.join(output_dir, "rgb_imgs")
    if os.path.exists(rgb_dir):
        import glob
        img_files = glob.glob(os.path.join(rgb_dir, "*.png")) + glob.glob(os.path.join(rgb_dir, "*.jpg"))
        if img_files:
            try:
                img = bpy.data.images.load(img_files[0])
                image_size = (img.size[0], img.size[1])
                print(f"Detected image size: {image_size[0]}x{image_size[1]}")
            except Exception as e:
                print(f"Warning: Could not detect image size: {e}, using default {image_size}")
    
    # Compute scene transform from first camera
    first_timestamp, first_pos, first_quat = poses[0]
    first_focal = intrinsics[0] if intrinsics else (433.7, 433.7, 256, 144)
    
    # Build first camera c2w
    quat_blender_first = Quaternion([first_quat[3], first_quat[0], first_quat[1], first_quat[2]])
    first_c2w = Matrix.Translation(Vector(first_pos))
    first_c2w = first_c2w @ quat_blender_first.to_matrix().to_4x4()
    
    OPENGL = Matrix([
        [1, 0, 0, 0],
        [0, -1, 0, 0],
        [0, 0, -1, 0],
        [0, 0, 0, 1]
    ])
    rot_y180 = Euler((0, math.radians(180), 0), 'XYZ').to_matrix().to_4x4()
    first_c2w_opengl = first_c2w @ OPENGL
    scene_transform_inv = (first_c2w_opengl @ rot_y180).inverted()
    
    # Compute transforms for all cameras
    transforms = []
    for i, (timestamp, pos, quat) in enumerate(poses):
        focal = intrinsics[i] if i < len(intrinsics) else (433.7, 433.7, 256, 144)
        
        print(f"Computing transform for camera {i+1}/{len(poses)}...")
        transform_data = compute_transform_step_by_step(
            pos, quat, 
            focal=(focal[0], focal[1]), 
            image_size=image_size,
            first_c2w=scene_transform_inv,
            screen_width=SCREEN_WIDTH
        )
        transform_data['index'] = i
        transform_data['timestamp'] = timestamp
        transform_data['original_position'] = pos
        transform_data['original_quaternion'] = quat
        transforms.append(transform_data)
    
    # Save to JSON
    output_path = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd(), OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump({
            'num_cameras': len(transforms),
            'transforms': transforms,
            'source': 'Computed from pred_traj.txt and pred_intrinsics.txt',
            'image_size': image_size,
            'screen_width': SCREEN_WIDTH,
        }, f, indent=2)
    
    print(f"\nSaved {len(transforms)} computed transforms to: {output_path}")
    print(f"Output file: {output_path}")
    
    # Print summary
    print("\nSummary:")
    print(f"  Total cameras: {len(transforms)}")
    if transforms:
        first = transforms[0]
        print(f"  First camera:")
        print(f"    Position: [{first['position'][0]:.6f}, {first['position'][1]:.6f}, {first['position'][2]:.6f}]")
        print(f"    Rotation (quat): [{first['rotation_quaternion'][0]:.6f}, {first['rotation_quaternion'][1]:.6f}, {first['rotation_quaternion'][2]:.6f}, {first['rotation_quaternion'][3]:.6f}]")
    
    return transforms

if __name__ == "__main__":
    compute_expected_transforms()
