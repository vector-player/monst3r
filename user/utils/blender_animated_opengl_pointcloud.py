"""
Blender Script: Animated OpenGL Point Cloud from MonST3R Output

This script creates an animated point cloud visualization in Blender using OpenGL
that updates per frame based on MonST3R's per-frame depth maps and camera poses.

Usage:
1. Set MONST3R_OUTPUT_DIR to your MonST3R output directory
2. Open Blender Scripting workspace
3. Run this script (Alt+P or click Run button)
4. Scrub timeline or press Space to see animated point cloud

Features:
- Loads per-frame depth maps and RGB images
- Converts depth maps to 3D point clouds using camera poses/intrinsics
- Uses OpenGL for efficient rendering of large point clouds
- Updates point cloud automatically when timeline frame changes
- Supports dynamic mask filtering (optional)
"""

import bpy
import numpy as np
import os
from mathutils import Vector, Matrix
from bpy.app.handlers import persistent

# Try to import the photogrammetry importer's OpenGL utilities
try:
    from photogrammetry_importer.opengl.draw_manager import DrawManager
    from photogrammetry_importer.blender_utility.object_utility import add_empty
    HAS_PHOTOGRAMMETRY_IMPORTER = True
except ImportError:
    print("Warning: photogrammetry_importer not found. Using simplified OpenGL implementation.")
    HAS_PHOTOGRAMMETRY_IMPORTER = False
    import gpu
    from gpu_extras.batch import batch_for_shader

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to MonST3R output directory (where frame_*.npy, pred_traj.txt are located)
MONST3R_OUTPUT_DIR = None  # e.g., "/root/monst3r/demo_tmp/lady-running"

# Point cloud settings
POINT_SIZE = 2  # Size of points in pixels
USE_DYNAMIC_MASK = False  # Filter points using dynamic_mask_*.png files
MASK_THRESHOLD = 0.5  # Threshold for dynamic mask (0-1)
SUBSAMPLE_POINTS = 1  # Use every Nth point (1 = all points, 2 = every other point, etc.)
MAX_POINTS_PER_FRAME = 100000  # Limit points per frame for performance

# Collection name
POINT_CLOUD_COLLECTION_NAME = "AnimatedPointCloud"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_tum_trajectory(filepath):
    """Parse TUM format trajectory file"""
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
                    pos = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
                    quat = np.array([float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])])
                    # Convert quaternion (qx, qy, qz, qw) to rotation matrix
                    try:
                        from scipy.spatial.transform import Rotation
                        rot = Rotation.from_quat([quat[0], quat[1], quat[2], quat[3]])
                        R = rot.as_matrix()
                    except ImportError:
                        # Fallback: manual quaternion to rotation matrix conversion
                        qx, qy, qz, qw = quat[0], quat[1], quat[2], quat[3]
                        R = np.array([
                            [1 - 2*(qy**2 + qz**2), 2*(qx*qy - qw*qz), 2*(qx*qz + qw*qy)],
                            [2*(qx*qy + qw*qz), 1 - 2*(qx**2 + qz**2), 2*(qy*qz - qw*qx)],
                            [2*(qx*qz - qw*qy), 2*(qy*qz + qw*qx), 1 - 2*(qx**2 + qy**2)]
                        ])
                    # Build 4x4 transformation matrix (camera-to-world)
                    T = np.eye(4)
                    T[:3, :3] = R
                    T[:3, 3] = pos
                    poses.append(T)
                except ValueError:
                    continue
    return poses

def parse_intrinsics(filepath):
    """Parse intrinsics file (3x3 matrix flattened)"""
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
                    K = np.array([
                        [float(parts[0]), float(parts[1]), float(parts[2])],
                        [float(parts[3]), float(parts[4]), float(parts[5])],
                        [float(parts[6]), float(parts[7]), float(parts[8])]
                    ])
                    intrinsics.append(K)
                except ValueError:
                    continue
    return intrinsics

