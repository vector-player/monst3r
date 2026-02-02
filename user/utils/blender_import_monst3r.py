"""
Blender Script to Import and Visualize MonST3R Results

Usage:
1. Open Blender
2. Go to Scripting workspace
3. Open this file: File → Open → select this script
4. Configure MONST3R_ROOT_PATH and SEQUENCE_NAME at the top (if needed)
5. Run the script (Alt+P or click Run button)

Configuration:
- MONST3R_ROOT_PATH: Set to your MonST3R root directory, or None for auto-detection
- SEQUENCE_NAME: Name of your sequence (default: "lady-running")
- All other paths are automatically derived from these two variables
"""

import bpy
import os
from mathutils import Quaternion

# ============================================================================
# CONFIGURATION - UPDATE THIS PATH
# ============================================================================
#
# IMPORTANT: Set the MonST3R root directory path here.
# Leave as None to auto-detect, or set to your actual path:
#
# Examples:
#   MONST3R_ROOT_PATH = r"D:\ProgramData\monst3r"           # Windows absolute path
#   MONST3R_ROOT_PATH = "/root/monst3r"                     # Linux absolute path
#   MONST3R_ROOT_PATH = None                                # Auto-detect (default)
#

MONST3R_ROOT_PATH = None  # Set to None for auto-detection, or set your path here

# Sequence name (subdirectory in demo_tmp)
SEQUENCE_NAME = "lady-running"  # Change this if your sequence has a different name

# ============================================================================
# AUTO-DETECTION LOGIC (runs if MONST3R_ROOT_PATH is None)
# ============================================================================

def detect_monst3r_root():
    """Auto-detect MonST3R root directory"""
    # Try to get script directory first
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Assuming script is in: monst3r/user/docs/blender_visualization/
        # Go up to monst3r root: ../../../
        detected_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
        # Verify it's correct
        if os.path.exists(os.path.join(detected_root, "demo_tmp")):
            return detected_root
    except NameError:
        pass  # __file__ not available, continue with other methods
    
    # Common Windows locations (checked first to avoid false positives)
    common_paths = [
        r"D:\ProgramData\monst3r",
        r"C:\monst3r",
        r"D:\monst3r",
        os.path.expanduser(r"~\monst3r"),  # User home
        "/root/monst3r",  # Linux default
    ]
    
    # Check current directory and parents
    cwd = os.getcwd()
    relative_paths = [
        cwd,
        os.path.join(cwd, "monst3r"),
        os.path.dirname(cwd),
        os.path.dirname(os.path.dirname(cwd)),
    ]
    
    # Check all possible paths
    all_paths = common_paths + relative_paths
    
    for root in all_paths:
        if not root or not os.path.exists(root):
            continue
        
        # Verify it's a MonST3R root by checking for demo_tmp and MonST3R files
        demo_tmp_path = os.path.join(root, "demo_tmp")
        if os.path.exists(demo_tmp_path):
            # Additional verification
            verification_paths = [
                os.path.join(demo_tmp_path, SEQUENCE_NAME),
                os.path.join(root, "demo.py"),
                os.path.join(root, "dust3r"),
            ]
            if any(os.path.exists(vp) for vp in verification_paths):
                return root
    
    return None

# Get MonST3R root (use provided path or auto-detect)
if MONST3R_ROOT_PATH is None:
    MONST3R_ROOT = detect_monst3r_root()
    if MONST3R_ROOT is None:
        # Default fallback
        MONST3R_ROOT = r"D:\ProgramData\monst3r" if os.name == 'nt' else "/root/monst3r"
        print(f"Warning: Could not auto-detect MonST3R root.")
        print(f"Using default: {MONST3R_ROOT}")
        print(f"To fix: Set MONST3R_ROOT_PATH at the top of this script.")
else:
    MONST3R_ROOT = MONST3R_ROOT_PATH

# ============================================================================
# DERIVED PATHS (automatically computed from MONST3R_ROOT)
# ============================================================================

DEMO_TMP_DIR = os.path.join(MONST3R_ROOT, "demo_tmp", SEQUENCE_NAME)

