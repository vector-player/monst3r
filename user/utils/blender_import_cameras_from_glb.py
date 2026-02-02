"""
Blender Script to Import Cameras from MonST3R GLB File

This script reads camera poses from the TUM trajectory file and creates
actual Blender camera objects (not just geometry) that match the cameras
shown in the GLB file.

Usage:
1. Import GLB file into Blender (File → Import → glTF 2.0)
2. Open Blender Scripting workspace
3. Open this script: File → Open → select this script
4. Configure paths at the top if needed
5. Run the script (Alt+P or click Run button)

The script will:
- Read camera poses from pred_traj.txt
- Create Blender camera objects with correct positions and orientations
- Match the coordinate system transformation used in GLB export
- Optionally create camera animation
"""

import bpy
import os
import re
from mathutils import Vector, Matrix, Quaternion, Euler
import math

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to MonST3R output directory (where pred_traj.txt is located)
# Set to None to auto-detect from imported GLB file
MONST3R_OUTPUT_DIR = None  # e.g., "/root/monst3r/demo_tmp/lady-running"

# Camera settings
CREATE_ANIMATION = True  # Create keyframe animation for cameras
CAMERA_SCALE = 1.0  # Scale factor for camera objects (visual size)
CAMERA_COLLECTION_NAME = "MonST3R_Cameras"  # Collection name for cameras
SCREEN_WIDTH = 0.03  # Camera frustum size (should match GLB export, default 0.03)

# ============================================================================
# AUTO-DETECTION LOGIC
# ============================================================================

def detect_monst3r_output_dir():
    """Try to detect MonST3R output directory from imported GLB file"""
    # Check if there's an imported GLB file
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.name.startswith('scene'):
            # Try to find pred_traj.txt in parent directories
            blend_file_path = bpy.data.filepath
            if blend_file_path:
                # Try common locations
                possible_dirs = [
                    os.path.join(os.path.dirname(blend_file_path), "demo_tmp", "lady-running"),
                    os.path.dirname(blend_file_path),
                ]
                for dir_path in possible_dirs:
                    traj_file = os.path.join(dir_path, "pred_traj.txt")
                    if os.path.exists(traj_file):
                        return dir_path
    return None

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

def quaternion_multiply(q1, q2):
    """Multiply two quaternions (w, x, y, z format)"""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    return (w, x, y, z)

def quaternion_from_matrix(matrix):
    """Convert rotation matrix to quaternion (w, x, y, z)"""
    # Use Blender's Matrix to Quaternion conversion
    mat = Matrix(matrix)
    quat = mat.to_quaternion()
    return (quat.w, quat.x, quat.y, quat.z)

def apply_glb_transformation(pos, quat, scene_transform_inv=None, focal=None, image_size=None):
    """Apply the same transformation that GLB export uses
    
    GLB export process (from viz_demo.py and viz.py):
    1. Camera geometry is created with transform: c2w @ OPENGL @ aspect_ratio @ rot45
       - aspect_ratio: scales X by W/H (for frustum aspect ratio) - only affects X axis
       - rot45: rotates frustum 45deg around Z, translates -height along Z
       - rot45[2, 3] = -height sets the cone tip = optical center
       - height = max(screen_width/10, focal * screen_width / H)
    
    2. Scene is transformed by: inv(cams2world[0] @ OPENGL @ rot_y180)
       - This normalizes the scene relative to first camera
    
    So the final camera geometry transform in GLB is:
    T_final = inv(cams2world[0] @ OPENGL @ rot_y180) @ (c2w @ OPENGL @ aspect_ratio @ rot45)
    
    The camera CENTER (optical center, cone tip) is at T_final[:3, 3]
    The camera ROTATION matrix is T_final[:3, :3]
    
    This function matches the step-by-step computation in blender_compute_expected_transforms.py
    """
    # OPENGL transformation matrix (inverts Y and Z)
    # Converts from CV convention (+Z forward, +Y down, +X right) 
    # to OpenGL convention (+Z up, +Y forward, +X right)
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
    
    # Step 1: Build camera-to-world matrix from TUM pose
    c2w = Matrix.Translation(Vector(pos))
    c2w = c2w @ quat_blender.to_matrix().to_4x4()
    
    # Compute scene transform from first camera if not provided
    if scene_transform_inv is None:
        # First camera: compute scene transform
        # Scene transform: inv(c2w @ OPENGL @ rot_y180)
        first_c2w_opengl = c2w @ OPENGL
        scene_transform_inv = (first_c2w_opengl @ rot_y180).inverted()
    
    # Step 2: Apply OPENGL
    c2w_opengl = c2w @ OPENGL
    
    # Step 3: Apply aspect_ratio (if we have image info)
    aspect_ratio = Matrix.Identity(4)
    if image_size:
        W, H = image_size[0], image_size[1]
        aspect_ratio[0][0] = W / H
    
    c2w_opengl_aspect = c2w_opengl @ aspect_ratio
    
    # Step 4: Apply rot45
    height = SCREEN_WIDTH / 10.0  # Default height
    if focal and image_size:
        W, H = image_size[0], image_size[1]
        fx = focal[0] if isinstance(focal, (list, tuple)) else focal
        height = max(SCREEN_WIDTH / 10.0, fx * SCREEN_WIDTH / H)
    
    rot45_z = Euler((0, 0, math.radians(45)), 'XYZ').to_matrix().to_4x4()
    rot45 = rot45_z.copy()
    rot45[2][3] = -height  # Translate -height along Z
    
    geometry_transform = c2w_opengl_aspect @ rot45
    
    # Step 5: Apply scene normalization
    geometry_transform_final = scene_transform_inv @ geometry_transform
    
    # Extract position and rotation from final transform
    pos_transformed = Vector(geometry_transform_final.translation)
    R_camera_geometry = geometry_transform_final.to_3x3()
    
    # Convert to quaternion for Blender camera object
    quat_transformed = R_camera_geometry.to_quaternion()
    
    return pos_transformed, quat_transformed, scene_transform_inv

