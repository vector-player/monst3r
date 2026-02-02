#!/usr/bin/env python3
"""
Convert MonST3R output to COLMAP format

This script converts MonST3R reconstruction results to COLMAP format:
- pred_traj.txt (TUM format) -> images.txt (COLMAP format)
- pred_intrinsics.txt -> cameras.txt (COLMAP format)
- Depth maps + RGB images -> points3D.txt (COLMAP format)

Blender photogrammetry_importer Addon Compatibility:
This script is optimized for the Blender photogrammetry_importer addon:
- Image names MUST contain digits (e.g., image_0001.png) for camera animation sorting
- images.txt format: Two lines per image (pose line + empty points2D line)
- Camera model: PINHOLE with 4 parameters (fx, fy, cx, cy)
- All required files: cameras.txt, images.txt, points3D.txt must be present
- Image paths: Relative to COLMAP model directory (e.g., images/image_0001.png)

Usage:
    # Interactive mode (prompts for input path)
    python convert_to_colmap.py
    
    # Command-line mode
    python convert_to_colmap.py --input <path/to/monst3r/output> --output <path/to/colmap/output>
    python convert_to_colmap.py --input demo_tmp/lady-running --copy-images
    python convert_to_colmap.py --input demo_tmp/lady-running --copy-images --copy-depth-maps
    # Camera orientation fix is enabled by default to match GLB export
    # Use --no-fix-camera-orientation to disable if cameras are already correct
"""