# GLB file path (relative to DEMO_TMP_DIR or absolute)
GLB_FILE = os.path.join(DEMO_TMP_DIR, "scene.glb")

# Trajectory file path
TRAJ_FILE = os.path.join(DEMO_TMP_DIR, "pred_traj.txt")

# Options
IMPORT_SCENE = True          # Import the 3D scene GLB file
IMPORT_CAMERAS = True       # Import camera trajectory
CREATE_ANIMATION = False    # Create animated camera sequence
SAMPLE_CAMERAS = 10         # Import every Nth camera (1 = all cameras)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clear_scene():
    """Clear all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Clear materials
    for material in bpy.data.materials:
        bpy.data.materials.remove(material)

def load_tum_trajectory(filepath):
    """Load TUM format trajectory file
    
    Format: timestamp tx ty tz qx qy qz qw
    Returns: list of (timestamp, position, quaternion) tuples
    """
    poses = []
    if not os.path.exists(filepath):
        print(f"Warning: Trajectory file not found: {filepath}")
        return poses
    
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
                    # TUM format: qx qy qz qw, but Blender uses w x y z
                    quat = [float(parts[7]), float(parts[4]), float(parts[5]), float(parts[6])]
                    poses.append((timestamp, pos, quat))
                except ValueError:
                    continue
    return poses

def setup_lighting():
    """Add lights to the scene"""
    # Clear existing lights
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            obj.select_set(True)
    bpy.ops.object.delete()
    
    # Add sun light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    sun = bpy.context.active_object
    sun.data.energy = 3.0
    sun.data.angle = 0.1
    
    # Add area light
    bpy.ops.object.light_add(type='AREA', location=(-5, -5, 5))
    area = bpy.context.active_object
    area.data.energy = 100.0
    area.data.size = 10.0
    
    # Add world lighting
    world = bpy.context.scene.world
    if world:
        world.use_nodes = True
        bg = world.node_tree.nodes['Background']
        bg.inputs['Strength'].default_value = 0.5

def create_camera_from_pose(location, quaternion, name, frame=None):
    """Create a camera object at given pose"""
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.active_object
    camera.name = name
    
    # Set rotation from quaternion
    q = Quaternion(quaternion)
    camera.rotation_euler = q.to_euler()
    
    # Set keyframes if animating
    if frame is not None:
        camera.location = location
        camera.rotation_euler = q.to_euler()
        camera.keyframe_insert(data_path="location", frame=frame)
        camera.keyframe_insert(data_path="rotation_euler", frame=frame)
    
    return camera

# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    print("=" * 60)
    print("MonST3R Blender Import Script")
    print("=" * 60)
    
    # Clear existing scene
    print("Clearing scene...")
    clear_scene()
    
    # Import GLB scene
    if IMPORT_SCENE:
        # Check if file exists
        if not os.path.exists(GLB_FILE):
            print(f"✗ GLB file not found: {GLB_FILE}")
            print(f"\n  Debugging information:")
            print(f"  - MonST3R root detected: {MONST3R_ROOT}")
            print(f"  - DEMO_TMP_DIR: {DEMO_TMP_DIR}")
            print(f"  - Current working directory: {os.getcwd()}")
            
            # Try to find the actual file location using common paths
            print(f"\n  Searching for scene.glb in common locations...")
            common_roots = [
                r"D:\ProgramData\monst3r",
                r"C:\monst3r",
                r"D:\monst3r",
                os.path.expanduser(r"~\monst3r"),
                "/root/monst3r",
            ]
            
            search_paths = [
                os.path.join(root, "demo_tmp", SEQUENCE_NAME, "scene.glb")
                for root in common_roots
            ]
            
            found_path = None
            for search_path in search_paths:
                if os.path.exists(search_path):
                    found_path = search_path
                    found_root = os.path.dirname(os.path.dirname(os.path.dirname(search_path)))
                    print(f"  ✓ Found GLB file at: {search_path}")
                    break
            
            if found_path:
                print(f"\n  Solution: Edit the script and set at the top:")
                print(f"  MONST3R_ROOT_PATH = r\"{found_root}\"")
                print(f"\n  Or import manually:")
                print(f"  File → Import → glTF 2.0 → {found_path}")
            else:
                print(f"  ✗ Could not find scene.glb in common locations")
                print(f"\n  Solution: Set MONST3R_ROOT_PATH at the top of this script")
                print(f"  Example:")
                print(f"  MONST3R_ROOT_PATH = r\"D:\\ProgramData\\monst3r\"")
                print(f"  SEQUENCE_NAME = \"lady-running\"")
        else:
            print(f"Importing GLB file: {GLB_FILE}")
            try:
                bpy.ops.import_scene.gltf(filepath=GLB_FILE)
                print("✓ GLB file imported successfully")
            except Exception as e:
                print(f"✗ Error importing GLB: {e}")
                import traceback
                traceback.print_exc()
    
    # Setup lighting
    print("Setting up lighting...")
    setup_lighting()
    
    # Import camera trajectory
    if IMPORT_CAMERAS:
        print(f"Loading camera trajectory: {TRAJ_FILE}")
        if not os.path.exists(TRAJ_FILE):
            print(f"  Warning: Trajectory file not found: {TRAJ_FILE}")
            print(f"  Camera import will be skipped.")
        poses = load_tum_trajectory(TRAJ_FILE)
        
        if poses:
            print(f"Found {len(poses)} camera poses")
            
            if CREATE_ANIMATION:
                # Create animated camera
                print("Creating animated camera sequence...")
                if poses:
                    first_pose = poses[0]
                    camera = create_camera_from_pose(
                        first_pose[1], 
                        first_pose[2], 
                        "AnimatedCamera",
                        frame=1
                    )
                    
                    # Set keyframes for all poses
                    bpy.context.scene.frame_start = 1
                    bpy.context.scene.frame_end = len(poses)
                    
                    for frame, (timestamp, pos, quat) in enumerate(poses, start=1):
                        bpy.context.scene.frame_set(frame)
                        camera.location = pos
                        q = Quaternion(quat)
                        camera.rotation_euler = q.to_euler()
                        camera.keyframe_insert(data_path="location", index=-1)
                        camera.keyframe_insert(data_path="rotation_euler", index=-1)
                    
                    bpy.context.scene.camera = camera
                    print(f"✓ Created animation with {len(poses)} frames")
            else:
                # Create static cameras
                print(f"Creating camera objects (sampling every {SAMPLE_CAMERAS}th)...")
                cameras_created = 0
                for i, (timestamp, pos, quat) in enumerate(poses):
                    if i % SAMPLE_CAMERAS == 0:
                        camera = create_camera_from_pose(
                            pos, 
                            quat, 
                            f"Camera_{i:04d}"
                        )
                        cameras_created += 1
                
                # Set first camera as active
                if cameras_created > 0:
                    first_camera = bpy.data.objects.get("Camera_0000")
                    if first_camera:
                        bpy.context.scene.camera = first_camera
                    print(f"✓ Created {cameras_created} camera objects")
        else:
            print("✗ No camera poses found in trajectory file")
    
    # Set viewport settings
    print("Configuring viewport...")
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.shading.use_scene_world = True
    
    # Frame all objects
    print("Framing scene...")
    try:
        # Try to frame all objects in viewport
        # Method 1: Use context override (Blender 3.0+)
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                # Get the 3D viewport region
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {
                            'area': area,
                            'region': region,
                            'space_data': area.spaces.active,
                        }
                        try:
                            bpy.ops.view3d.view_all(override)
                        except (ValueError, TypeError):
                            # Fallback: use context directly
                            with bpy.context.temp_override(**override):
                                bpy.ops.view3d.view_all()
                        break
                break
    except Exception as e:
        print(f"Note: Could not auto-frame scene ({e}). Press Home key to frame manually.")
    
    print("=" * 60)
    print("Import complete!")
    print("=" * 60)
    print("\nTips:")
    print("- Press Z to change viewport shading mode")
    print("- Press N to open properties panel")
    print("- Press Home to frame all objects")
    print("- Use middle mouse button to navigate")
    if CREATE_ANIMATION:
        print("- Press Space to play animation")
        print("- Press F12 to render animation")

if __name__ == "__main__":
    main()