def depthmap_to_pts3d(depth, intrinsics, cam2world=None):
    """
    Convert depth map to 3D points.
    
    Args:
        depth: (H, W) depth map
        intrinsics: (3, 3) camera intrinsics matrix
        cam2world: (4, 4) camera-to-world transformation (optional)
    
    Returns:
        pts3d: (H, W, 3) 3D points
        mask: (H, W) valid mask
    """
    H, W = depth.shape
    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    cx, cy = intrinsics[0, 2], intrinsics[1, 2]
    
    # Create pixel grid
    y, x = np.meshgrid(np.arange(H), np.arange(W), indexing='ij')
    
    # Convert to camera coordinates
    X_cam = (x - cx) * depth / fx
    Y_cam = (y - cy) * depth / fy
    Z_cam = depth
    
    # Stack into (H, W, 3)
    pts3d_cam = np.stack([X_cam, Y_cam, Z_cam], axis=-1)
    
    # Valid mask (non-zero depth)
    mask = depth > 0
    
    # Transform to world coordinates if provided
    if cam2world is not None:
        # Reshape to (H*W, 3) for transformation
        pts_flat = pts3d_cam.reshape(-1, 3)
        valid_flat = mask.reshape(-1)
        
        # Apply transformation
        pts_hom = np.hstack([pts_flat, np.ones((pts_flat.shape[0], 1))])
        pts_world_hom = (cam2world @ pts_hom.T).T
        pts_world = pts_world_hom[:, :3]
        
        # Reshape back
        pts3d = pts_world.reshape(H, W, 3)
    else:
        pts3d = pts3d_cam
    
    return pts3d, mask

def load_image_as_array(image_path):
    """Load image and return as numpy array"""
    try:
        img = bpy.data.images.load(image_path)
        # Convert to numpy array (RGBA)
        pixels = np.array(img.pixels).reshape(img.size[1], img.size[0], -1)
        # Convert to RGB (remove alpha if present)
        if pixels.shape[2] == 4:
            pixels = pixels[:, :, :3]
        return pixels
    except Exception as e:
        print(f"Warning: Could not load image {image_path}: {e}")
        return None

# ============================================================================
# OPENGL POINT CLOUD HANDLER (Simplified if photogrammetry_importer not available)
# ============================================================================

if not HAS_PHOTOGRAMMETRY_IMPORTER:
    class SimpleDrawHandler:
        """Simplified OpenGL draw handler for point clouds"""
        def __init__(self):
            self.shader = gpu.shader.from_builtin("FLAT_COLOR")
            self.batch = None
            self.point_size = POINT_SIZE
            self.handle = None
        
        def update_points(self, coords, colors):
            """Update point cloud data"""
            if len(coords) == 0:
                return
            
            # Ensure colors are in correct format (RGBA, 0-1 range)
            if colors.shape[1] == 3:
                colors_rgba = np.hstack([colors, np.ones((colors.shape[0], 1))])
            else:
                colors_rgba = colors
            
            # Normalize colors to 0-1 if needed
            if colors_rgba.max() > 1.0:
                colors_rgba = colors_rgba / 255.0
            
            self.batch = batch_for_shader(
                self.shader, "POINTS",
                {"pos": coords.tolist(), "color": colors_rgba.tolist()}
            )
        
        def draw_callback(self):
            """Draw callback function"""
            if self.batch is None:
                return
            
            self.shader.bind()
            gpu.state.point_size_set(self.point_size)
            
            prev_depth_mask = gpu.state.depth_mask_get()
            prev_depth_test = gpu.state.depth_test_get()
            gpu.state.depth_mask_set(True)
            gpu.state.depth_test_set("LESS_EQUAL")
            
            self.batch.draw(self.shader)
            
            gpu.state.depth_mask_set(prev_depth_mask)
            gpu.state.depth_test_set(prev_depth_test)
        
        def register(self):
            """Register draw handler"""
            if self.handle is None:
                self.handle = bpy.types.SpaceView3D.draw_handler_add(
                    self.draw_callback, (), 'WINDOW', 'POST_VIEW'
                )
        
        def unregister(self):
            """Unregister draw handler"""
            if self.handle is not None:
                bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
                self.handle = None

# ============================================================================
# ANIMATED POINT CLOUD MANAGER
# ============================================================================