import argparse
import os
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
import trimesh
import re


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
    
    Format: One 3x3 K matrix per line (9 values: fx 0 cx 0 fy cy 0 0 1)
    Returns: list of 3x3 K matrices
    """
    intrinsics = []
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Intrinsics file not found: {filepath}")
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 9:
                try:
                    K = np.array([
                        [float(parts[0]), float(parts[1]), float(parts[2])],
                        [float(parts[3]), float(parts[4]), float(parts[5])],
                        [float(parts[6]), float(parts[7]), float(parts[8])]
                    ])
                    intrinsics.append(K)
                except ValueError:
                    continue
    return intrinsics


def get_image_files(input_dir):
    """Get list of image files, preferring RGB images over masks
    
    Priority:
    1. rgb_imgs/ directory (RGB images)
    2. images/ directory (alternative name)
    3. Current directory (excluding mask files)
    """
    # Priority 1: rgb_imgs directory
    rgb_dir = os.path.join(input_dir, "rgb_imgs")
    if os.path.exists(rgb_dir):
        image_files = sorted([f for f in os.listdir(rgb_dir) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        if len(image_files) > 0:
            return [os.path.join(rgb_dir, f) for f in image_files]
    
    # Priority 2: images directory
    images_dir = os.path.join(input_dir, "images")
    if os.path.exists(images_dir):
        image_files = sorted([f for f in os.listdir(images_dir) 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        if len(image_files) > 0:
            return [os.path.join(images_dir, f) for f in image_files]
    
    # Priority 3: Current directory (exclude mask files)
    all_files = [f for f in os.listdir(input_dir)
                 if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    
    # Filter out mask files (prefer RGB images)
    rgb_files = [f for f in all_files 
                 if not any(mask_term in f.lower() for mask_term in 
                           ['mask', 'depth', 'conf', 'seg', 'dynamic_mask'])]
    
    if len(rgb_files) > 0:
        image_files = sorted(rgb_files)
        return [os.path.join(input_dir, f) for f in image_files]
    
    # Fallback: use all images (including masks) but sorted properly
    if len(all_files) > 0:
        # Sort by frame number if possible
        def extract_frame_number(filename):
            import re
            numbers = re.findall(r'\d+', filename)
            return int(numbers[0]) if numbers else 0
        
        image_files = sorted(all_files, key=extract_frame_number)
        return [os.path.join(input_dir, f) for f in image_files]
    
    return []


def get_image_size(image_path):
    """Get image dimensions"""
    try:
        from PIL import Image
        img = Image.open(image_path)
        return img.size  # Returns (width, height)
    except ImportError:
        # Fallback: try cv2
        try:
            import cv2
            img = cv2.imread(image_path)
            if img is not None:
                return (img.shape[1], img.shape[0])  # (width, height)
        except ImportError:
            pass
    # Default fallback
    return (512, 512)


def extract_3d_points_from_glb(glb_path, max_points=100000):
    """Extract 3D points from GLB file
    
    Returns: numpy array of points (N, 3) and colors (N, 3)
    """
    if not os.path.exists(glb_path):
        return None, None
    
    try:
        scene = trimesh.load(glb_path)
        
        # Collect all points from the scene
        all_points = []
        all_colors = []
        
        for name, geometry in scene.geometry.items():
            if isinstance(geometry, trimesh.PointCloud):
                points = geometry.vertices
                colors = geometry.colors[:, :3] if geometry.colors is not None else None
            elif isinstance(geometry, trimesh.Trimesh):
                points = geometry.vertices
                # Try to get vertex colors
                if hasattr(geometry.visual, 'vertex_colors') and geometry.visual.vertex_colors is not None:
                    colors = geometry.visual.vertex_colors[:, :3]
                else:
                    colors = None
            else:
                continue
            
            all_points.append(points)
            if colors is not None:
                all_colors.append(colors)
        
        if len(all_points) == 0:
            return None, None
        
        # Concatenate all points
        points = np.vstack(all_points)
        
        # Handle colors
        if len(all_colors) > 0 and len(all_colors) == len(all_points):
            colors = np.vstack(all_colors)
        else:
            # Generate random colors if not available
            colors = np.random.rand(len(points), 3) * 255
        
        # Sample points if too many
        if len(points) > max_points:
            indices = np.random.choice(len(points), max_points, replace=False)
            points = points[indices]
            colors = colors[indices]
        
        return points, colors
    
    except Exception as e:
        print(f"Warning: Could not extract points from GLB: {e}")
        return None, None


def extract_3d_points_from_depth(depth_dir, rgb_dir, intrinsics, poses, max_points=100000):
    """Extract 3D points from depth maps and RGB images
    
    Supports:
    - MonST3R depth maps: frame_XXXX.npy files in the input directory
    - Standard depth_maps/ directory with depth files
    """
    # First, try MonST3R format: frame_*.npy files in the directory
    if depth_dir and os.path.exists(depth_dir):
        depth_files = sorted([f for f in os.listdir(depth_dir) 
                             if f.endswith('.npy') or f.endswith('.png')])
    else:
        depth_files = []
    
    # If no depth_dir or empty, try looking for frame_*.npy in parent directory (MonST3R format)
    if len(depth_files) == 0 and depth_dir:
        parent_dir = os.path.dirname(depth_dir) if os.path.isdir(depth_dir) else depth_dir
        if os.path.exists(parent_dir):
            # Look for MonST3R depth maps: frame_XXXX.npy
            all_files = os.listdir(parent_dir)
            depth_files = sorted([f for f in all_files 
                                 if f.startswith('frame_') and f.endswith('.npy')])
            if len(depth_files) > 0:
                depth_dir = parent_dir  # Update depth_dir to parent
                print(f"  Found MonST3R depth maps: {len(depth_files)} frame_*.npy files")
    
    if len(depth_files) == 0:
        return None, None
    
    all_points = []
    all_colors = []
    
    try:
        import cv2
    except ImportError:
        print("Warning: OpenCV not available, skipping depth-based point extraction")
        return None, None
    
    for i, depth_file in enumerate(depth_files[:min(len(poses), len(intrinsics))]):
        depth_path = os.path.join(depth_dir, depth_file)
        
        # Load depth map
        if depth_file.endswith('.npy'):
            try:
                depth = np.load(depth_path)
            except Exception as e:
                print(f"    Warning: Could not load {depth_file}: {e}")
                continue
        else:
            depth = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
            if depth is None:
                continue
            if len(depth.shape) == 3:
                depth = depth[:, :, 0]
        
        # Handle MonST3R format: frame_XXXX.npy -> look for corresponding RGB
        # MonST3R saves RGB images as separate files (not necessarily matching depth names)
        rgb_path = None
        if rgb_dir and os.path.exists(rgb_dir):
            # Try to find corresponding RGB image
            # For MonST3R: frame_0000.npy might correspond to rgb image with similar index
            if depth_file.startswith('frame_'):
                # Extract frame number
                import re
                frame_match = re.search(r'frame_(\d+)', depth_file)
                if frame_match:
                    frame_num = frame_match.group(1)
                    # Try common RGB naming patterns
                    rgb_patterns = [
                        f"frame_{frame_num}.png",
                        f"rgb_{frame_num}.png",
                        f"image_{int(frame_num):04d}.png",
                        f"{frame_num}.png"
                    ]
                    for pattern in rgb_patterns:
                        test_path = os.path.join(rgb_dir, pattern)
                        if os.path.exists(test_path):
                            rgb_path = test_path
                            break
            
            # Fallback: try standard naming patterns
            if rgb_path is None:
                rgb_file = depth_file.replace('depth', 'rgb').replace('_depth', '').replace('.npy', '.png')
                rgb_path = os.path.join(rgb_dir, rgb_file) if rgb_dir else None
                if rgb_path and not os.path.exists(rgb_path):
                    rgb_path = None
        
        # Get intrinsics and pose
        if i >= len(intrinsics) or i >= len(poses):
            continue
        
        K = intrinsics[i]
        _, pos, quat = poses[i]
        
        # Convert quaternion to rotation matrix
        # TUM format: qx qy qz qw -> scipy expects w x y z
        q_scipy = [quat[3], quat[0], quat[1], quat[2]]
        R = Rotation.from_quat(q_scipy).as_matrix()
        
        # Create camera-to-world transformation
        T_c2w = np.eye(4)
        T_c2w[:3, :3] = R
        T_c2w[:3, 3] = pos
        
        # Extract 3D points from depth map
        h, w = depth.shape
        fx, fy = K[0, 0], K[1, 1]
        cx, cy = K[0, 2], K[1, 2]
        
        # Sample points (every Nth pixel)
        step = max(1, int(np.sqrt(h * w / max_points)))
        y_coords, x_coords = np.mgrid[0:h:step, 0:w:step]
        y_coords = y_coords.flatten()
        x_coords = x_coords.flatten()
        
        # Backproject to 3D
        z = depth[y_coords, x_coords]
        valid = z > 0
        
        if np.sum(valid) == 0:
            continue
        
        x_coords = x_coords[valid]
        y_coords = y_coords[valid]
        z = z[valid]
        
        x = (x_coords - cx) * z / fx
        y = (y_coords - cy) * z / fy
        
        # Points in camera frame
        points_cam = np.stack([x, y, z], axis=1)
        
        # Transform to world frame
        points_hom = np.hstack([points_cam, np.ones((len(points_cam), 1))])
        points_world = (T_c2w @ points_hom.T).T[:, :3]
        
        all_points.append(points_world)
        
        # Get colors
        if rgb_path:
            rgb_img = cv2.imread(rgb_path)
            if rgb_img is not None:
                colors = rgb_img[y_coords, x_coords, ::-1]  # BGR to RGB
                all_colors.append(colors)
    
    if len(all_points) == 0:
        return None, None
    
    points = np.vstack(all_points)
    if len(all_colors) > 0:
        colors = np.vstack(all_colors)
    else:
        colors = np.random.rand(len(points), 3) * 255
    
    # Sample if too many
    if len(points) > max_points:
        indices = np.random.choice(len(points), max_points, replace=False)
        points = points[indices]
        colors = colors[indices]
    
    return points, colors


def write_colmap_cameras(output_path, intrinsics, image_sizes):
    """Write COLMAP cameras.txt file
    
    Format: CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
    For PINHOLE model: fx, fy, cx, cy (4 parameters)
    
    The Blender addon expects PINHOLE model with exactly 4 parameters:
    - fx: focal length in x direction
    - fy: focal length in y direction  
    - cx: principal point x coordinate
    - cy: principal point y coordinate
    """
    with open(output_path, 'w') as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write("# Number of cameras: {}\n".format(len(intrinsics)))
        
        for i, (K, (width, height)) in enumerate(zip(intrinsics, image_sizes), start=1):
            fx, fy = K[0, 0], K[1, 1]
            cx, cy = K[0, 2], K[1, 2]
            
            # Validate parameters
            if fx <= 0 or fy <= 0:
                print(f"    WARNING: Invalid focal length for camera {i}: fx={fx}, fy={fy}")
            if cx < 0 or cy < 0 or cx > width or cy > height:
                print(f"    WARNING: Principal point may be out of bounds for camera {i}: cx={cx}, cy={cy}, size=({width}, {height})")
            
            # Write PINHOLE camera model with 4 parameters (required by Blender addon)
            # Format: CAMERA_ID MODEL WIDTH HEIGHT fx fy cx cy
            f.write(f"{i} PINHOLE {int(width)} {int(height)} {fx:.6f} {fy:.6f} {cx:.6f} {cy:.6f}\n")


def write_colmap_images(output_path, poses, image_files, camera_ids, image_base_dir=None, return_image_names=None, fix_orientation=False):
    """Write COLMAP images.txt file
    
    Format: IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
    
    Args:
        output_path: Path to output images.txt file
        poses: List of camera poses
        image_files: List of image file paths (absolute or relative)
        camera_ids: List of camera IDs
        image_base_dir: Base directory for images (for relative paths). 
                       If set (e.g., when --copy-images is used), images are in images/ subdirectory.
    """
    # Get the COLMAP model directory (where images.txt is located)
    model_dir = os.path.dirname(os.path.abspath(output_path))
    
    # Debug: print first call info
    if image_base_dir:
        print(f"    DEBUG: image_base_dir={image_base_dir}, model_dir={model_dir}")
    
    with open(output_path, 'w') as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write("# POINTS2D[] as (X, Y, POINT3D_ID)\n")
        f.write("# Number of images: {}\n".format(len(poses)))
        
        for i, ((timestamp, pos, quat), img_file, cam_id) in enumerate(zip(poses, image_files, camera_ids), start=1):
            # TUM format: qx qy qz qw -> COLMAP: qw qx qy qz
            # MonST3R uses camera-to-world poses directly from c2w matrices
            # COLMAP also uses camera-to-world poses
            # However, there may be a coordinate system difference
            
            # Extract position components (must be done before if/else block)
            tx, ty, tz = pos
            
            # Convert quaternion from TUM format (qx qy qz qw) to scipy format (w x y z)
            quat_scipy = [quat[3], quat[0], quat[1], quat[2]]  # w x y z
            
            # Check if coordinate system transformation is needed
            # MonST3R GLB export applies: inv(cams2world[0] @ OPENGL @ rot_y180)
            # This suggests MonST3R might use a different forward direction
            # If cameras point opposite direction, apply 180 deg rotation around Y axis
            # This rotates the camera to point in the correct direction
            
            # COORDINATE SYSTEM FIX: Apply 180 degree rotation around Y axis if needed
            # MonST3R's GLB export applies: inv(cams2world[0] @ OPENGL @ rot_y180)
            # This suggests MonST3R camera poses may need rotation correction
            # If cameras point opposite to movement direction, rotate by 180 deg around Y
            # This rotates the camera forward direction to match movement direction
            
            # Check if orientation fix is requested
            if fix_orientation:
                # GLB export applies transformations to match Blender coordinate system
                # To fix upside-down cameras and correct orientation:
                # 1. OPENGL inverts Y and Z axes: [[1,0,0], [0,-1,0], [0,0,-1]]
                # 2. Y-axis 180 rotation for forward direction
                # 3. X-axis 180 rotation to fix upside-down cameras
                
                # Create OPENGL transformation matrix (inverts Y and Z)
                opengl_matrix = np.array([[1, 0, 0],
                                         [0, -1, 0],
                                         [0, 0, -1]])
                
                # Create rotation matrices
                rot_y180_matrix = Rotation.from_euler('y', np.deg2rad(180)).as_matrix()
                rot_x180_matrix = Rotation.from_euler('x', np.deg2rad(180)).as_matrix()
                
                # Combine: X-axis rotation first (fixes upside-down), then Y-axis, then OPENGL
                # This should fix both upside-down and orientation issues
                combined_transform = rot_x180_matrix @ rot_y180_matrix @ opengl_matrix
                
                # Convert to quaternion for rotation composition
                transform_quat = Rotation.from_matrix(combined_transform)
                
                # Build camera-to-world matrix from TUM pose
                # TUM format: position is camera center in world coordinates
                R_original = Rotation.from_quat(quat_scipy).as_matrix()
                c2w = np.eye(4)
                c2w[:3, :3] = R_original
                c2w[:3, 3] = np.array([tx, ty, tz])
                
                # Apply transformation to full c2w matrix: new_c2w = T @ c2w
                # This correctly transforms both rotation and translation together
                T_full = np.eye(4)
                T_full[:3, :3] = combined_transform
                c2w_transformed = T_full @ c2w
                
                # Extract transformed rotation and position
                R_transformed = c2w_transformed[:3, :3]
                pos_transformed = c2w_transformed[:3, 3]
                
                # Convert back to quaternion
                quat_transformed = Rotation.from_matrix(R_transformed).as_quat()  # Returns [w, x, y, z]
                
                # Convert back to COLMAP format: qw qx qy qz
                qw, qx, qy, qz = quat_transformed[0], quat_transformed[1], quat_transformed[2], quat_transformed[3]
                tx, ty, tz = pos_transformed[0], pos_transformed[1], pos_transformed[2]
            else:
                # Use original quaternion without modification
                qw, qx, qy, qz = quat_scipy[0], quat_scipy[1], quat_scipy[2], quat_scipy[3]
                tx, ty, tz = pos
            
            # Get image filename - always use sequential naming for COLMAP compatibility
            # This avoids parsing issues with non-sequential names like dynamic_mask_0.png
            ext = '.png'
            if img_file:
                # Extract extension from file path
                ext = os.path.splitext(img_file)[1] or '.png'
            
            # Determine the correct relative path for the image
            # The path in images.txt must be relative to the COLMAP model directory
            # CRITICAL: If image_base_dir is set (when --copy-images is used), 
            # images are ALWAYS in images/ subdirectory relative to model_dir
            # Check this FIRST before any other logic
            use_images_prefix = (image_base_dir is not None and image_base_dir != "")
            
            # Also check if the actual image file path suggests images are in images/ subdirectory
            if not use_images_prefix and img_file:
                img_abs_check = os.path.abspath(img_file) if os.path.exists(img_file) else img_file
                # Check if path contains "images" and the parent directory is "images"
                if "images" in img_abs_check.replace('\\', '/'):
                    img_dir_check = os.path.dirname(img_abs_check) if os.path.exists(img_file) else ""
                    if img_dir_check and os.path.basename(img_dir_check) == "images":
                        use_images_prefix = True
                        if i <= 3:
                            print(f"    DEBUG Image {i}: Detected images/ subdirectory from file path")
            
            if use_images_prefix:
                # When --copy-images is used, images are always in images/ subdirectory
                # This ensures the path in images.txt is "images/image_XXXX.png"
                img_name = f"images/image_{i:04d}{ext}"
                # Debug first few entries
                if i <= 3:
                    print(f"    DEBUG Image {i}: Using images/ prefix (image_base_dir={image_base_dir})")
            elif img_file and os.path.exists(img_file):
                # Try to compute relative path from model directory
                img_abs = os.path.abspath(img_file)
                try:
                    # Compute relative path from model directory
                    img_rel = os.path.relpath(img_abs, model_dir)
                    # Use forward slashes for cross-platform compatibility
                    img_rel = img_rel.replace('\\', '/')
                    
                    # Validate the relative path - must not be absolute or contain drive letters
                    if (img_rel and img_rel.strip() and 
                        not (len(img_rel) > 2 and img_rel[1] == ':') and
                        not img_rel.startswith('../')):
                        # Valid relative path - use it
                        img_name = img_rel
                    else:
                        # Relative path computation failed or invalid
                        # Check if image is in an "images" subdirectory by examining the path
                        img_dir = os.path.dirname(img_abs)
                        if os.path.basename(img_dir) == "images":
                            img_name = f"images/image_{i:04d}{ext}"
                        else:
                            img_name = f"image_{i:04d}{ext}"
                except (ValueError, OSError):
                    # Path computation failed, check directory structure
                    img_dir = os.path.dirname(os.path.abspath(img_file))
                    if os.path.basename(img_dir) == "images":
                        img_name = f"images/image_{i:04d}{ext}"
                    else:
                        img_name = f"image_{i:04d}{ext}"
            else:
                # Image file doesn't exist or wasn't provided
                # Default to sequential naming without subdirectory
                img_name = f"image_{i:04d}{ext}"
            
            # CRITICAL: Ensure img_name is never empty (this causes ValueError in Blender addon)
            # The Blender addon tries to parse frame numbers from image names, and empty strings cause errors
            img_name = img_name.strip()
            if not img_name:
                # Final fallback: use sequential name
                if use_images_prefix:
                    img_name = f"images/image_{i:04d}{ext}"
                else:
                    img_name = f"image_{i:04d}{ext}"
            
            # Final validation: if image_base_dir was set, ensure we're using images/ prefix
            # This is a safety check to catch any logic errors
            if use_images_prefix and not img_name.startswith("images/"):
                print(f"    WARNING: image_base_dir is set but img_name doesn't start with 'images/': {img_name}")
                print(f"    Fixing: changing to images/image_{i:04d}{ext}")
                img_name = f"images/image_{i:04d}{ext}"
            
            # CRITICAL FOR BLENDER ADDON: Image name MUST contain digits for animation sorting
            # The addon extracts digits from image name: int("".join(filter(str.isdigit, camera.get_relative_fp())))
            # If no digits found, it will fail with ValueError: invalid literal for int() with base 10: ''
            # Our sequential naming (image_0001.png) ensures digits are always present
            
            # Write image line: IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
            # Format per COLMAP spec and Blender addon expectations:
            # Line 1: IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
            # Line 2: POINTS2D[] as (X, Y, POINT3D_ID) - can be empty but line must exist
            assert img_name and img_name.strip(), f"Image name cannot be empty for image {i}"
            
            # Verify image name contains digits (required for Blender addon animation)
            import re
            if not re.search(r'\d', img_name):
                print(f"    WARNING: Image name '{img_name}' contains no digits - Blender addon may fail!")
                # Force sequential naming with digits
                if use_images_prefix:
                    img_name = f"images/image_{i:04d}{ext}"
                else:
                    img_name = f"image_{i:04d}{ext}"
            
            f.write(f"{i} {qw:.6f} {qx:.6f} {qy:.6f} {qz:.6f} {tx:.6f} {ty:.6f} {tz:.6f} {cam_id} {img_name}\n")
            # Write empty line for points2D (COLMAP format requirement)
            # The Blender addon expects TWO lines per image:
            # Line 1: IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME
            # Line 2: POINTS2D data (can be empty, but line must exist)
            # This empty line is critical - missing it will cause parsing errors
            f.write("\n")
            
            # Store image name for depth map conversion
            if return_image_names is not None:
                return_image_names.append(img_name)


def write_colmap_depth_map_bin(depth_map_npy_path, output_bin_path):
    """Convert MonST3R depth map (.npy) to COLMAP binary format (.geometric.bin)
    
    COLMAP binary format:
    - Header: width&height&channels& (as text, channels=1 for depth)
    - Data: float32 array in Fortran order (column-major)
    
    Args:
        depth_map_npy_path: Path to input .npy depth map
        output_bin_path: Path to output .geometric.bin file
    """
    try:
        # Load depth map
        depth_map = np.load(depth_map_npy_path)
        
        # Ensure 2D array
        if len(depth_map.shape) > 2:
            depth_map = depth_map.squeeze()
        if len(depth_map.shape) != 2:
            raise ValueError(f"Depth map must be 2D, got shape {depth_map.shape}")
        
        height, width = depth_map.shape
        channels = 1
        
        # Convert to float32
        depth_map = depth_map.astype(np.float32)
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_bin_path), exist_ok=True)
        
        # Write COLMAP binary format
        with open(output_bin_path, 'wb') as fid:
            # Write header: width&height&channels&
            header = f"{width}&{height}&{channels}&"
            fid.write(header.encode('ascii'))
            
            # Write data in Fortran order (column-major)
            # COLMAP stores arrays in Fortran order, so we transpose first
            depth_map_fortran = np.asfortranarray(depth_map)
            depth_map_fortran.tofile(fid)
        
        return True
    except Exception as e:
        print(f"    Warning: Could not convert {depth_map_npy_path} to {output_bin_path}: {e}")
        return False


def convert_depth_maps_to_colmap_format(input_dir, output_dir, image_names, image_base_dir=None):
    """Convert MonST3R depth maps to COLMAP binary format
    
    The Blender addon expects depth maps in:
    - Location: stereo/depth_maps/ (or stereo/depth_maps/images/ if images are in subdirectory)
    - Format: .geometric.bin (COLMAP binary format)
    - Naming: {image_name}.geometric.bin (where image_name comes from images.txt)
    
    Args:
        input_dir: MonST3R input directory (contains frame_*.npy files)
        output_dir: COLMAP output directory
        image_names: List of image names from images.txt (e.g., ['images/image_0001.png', ...])
        image_base_dir: Base directory for images (to determine depth map subdirectory structure)
    
    Returns:
        Number of depth maps converted
    """
    # Find MonST3R depth maps
    frame_files = sorted([f for f in os.listdir(input_dir) 
                         if f.startswith('frame_') and f.endswith('.npy')])
    
    if len(frame_files) == 0:
        print(f"    No frame_*.npy files found in {input_dir}")
        return 0
    
    print(f"    Found {len(frame_files)} MonST3R depth maps (frame_*.npy)")
    
    # Determine depth map output directory
    # COLMAP workspace format: stereo/depth_maps/
    # If images are in images/ subdirectory, depth maps should match that structure
    # Check if any image name contains "images/" prefix
    has_images_subdir = any("/" in name and name.startswith("images/") for name in image_names[:5])
    
    if has_images_subdir or (image_base_dir and "images" in str(image_base_dir)):
        # Depth maps should be in stereo/depth_maps/images/ to match image structure
        depth_map_output_dir = os.path.join(output_dir, "stereo", "depth_maps", "images")
    else:
        # Depth maps in stereo/depth_maps/
        depth_map_output_dir = os.path.join(output_dir, "stereo", "depth_maps")
    
    os.makedirs(depth_map_output_dir, exist_ok=True)
    
    converted_count = 0
    
    # Map frame files to image names by index
    # Assumes frame_0000.npy -> image_0001.png (or images/image_0001.png)
    for i, frame_file in enumerate(frame_files[:len(image_names)]):
        # Extract frame number from frame_XXXX.npy
        frame_match = re.search(r'frame_(\d+)', frame_file)
        if not frame_match:
            continue
        
        frame_num = int(frame_match.group(1))
        
        # Get corresponding image name (by index)
        if i < len(image_names):
            image_name = image_names[i]
        else:
            # Fallback: construct image name from frame number
            # Note: frame_0000.npy typically corresponds to image_0001.png (1-indexed)
            image_name = f"image_{frame_num+1:04d}.png"
            if has_images_subdir:
                image_name = f"images/{image_name}"
        
        # Construct output path: {image_name}.geometric.bin
        # Remove extension from image name and add .geometric.bin
        # CRITICAL: If depth_map_output_dir already includes "images/", strip it from image_name
        # to avoid double nesting (stereo/depth_maps/images/images/image_0001.png.geometric.bin)
        image_name_for_path = image_name
        if has_images_subdir or (image_base_dir and "images" in str(image_base_dir)):
            # We've already put depth maps in stereo/depth_maps/images/
            # So strip "images/" prefix from image_name to avoid double nesting
            if image_name.startswith("images/"):
                image_name_for_path = image_name[7:]  # Remove "images/" prefix
        
        image_base = os.path.splitext(image_name_for_path)[0]
        output_bin_path = os.path.join(depth_map_output_dir, image_base + ".geometric.bin")
        
        # Convert
        input_npy_path = os.path.join(input_dir, frame_file)
        if write_colmap_depth_map_bin(input_npy_path, output_bin_path):
            converted_count += 1
            if converted_count <= 3:
                print(f"    {frame_file} -> {os.path.basename(output_bin_path)}")
    
    return converted_count


def write_colmap_points3d(output_path, points, colors, fix_orientation=False):
    """Write COLMAP points3D.txt file
    
    Format: POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]
    
    The Blender addon expects:
    - Each point on a single line
    - TRACK[] is optional (can be empty)
    - ERROR is typically 0.0 if unknown
    - RGB values should be integers 0-255
    """
    if points is None or len(points) == 0:
        # Create empty file with proper header (required by Blender addon)
        # The addon checks for file existence and proper format
        with open(output_path, 'w') as f:
            f.write("# 3D point list with one line of data per point:\n")
            f.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
            f.write("# Number of points: 0\n")
        return
    
    with open(output_path, 'w') as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("# POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[] as (IMAGE_ID, POINT2D_IDX)\n")
        f.write("# Number of points: {}\n".format(len(points)))
        
        for i, (point, color) in enumerate(zip(points, colors), start=1):
            x, y, z = point
            
            # Apply same coordinate transformation as cameras if orientation fix is enabled
            if fix_orientation:
                # OPENGL @ rot_y180 transformation (same as camera poses)
                opengl_matrix = np.array([[1, 0, 0],
                                         [0, -1, 0],
                                         [0, 0, -1]])
                rot_y180_matrix = Rotation.from_euler('y', np.deg2rad(180)).as_matrix()
                combined_transform = opengl_matrix @ rot_y180_matrix
                
                # Transform point
                point_array = np.array([x, y, z])
                point_transformed = combined_transform @ point_array
                x, y, z = point_transformed[0], point_transformed[1], point_transformed[2]
            # Ensure RGB values are in valid range [0, 255] and integers
            r = max(0, min(255, int(round(color[0]))))
            g = max(0, min(255, int(round(color[1]))))
            b = max(0, min(255, int(round(color[2]))))
            error = 0.0  # Unknown error (Blender addon accepts 0.0)
            # Format: POINT3D_ID X Y Z R G B ERROR [TRACK...]
            # TRACK is optional - we omit it since we don't have 2D point correspondences
            f.write(f"{i} {x:.6f} {y:.6f} {z:.6f} {r} {g} {b} {error:.6f}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Convert MonST3R output to COLMAP format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for input path)
  python convert_to_colmap.py
  
  # Command-line mode
  python convert_to_colmap.py --input demo_tmp/lady-running
  python convert_to_colmap.py --input demo_tmp/lady-running --output colmap_output
  python convert_to_colmap.py --input /path/to/data --output /path/to/output
        """
    )
    
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to MonST3R output directory (contains pred_traj.txt, pred_intrinsics.txt, etc.). If not provided, will prompt interactively."
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to COLMAP output directory (default: sibling directory of input named 'colmap/')"
    )
    
    parser.add_argument(
        "--max-points",
        type=int,
        default=100000,
        help="Maximum number of 3D points to extract (default: 100000)"
    )
    
    parser.add_argument(
        "--copy-images",
        action="store_true",
        help="Copy images to output directory with sequential names (recommended for Blender import)"
    )
    
    parser.add_argument(
        "--copy-depth-maps",
        action="store_true",
        help="Convert and copy MonST3R depth maps (frame_*.npy) to COLMAP binary format (.geometric.bin) in stereo/depth_maps/ directory"
    )
    
    parser.add_argument(
        "--fix-camera-orientation",
        action="store_true",
        help="Apply OPENGL @ rot_y180 transformation to match GLB export coordinate system (ENABLED BY DEFAULT - use --no-fix-camera-orientation to disable)"
    )
    
    parser.add_argument(
        "--no-fix-camera-orientation",
        dest="fix_camera_orientation",
        action="store_false",
        help="Disable camera orientation fix (use if cameras are already correctly oriented)"
    )
    
    # Set default to True (orientation fix enabled by default to match GLB)
    parser.set_defaults(fix_camera_orientation=True)
    
    args = parser.parse_args()
    
    # Interactive input if --input not provided
    # IMPORTANT: Check args.input FIRST before any other logic
    # This ensures the input prompt always shows when --input is not provided
    if args.input is None:
        # We're in interactive mode - show input prompt
        interactive_mode = True
        print("=" * 60)
        print("MonST3R to COLMAP Converter - Interactive Mode")
        print("=" * 60)
        print("\n[INPUT] Please provide the MonST3R output directory path.")
        print("This directory should contain:")
        print("  - pred_traj.txt (camera trajectory)")
        print("  - pred_intrinsics.txt (camera intrinsics)")
        print("  - scene.glb (optional, 3D model)")
        print("  - frame_*.npy (optional, MonST3R depth maps)")
        print("  - depth_maps/ (optional, standard depth maps)")
        print("  - rgb_imgs/ (optional, RGB images)")
        print()
        
        while True:
            try:
                # Explicit prompt for input directory
                input_path = input("\n[INPUT] Enter path to MonST3R output directory: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled by user.")
                return 1
            
            # Remove quotes if user added them
            input_path = input_path.strip('"').strip("'")
            
            if not input_path:
                print("Error: Path cannot be empty. Please try again.")
                continue
            
            # Expand user home directory
            input_path = os.path.expanduser(input_path)
            
            # Convert to absolute path
            if not os.path.isabs(input_path):
                # If relative, make it relative to current directory
                input_path = os.path.abspath(input_path)
            
            if not os.path.exists(input_path):
                print(f"Error: Directory does not exist: {input_path}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    return 1
                continue
            
            if not os.path.isdir(input_path):
                print(f"Error: Path is not a directory: {input_path}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    return 1
                continue
            
            # Check for required files
            traj_file = os.path.join(input_path, "pred_traj.txt")
            intrinsics_file = os.path.join(input_path, "pred_intrinsics.txt")
            
            if not os.path.exists(traj_file):
                print(f"Warning: pred_traj.txt not found in {input_path}")
                proceed = input("Continue anyway? (y/n): ").strip().lower()
                if proceed != 'y':
                    retry = input("Try different path? (y/n): ").strip().lower()
                    if retry != 'y':
                        return 1
                    continue
            
            if not os.path.exists(intrinsics_file):
                print(f"Warning: pred_intrinsics.txt not found in {input_path}")
                proceed = input("Continue anyway? (y/n): ").strip().lower()
                if proceed != 'y':
                    retry = input("Try different path? (y/n): ").strip().lower()
                    if retry != 'y':
                        return 1
                    continue
            
            # Valid path found
            args.input = input_path
            break
    else:
        # Not in interactive mode - input was provided via command line
        interactive_mode = False
    
    # Validate input directory (should be set by now)
    if args.input is None:
        print("Error: Input directory not specified.")
        return 1
    
    input_dir = os.path.abspath(args.input)
    if not os.path.exists(input_dir):
        print(f"Error: Input directory does not exist: {input_dir}")
        return 1
    
    # Set default output path (sibling directory named "colmap/")
    # If output not provided and we're in interactive mode, optionally prompt
    if args.output is None:
        input_path = Path(input_dir)
        default_output = str(input_path.parent / "colmap")
        
        # If we were in interactive mode for input, also prompt for output
        if interactive_mode:
            print(f"\n[OUTPUT] Output directory (default: {default_output}): ", end="")
            try:
                user_output = input().strip()
            except (EOFError, KeyboardInterrupt):
                # Handle non-interactive environments
                user_output = ""
            
            if user_output:
                # Remove quotes if user added them
                user_output = user_output.strip('"').strip("'")
                output_dir = os.path.abspath(os.path.expanduser(user_output))
            else:
                output_dir = default_output
                print(f"Using default output directory: {output_dir}")
        else:
            output_dir = default_output
    else:
        output_dir = os.path.abspath(args.output)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("MonST3R to COLMAP Converter")
    print("=" * 60)
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Check required files
    traj_file = os.path.join(input_dir, "pred_traj.txt")
    intrinsics_file = os.path.join(input_dir, "pred_intrinsics.txt")
    glb_file = os.path.join(input_dir, "scene.glb")
    
    if not os.path.exists(traj_file):
        print(f"Error: Trajectory file not found: {traj_file}")
        return 1
    
    if not os.path.exists(intrinsics_file):
        print(f"Error: Intrinsics file not found: {intrinsics_file}")
        return 1
    
    # Parse input files
    print("Parsing trajectory file...")
    poses = parse_tum_trajectory(traj_file)
    print(f"  Found {len(poses)} camera poses")
    
    print("Parsing intrinsics file...")
    intrinsics = parse_intrinsics(intrinsics_file)
    print(f"  Found {len(intrinsics)} camera intrinsics")
    
    if len(poses) != len(intrinsics):
        print(f"Warning: Number of poses ({len(poses)}) != number of intrinsics ({len(intrinsics)})")
        min_len = min(len(poses), len(intrinsics))
        poses = poses[:min_len]
        intrinsics = intrinsics[:min_len]
        print(f"  Using first {min_len} entries")
    
    # Get image files
    print("Finding image files...")
    image_files = get_image_files(input_dir)
    if len(image_files) == 0:
        print("  Warning: No image files found, using placeholder names")
        image_files = [f"image_{i:04d}.png" for i in range(len(poses))]
    else:
        print(f"  Found {len(image_files)} image files")
    
    # Get image sizes
    print("Getting image dimensions...")
    image_sizes = []
    for img_file in image_files[:len(poses)]:
        if os.path.exists(img_file):
            size = get_image_size(img_file)
        else:
            # Use intrinsics to estimate size
            K = intrinsics[min(len(image_sizes), len(intrinsics) - 1)]
            size = (int(K[0, 2] * 2), int(K[1, 2] * 2))  # Estimate from principal point
        image_sizes.append(size)
    
    # Extract 3D points
    print("Extracting 3D points...")
    points = None
    colors = None
    
    # Try GLB first
    if os.path.exists(glb_file):
        print("  Trying GLB file...")
        points, colors = extract_3d_points_from_glb(glb_file, args.max_points)
        if points is not None:
            print(f"  Extracted {len(points)} points from GLB file")
    
    # Try depth maps if GLB didn't work
    if points is None:
        # Try standard depth_maps/ directory first
        depth_dir = os.path.join(input_dir, "depth_maps")
        rgb_dir = os.path.join(input_dir, "rgb_imgs")
        
        # Also check for MonST3R format: frame_*.npy files directly in input_dir
        if not os.path.exists(depth_dir):
            # Check if MonST3R depth maps exist (frame_*.npy)
            frame_files = [f for f in os.listdir(input_dir) if f.startswith('frame_') and f.endswith('.npy')]
            if len(frame_files) > 0:
                depth_dir = input_dir  # Use input_dir as depth_dir for MonST3R format
                print(f"  Found {len(frame_files)} MonST3R depth maps (frame_*.npy)")
        
        if os.path.exists(depth_dir) or depth_dir == input_dir:
            print("  Trying depth maps...")
            points, colors = extract_3d_points_from_depth(
                depth_dir, rgb_dir, intrinsics, poses, args.max_points
            )
            if points is not None:
                print(f"  Extracted {len(points)} points from depth maps")
    
    if points is None:
        print("  Warning: Could not extract 3D points. Creating empty points3D.txt")
    
    # Write COLMAP files
    print("\nWriting COLMAP files...")
    
    cameras_file = os.path.join(output_dir, "cameras.txt")
    print(f"  Writing {cameras_file}...")
    write_colmap_cameras(cameras_file, intrinsics, image_sizes)
    
    # Copy images if requested
    images_dir = None
    if args.copy_images:
        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        print(f"  Copying images to {images_dir}...")
        copied_count = 0
        for i, img_file in enumerate(image_files[:len(poses)], start=1):
            if img_file and os.path.exists(img_file):
                ext = os.path.splitext(img_file)[1] or '.png'
                new_name = f"image_{i:04d}{ext}"
                new_path = os.path.join(images_dir, new_name)
                try:
                    import shutil
                    shutil.copy2(img_file, new_path)
                    copied_count += 1
                except Exception as e:
                    print(f"    Warning: Could not copy {img_file}: {e}")
        print(f"    Copied {copied_count} images")
        # Update image_files to point to copied images
        image_files_copied = [os.path.join(images_dir, f"image_{i:04d}{os.path.splitext(f)[1] if os.path.exists(f) else '.png'}")
                              for i, f in enumerate(image_files[:len(poses)], start=1)]
    else:
        image_files_copied = image_files[:len(poses)]
    
    images_file = os.path.join(output_dir, "images.txt")
    print(f"  Writing {images_file}...")
    camera_ids = list(range(1, len(intrinsics) + 1))  # Simple: one camera per image
    # Pass images_dir if images were copied, otherwise None
    # The image_base_dir parameter tells write_colmap_images that images are in a subdirectory
    # IMPORTANT: Pass the images_dir path (not just a flag) so the function can detect the "images" subdirectory
    image_base_dir_param = images_dir if args.copy_images else None
    if image_base_dir_param:
        print(f"  Using image_base_dir: {image_base_dir_param}")
        print(f"  Images will be written with 'images/' prefix in images.txt")
    
    # Write images.txt and collect image names for depth map conversion
    image_names_list = []  # Will store image names from images.txt
    write_colmap_images(images_file, poses, image_files_copied, camera_ids, 
                       image_base_dir=image_base_dir_param, return_image_names=image_names_list,
                       fix_orientation=args.fix_camera_orientation)
    
    # Use collected image names if available, otherwise read from file
    image_names_for_depth = image_names_list if len(image_names_list) > 0 else None
    
    # Convert depth maps if requested
    if args.copy_depth_maps:
        print("\nConverting depth maps...")
        # Use collected image names if available, otherwise read from file
        if image_names_for_depth and len(image_names_for_depth) > 0:
            image_names_to_use = image_names_for_depth
        else:
            # Fallback: read image names from images.txt
            image_names_to_use = []
            if os.path.exists(images_file):
                with open(images_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 10:
                                image_name = parts[9]  # Image name is the 10th field
                                image_names_to_use.append(image_name)
        
        if len(image_names_to_use) > 0:
            converted_count = convert_depth_maps_to_colmap_format(
                input_dir, output_dir, image_names_to_use, image_base_dir_param
            )
            if converted_count > 0:
                print(f"  Converted {converted_count} depth maps to COLMAP binary format")
                depth_map_path = os.path.join(output_dir, 'stereo', 'depth_maps')
                print(f"  Depth maps saved to: {depth_map_path}")
            else:
                print("  No depth maps found to convert")
                print("  Looking for: frame_*.npy files in input directory")
        else:
            print("  Warning: Could not determine image names for depth map conversion")
    
    points3d_file = os.path.join(output_dir, "points3D.txt")
    print(f"  Writing {points3d_file}...")
    write_colmap_points3d(points3d_file, points, colors, fix_orientation=args.fix_camera_orientation)
    
    print("\n" + "=" * 60)
    print("Conversion complete!")
    print("=" * 60)
    print(f"\nCOLMAP files written to: {output_dir}")
    print(f"  - cameras.txt ({len(intrinsics)} cameras)")
    print(f"  - images.txt ({len(poses)} images)")
    if points is not None:
        print(f"  - points3D.txt ({len(points)} points)")
    else:
        print(f"  - points3D.txt (empty)")
    print("\nTo use with COLMAP:")
    print(f"  colmap model_converter --input_path {output_dir} --output_path {output_dir} --output_type BIN")
    
    if args.copy_images:
        print(f"\nNote: Images have been copied to {images_dir}/")
        print("  The images.txt file references these copied images.")
    else:
        print(f"\nNote: Images are referenced from the input directory.")
        print("  If Blender addon can't find images, use --copy-images flag:")
        print(f"  python convert_to_colmap.py --input {args.input} --output {output_dir} --copy-images")
    
    if args.copy_depth_maps:
        depth_map_path = os.path.join(output_dir, 'stereo', 'depth_maps')
        if os.path.exists(depth_map_path):
            print("\n" + "=" * 60)
            print("Depth Maps for Blender Addon")
            print("=" * 60)
            print("Depth maps have been converted to COLMAP binary format.")
            print(f"Location: {depth_map_path}")
            print("\nTo use depth maps in Blender:")
            print("  1. Import COLMAP workspace (select the output directory)")
            print("  2. Enable 'Add Depth Maps (EXPERIMENTAL)' option")
            print("  3. Depth maps will be displayed as point clouds")
            print("\nNote: Depth maps are matched to cameras by image name from images.txt")
    
    if args.fix_camera_orientation:
        print("\n" + "=" * 60)
        print("Camera Orientation Fix Applied")
        print("=" * 60)
        print("Applied OPENGL @ rot_y180 transformation to match GLB export.")
        print("This ensures camera orientations match the GLB file shown in Blender.")
        print("\nIf cameras point wrong direction, try --no-fix-camera-orientation")
    
    return 0


if __name__ == "__main__":
    exit(main())