# ============================================================================
# CAMERA CREATION FUNCTIONS
# ============================================================================

def create_camera_collection(name):
    """Create or get collection for cameras"""
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection

def focal_length_to_blender_lens(fx, image_width, sensor_width_mm=36.0):
    """Convert focal length in pixels to Blender lens in mm
    
    Blender uses sensor width and focal length in mm
    Formula: lens_mm = (fx / image_width) * sensor_width_mm
    """
    if image_width > 0:
        return (fx / image_width) * sensor_width_mm
    return 50.0  # Default

def create_camera_from_pose(index, pos, quat, collection, frame=None, focal_length=None, image_size=None):
    """Create a Blender camera object from pose"""
    # Create camera data
    cam_name = f"Camera_{index:04d}"
    cam_data = bpy.data.cameras.new(name=cam_name)
    
    # Set focal length if provided
    if focal_length and image_size:
        fx, fy = focal_length[0], focal_length[1]
        width, height = image_size
        # Use average focal length and image width
        lens_mm = focal_length_to_blender_lens((fx + fy) / 2, width)
        cam_data.lens = lens_mm
        # Set sensor fit to match aspect ratio
        cam_data.sensor_fit = 'AUTO'
    else:
        cam_data.lens = 50.0  # Default focal length
    
    # Create camera object
    cam_obj = bpy.data.objects.new(cam_name, cam_data)
    collection.objects.link(cam_obj)
    
    # Set position
    cam_obj.location = Vector(pos)
    
    # Set rotation (Blender uses quaternion)
    cam_obj.rotation_mode = 'QUATERNION'
    cam_obj.rotation_quaternion = quat
    
    # Set keyframe if animation is enabled
    if CREATE_ANIMATION and frame is not None:
        cam_obj.keyframe_insert(data_path="location", frame=frame)
        cam_obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    
    return cam_obj

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to import cameras"""
    # Determine MonST3R output directory
    if MONST3R_OUTPUT_DIR:
        output_dir = MONST3R_OUTPUT_DIR
    else:
        output_dir = detect_monst3r_output_dir()
        if not output_dir:
            print("ERROR: Could not detect MonST3R output directory.")
            print("Please set MONST3R_OUTPUT_DIR in the script or ensure GLB file is imported.")
            return
    
    traj_file = os.path.join(output_dir, "pred_traj.txt")
    if not os.path.exists(traj_file):
        print(f"ERROR: Trajectory file not found: {traj_file}")
        return
    
    print(f"Reading camera poses from: {traj_file}")
    
    # Parse trajectory
    poses = parse_tum_trajectory(traj_file)
    print(f"Found {len(poses)} camera poses")
    
    if len(poses) == 0:
        print("ERROR: No camera poses found in trajectory file")
        return
    
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
        intrinsics = [(433.7, 433.7, 256, 144)] * len(poses)  # Default values
    
    # Get image size (try to detect from images or use default)
    # This is critical for computing the exact rot45 transform
    image_size = (512, 288)  # Default, will be updated if images are found
    rgb_dir = os.path.join(output_dir, "rgb_imgs")
    if os.path.exists(rgb_dir):
        import glob
        img_files = glob.glob(os.path.join(rgb_dir, "*.png")) + glob.glob(os.path.join(rgb_dir, "*.jpg"))
        if img_files:
            try:
                # Try to load first image to get size (bpy is already imported at top)
                img = bpy.data.images.load(img_files[0])
                image_size = (img.size[0], img.size[1])
                print(f"Detected image size: {image_size[0]}x{image_size[1]}")
            except Exception as e:
                print(f"Warning: Could not detect image size: {e}, using default {image_size}")
                print(f"  Camera positions/orientations may not match geometry exactly")
                pass
    else:
        print(f"Warning: rgb_imgs directory not found, using default image size {image_size}")
        print(f"  Camera positions/orientations may not match geometry exactly")
        print(f"  To fix: Ensure rgb_imgs/ directory exists or set image_size manually")
    
    # Create collection for cameras
    collection = create_camera_collection(CAMERA_COLLECTION_NAME)
    
    # Set scene frame range if creating animation
    if CREATE_ANIMATION:
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = len(poses)
        print(f"Animation range: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
    
    # Get first camera pose and compute scene normalization transform
    first_timestamp, first_pos, first_quat = poses[0]
    
    # Compute scene transform from first camera (will be computed in apply_glb_transformation)
    scene_transform_inv = None
    
    # Create cameras
    created_cameras = []
    for i, (timestamp, pos, quat) in enumerate(poses):
        # Get focal length and image size for this camera
        focal_length = intrinsics[i] if i < len(intrinsics) else (433.7, 433.7, 256, 144)
        
        # Apply GLB transformation with scene normalization
        # scene_transform_inv will be computed on first iteration and reused
        # Pass focal and image_size to compute exact rot45 transform
        pos_transformed, quat_transformed, scene_transform_inv = apply_glb_transformation(
            pos, quat, scene_transform_inv, 
            focal=(focal_length[0], focal_length[1]), 
            image_size=image_size
        )
        
        # Create camera
        frame = i + 1 if CREATE_ANIMATION else None
        cam_obj = create_camera_from_pose(
            i, pos_transformed, quat_transformed, collection, frame, 
            focal_length=(focal_length[0], focal_length[1]), 
            image_size=image_size
        )
        created_cameras.append(cam_obj)
        
        if (i + 1) % 10 == 0:
            print(f"Created {i + 1}/{len(poses)} cameras...")
    
    print(f"\nSuccessfully created {len(created_cameras)} camera objects!")
    print(f"Cameras are in collection: '{CAMERA_COLLECTION_NAME}'")
    
    if CREATE_ANIMATION:
        print(f"Camera animation created from frame {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
        print("Press Space to play animation, or scrub timeline to see camera movement")
    
    # Validation: Compare with GLB geometry if available
    print("\n" + "=" * 60)
    print("Validation: Comparing with GLB geometry")
    print("=" * 60)
    
    # Find camera geometry objects from GLB
    camera_geometries = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            if len(mesh.vertices) < 50 and len(mesh.vertices) > 4:
                camera_geometries.append(obj)
    
    if len(camera_geometries) > 0 and len(created_cameras) > 0:
        camera_geometries.sort(key=lambda x: int(re.search(r'\d+', x.name).group()) if re.search(r'\d+', x.name) else 0)
        
        # Compare first few cameras
        num_to_check = min(5, len(camera_geometries), len(created_cameras))
        pos_diffs = []
        rot_diffs = []
        
        for i in range(num_to_check):
            geom = camera_geometries[i]
            cam = created_cameras[i]
            
            pos_diff = (geom.location - cam.location).length
            rot_diff = (geom.rotation_euler.to_quaternion() - cam.rotation_quaternion).magnitude
            
            pos_diffs.append(pos_diff)
            rot_diffs.append(rot_diff)
            
            if i < 3:  # Print details for first 3
                print(f"Camera {i+1}:")
                print(f"  Position diff: {pos_diff:.6f} {'✓' if pos_diff < 0.001 else '✗'}")
                print(f"  Rotation diff: {rot_diff:.6f} {'✓' if rot_diff < 0.01 else '✗'}")
        
        avg_pos_diff = sum(pos_diffs) / len(pos_diffs)
        avg_rot_diff = sum(rot_diffs) / len(rot_diffs)
        max_pos_diff = max(pos_diffs)
        max_rot_diff = max(rot_diffs)
        
        print(f"\nSummary (first {num_to_check} cameras):")
        print(f"  Average position difference: {avg_pos_diff:.6f} {'✓' if avg_pos_diff < 0.001 else '✗'}")
        print(f"  Max position difference: {max_pos_diff:.6f} {'✓' if max_pos_diff < 0.001 else '✗'}")
        print(f"  Average rotation difference: {avg_rot_diff:.6f} {'✓' if avg_rot_diff < 0.01 else '✗'}")
        print(f"  Max rotation difference: {max_rot_diff:.6f} {'✓' if max_rot_diff < 0.01 else '✗'}")
        
        if avg_pos_diff < 0.001 and avg_rot_diff < 0.01:
            print("\n✓ Validation PASSED: Cameras match GLB geometry!")
        else:
            print("\n✗ Validation FAILED: Cameras do not match GLB geometry.")
            print("  Run blender_extract_glb_camera_transforms.py and blender_compute_expected_transforms.py")
            print("  Then run blender_compare_transforms.py to identify the issue.")
    else:
        print("  No GLB geometry found for comparison.")
        print("  Import GLB file first to enable validation.")
    
    # Select first camera
    if created_cameras:
        bpy.context.view_layer.objects.active = created_cameras[0]
        created_cameras[0].select_set(True)
        print(f"\nFirst camera selected: {created_cameras[0].name}")

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    main()