class AnimatedPointCloudManager:
    """Manages animated point cloud visualization"""
    
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.frame_data = {}  # Store per-frame point cloud data
        self.current_frame = -1
        self.anchor_obj = None
        self.draw_handler = None
        self.num_frames = 0
        
        # Load data
        self._load_data()
        
        # Setup OpenGL handler
        self._setup_opengl_handler()
        
        # Register frame change handler
        self._register_frame_handler()
    
    def _load_data(self):
        """Load all per-frame data"""
        print("Loading MonST3R output data...")
        
        # Find all depth map files
        depth_files = sorted([f for f in os.listdir(self.output_dir) 
                             if f.startswith('frame_') and f.endswith('.npy')])
        
        if len(depth_files) == 0:
            raise FileNotFoundError(f"No depth map files found in {self.output_dir}")
        
        self.num_frames = len(depth_files)
        print(f"Found {self.num_frames} frames")
        
        # Load camera poses and intrinsics
        traj_file = os.path.join(self.output_dir, "pred_traj.txt")
        intrinsics_file = os.path.join(self.output_dir, "pred_intrinsics.txt")
        
        poses = parse_tum_trajectory(traj_file)
        intrinsics = parse_intrinsics(intrinsics_file)
        
        if len(intrinsics) == 0:
            # Use default intrinsics if not found
            print("Warning: No intrinsics file found, using defaults")
            intrinsics = [np.array([[433.7, 0, 256], [0, 433.7, 144], [0, 0, 1]])] * self.num_frames
        
        if len(poses) != self.num_frames:
            print(f"Warning: Number of poses ({len(poses)}) != frames ({self.num_frames})")
            if len(poses) > self.num_frames:
                poses = poses[:self.num_frames]
            else:
                # Extend with last pose
                poses.extend([poses[-1]] * (self.num_frames - len(poses)))
        
        if len(intrinsics) != self.num_frames:
            if len(intrinsics) > self.num_frames:
                intrinsics = intrinsics[:self.num_frames]
            else:
                intrinsics.extend([intrinsics[-1]] * (self.num_frames - len(intrinsics)))
        
        # Load per-frame data
        for i, depth_file in enumerate(depth_files):
            frame_idx = int(depth_file.split('_')[1].split('.')[0])
            
            # Load depth map
            depth_path = os.path.join(self.output_dir, depth_file)
            depth = np.load(depth_path)
            
            # Load RGB image
            rgb_path = os.path.join(self.output_dir, f"frame_{frame_idx:04d}.png")
            rgb = load_image_as_array(rgb_path)
            
            # Load dynamic mask if enabled
            mask = None
            if USE_DYNAMIC_MASK:
                mask_path = os.path.join(self.output_dir, f"dynamic_mask_{frame_idx}.png")
                if os.path.exists(mask_path):
                    mask_img = load_image_as_array(mask_path)
                    if mask_img is not None:
                        # Convert to grayscale and threshold
                        mask_gray = mask_img.mean(axis=2) if mask_img.shape[2] > 1 else mask_img[:, :, 0]
                        mask = (mask_gray / 255.0) > MASK_THRESHOLD
            
            # Convert depth to 3D points
            K = intrinsics[i] if i < len(intrinsics) else intrinsics[-1]
            pose = poses[i] if i < len(poses) else poses[-1]
            
            pts3d, valid_mask = depthmap_to_pts3d(depth, K, cam2world=pose)
            
            # Apply dynamic mask if available
            if mask is not None:
                valid_mask = valid_mask & mask
            
            # Extract valid points
            pts_valid = pts3d[valid_mask]
            colors_valid = rgb[valid_mask] if rgb is not None else None
            
            # Subsample if needed
            if SUBSAMPLE_POINTS > 1:
                pts_valid = pts_valid[::SUBSAMPLE_POINTS]
                if colors_valid is not None:
                    colors_valid = colors_valid[::SUBSAMPLE_POINTS]
            
            # Limit points for performance
            if len(pts_valid) > MAX_POINTS_PER_FRAME:
                indices = np.random.choice(len(pts_valid), MAX_POINTS_PER_FRAME, replace=False)
                pts_valid = pts_valid[indices]
                if colors_valid is not None:
                    colors_valid = colors_valid[indices]
            
            # Default colors if RGB not available
            if colors_valid is None:
                colors_valid = np.ones((len(pts_valid), 3)) * 128  # Gray
            
            # Store frame data
            self.frame_data[frame_idx] = {
                'coords': pts_valid,
                'colors': colors_valid
            }
            
            if (i + 1) % 10 == 0:
                print(f"Loaded {i + 1}/{self.num_frames} frames...")
        
        print(f"Successfully loaded {len(self.frame_data)} frames")
    
    def _setup_opengl_handler(self):
        """Setup OpenGL point cloud handler"""
        # Create anchor object
        collection = bpy.data.collections.get(POINT_CLOUD_COLLECTION_NAME)
        if collection is None:
            collection = bpy.data.collections.new(POINT_CLOUD_COLLECTION_NAME)
            bpy.context.scene.collection.children.link(collection)
        
        self.anchor_obj = bpy.data.objects.new("PointCloudAnchor", None)
        collection.objects.link(self.anchor_obj)
        
        if HAS_PHOTOGRAMMETRY_IMPORTER:
            # Use photogrammetry importer's draw manager
            draw_manager = DrawManager.get_singleton()
            # Register with empty data initially, will be updated per frame
            draw_manager.register_points_draw_callback(
                self.anchor_obj, [], [], POINT_SIZE
            )
            self.draw_manager = draw_manager
        else:
            # Use simplified handler
            self.draw_handler = SimpleDrawHandler()
            self.draw_handler.register()
    
    def _register_frame_handler(self):
        """Register frame change handler"""
        @persistent
        def on_frame_change(scene, depsgraph):
            """Update point cloud when frame changes"""
            current_frame = scene.frame_current - 1  # Convert to 0-indexed
            
            if current_frame != self.current_frame and current_frame in self.frame_data:
                self.current_frame = current_frame
                self._update_pointcloud(current_frame)
        
        # Remove existing handler if any
        if hasattr(bpy.app.handlers, 'frame_change_pre'):
            handlers = bpy.app.handlers.frame_change_pre
            # Remove our handler if it exists (by checking function name)
            handlers[:] = [h for h in handlers if not hasattr(h, '__name__') or h.__name__ != 'on_frame_change']
        
        bpy.app.handlers.frame_change_pre.append(on_frame_change)
        
        # Also update immediately
        self._update_pointcloud(0)
    
    def _update_pointcloud(self, frame_idx):
        """Update point cloud data for current frame"""
        if frame_idx not in self.frame_data:
            return
        
        data = self.frame_data[frame_idx]
        coords = data['coords']
        colors = data['colors']
        
        if HAS_PHOTOGRAMMETRY_IMPORTER:
            # Update using photogrammetry importer's draw manager
            draw_manager = DrawManager.get_singleton()
            
            # Remove old callback
            if self.anchor_obj.name in draw_manager._anchor_to_draw_callback_handler:
                handler = draw_manager.get_draw_callback_handler(self.anchor_obj)
                if handler and handler._draw_handler_handle:
                    bpy.types.SpaceView3D.draw_handler_remove(
                        handler._draw_handler_handle, "WINDOW"
                    )
            
            # Register new callback with current frame data
            draw_manager.register_points_draw_callback(
                self.anchor_obj, coords.tolist(), colors.tolist(), POINT_SIZE
            )
        else:
            # Update simplified handler
            if self.draw_handler:
                self.draw_handler.update_points(coords, colors)
        
        # Redraw viewport
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
                break

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function"""
    # Determine output directory
    if MONST3R_OUTPUT_DIR:
        output_dir = MONST3R_OUTPUT_DIR
    else:
        # Try to auto-detect
        blend_file_path = bpy.data.filepath
        if blend_file_path:
            possible_dirs = [
                os.path.join(os.path.dirname(blend_file_path), "demo_tmp", "lady-running"),
                os.path.dirname(blend_file_path),
            ]
            for dir_path in possible_dirs:
                if os.path.exists(os.path.join(dir_path, "pred_traj.txt")):
                    output_dir = dir_path
                    break
            else:
                print("ERROR: Could not detect MonST3R output directory.")
                print("Please set MONST3R_OUTPUT_DIR in the script.")
                return
        else:
            print("ERROR: Please set MONST3R_OUTPUT_DIR in the script.")
            return
    
    print(f"Using MonST3R output directory: {output_dir}")
    
    # Create animated point cloud manager
    try:
        manager = AnimatedPointCloudManager(output_dir)
        
        # Set timeline range
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = manager.num_frames
        
        print(f"\n✓ Successfully created animated point cloud!")
        print(f"  Frames: {bpy.context.scene.frame_start} to {bpy.context.scene.frame_end}")
        print(f"  Point size: {POINT_SIZE}")
        print(f"  Collection: {POINT_CLOUD_COLLECTION_NAME}")
        print(f"\nPress Space to play animation, or scrub timeline to see point cloud update")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    main()
