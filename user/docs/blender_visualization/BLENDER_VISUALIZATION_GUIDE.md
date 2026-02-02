# Blender Visualization Guide for MonST3R Results

This guide explains how to visualize MonST3R reconstruction results from `demo_tmp` in Blender.

## 📁 Output Files Structure

When you run MonST3R with `--output_dir demo_tmp`, the following files are generated in `demo_tmp/{seq_name}/`:

```
demo_tmp/
└── {seq_name}/
    ├── scene.glb              # 3D scene model (mesh or point cloud)
    ├── pred_traj.txt          # Camera trajectory (TUM format)
    ├── pred_intrinsics.txt    # Camera intrinsics
    ├── depth_maps/            # Depth maps for each frame
    ├── dynamic_masks/         # Dynamic object masks
    ├── conf_maps/             # Confidence maps
    ├── rgb_imgs/              # RGB images
    └── frame_*.npy            # Various numpy arrays
```

## 🎨 Method 1: Direct GLB Import (Recommended)

The easiest way to visualize results is to import the GLB file directly into Blender.

### Steps:

1. **Open Blender**
   - Launch Blender (version 2.8+ recommended)

2. **Import GLB File**
   - Go to `File` → `Import` → `glTF 2.0 (.glb/.gltf)`
   - Navigate to `demo_tmp/{seq_name}/scene.glb`
   - Click `Import glTF 2.0`

3. **View the Scene**
   - The scene will be imported with:
     - **3D Mesh/Point Cloud**: The reconstructed 3D geometry
     - **Camera Objects**: Camera frustums showing camera poses (if `show_cam=True`)
     - **Textures**: RGB colors mapped to the geometry

4. **Navigation**
   - **Rotate**: Middle mouse button + drag
   - **Pan**: Shift + Middle mouse button + drag
   - **Zoom**: Scroll wheel or Ctrl + Middle mouse button

5. **Rendering**
   - Press `Z` to open render mode menu
   - Select `Material Preview` or `Rendered` to see textures
   - Press `F12` to render the scene

## 🔧 Method 2: Python Script for Advanced Visualization

For more control, you can use a Python script in Blender's scripting workspace.

### Blender Python Script:

```python
import bpy
import os

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Set path to your GLB file
glb_path = "/path/to/demo_tmp/lady-running/scene.glb"

# Import GLB file
bpy.ops.import_scene.gltf(filepath=glb_path)

# Set up lighting
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
sun = bpy.context.active_object
sun.data.energy = 3.0

# Add area light for better illumination
bpy.ops.object.light_add(type='AREA', location=(-5, -5, 5))
area = bpy.context.active_object
area.data.energy = 100.0
area.data.size = 10.0

# Set camera view
bpy.ops.object.camera_add(location=(0, -10, 5))
camera = bpy.context.active_object
camera.rotation_euler = (1.1, 0, 0)  # Point camera at scene
bpy.context.scene.camera = camera

# Set render engine to Cycles for better quality
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 128

# Set viewport shading to Material Preview
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
```

### How to Use:

1. Open Blender
2. Switch to `Scripting` workspace (top menu)
3. Click `New` to create a new script
4. Paste the script above
5. Update `glb_path` to your actual file path
6. Click `Run Script` (▶️ button)

## 📊 Method 3: Import Camera Trajectory

To visualize the camera trajectory separately:

### Python Script to Import Camera Poses:

```python
import bpy
import numpy as np

def load_tum_trajectory(filepath):
    """Load TUM format trajectory file"""
    poses = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) >= 8:
                # TUM format: timestamp tx ty tz qx qy qz qw
                t = float(parts[0])
                pos = [float(parts[1]), float(parts[2]), float(parts[3])]
                quat = [float(parts[7]), float(parts[4]), float(parts[5]), float(parts[6])]  # w, x, y, z
                poses.append((t, pos, quat))
    return poses

# Clear existing cameras
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Load trajectory
traj_path = "/path/to/demo_tmp/lady-running/pred_traj.txt"
poses = load_tum_trajectory(traj_path)

# Create camera for each pose
for i, (timestamp, pos, quat) in enumerate(poses[::10]):  # Sample every 10th frame
    bpy.ops.object.camera_add(location=pos)
    camera = bpy.context.active_object
    camera.name = f"Camera_{i:04d}"
    
    # Convert quaternion to rotation
    from mathutils import Quaternion
    q = Quaternion(quat)
    camera.rotation_euler = q.to_euler()

# Set first camera as active
if bpy.data.objects.get("Camera_0000"):
    bpy.context.scene.camera = bpy.data.objects["Camera_0000"]
```

## 🎬 Method 4: Animate Camera Sequence

To create an animation following the camera trajectory:

```python
import bpy
import numpy as np
from mathutils import Quaternion

def load_tum_trajectory(filepath):
    """Load TUM format trajectory file"""
    poses = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split()
            if len(parts) >= 8:
                t = float(parts[0])
                pos = [float(parts[1]), float(parts[2]), float(parts[3])]
                quat = [float(parts[7]), float(parts[4]), float(parts[5]), float(parts[6])]
                poses.append((t, pos, quat))
    return poses

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import GLB scene
glb_path = "/path/to/demo_tmp/lady-running/scene.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)

# Load trajectory
traj_path = "/path/to/demo_tmp/lady-running/pred_traj.txt"
poses = load_tum_trajectory(traj_path)

# Create animated camera
bpy.ops.object.camera_add(location=(0, 0, 0))
camera = bpy.context.active_object
camera.name = "AnimatedCamera"

# Set keyframes
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = len(poses)

for frame, (timestamp, pos, quat) in enumerate(poses, start=1):
    bpy.context.scene.frame_set(frame)
    camera.location = pos
    q = Quaternion(quat)
    camera.rotation_euler = q.to_euler()
    camera.keyframe_insert(data_path="location", index=-1)
    camera.keyframe_insert(data_path="rotation_euler", index=-1)

# Set as active camera
bpy.context.scene.camera = camera

# Set render settings
bpy.context.scene.render.fps = 30
bpy.context.scene.render.frame_map_new = len(poses)
```

## 🔍 Understanding the GLB File Contents

The `scene.glb` file exported by MonST3R contains:

1. **3D Geometry**:
   - **Mesh mode** (`as_pointcloud=False`): Textured triangular mesh
   - **Point cloud mode** (`as_pointcloud=True`): Colored point cloud

2. **Camera Frustums** (if `show_cam=True`):
   - Visual representation of camera poses
   - Colored edges showing camera orientation
   - Optional image planes showing camera views

3. **Coordinate System**:
   - Uses OpenGL convention (Y-up)
   - Transformed to align with first camera pose

## 💡 Tips for Better Visualization

1. **Material Settings**:
   - Select the mesh object
   - Go to `Material Properties` tab
   - Adjust `Metallic` and `Roughness` for better appearance

2. **Lighting**:
   - Add multiple lights from different angles
   - Use `World` → `Surface` → `Background` for environment lighting

3. **Viewport Settings**:
   - Press `N` to open properties panel
   - Enable `Wireframe` overlay to see mesh structure
   - Adjust `Viewport Display` → `Color` for better visibility

4. **Export Options**:
   - You can re-export from Blender in other formats (OBJ, PLY, STL)
   - Use `File` → `Export` → `glTF 2.0` to save modified scene

## 🐛 Troubleshooting

### GLB file won't import:
- **Check Blender version**: Requires Blender 2.8+ with glTF 2.0 support
- **File path**: Ensure the path is correct and file exists
- **File size**: Very large GLB files may take time to load

### Scene appears empty:
- **Check viewport**: Press `Home` to frame all objects
- **Check layers**: Ensure objects aren't on hidden layers
- **Scale**: The scene might be very small/large - use `S` to scale

### Textures not showing:
- **Material Preview**: Switch to `Material Preview` or `Rendered` mode
- **UV Maps**: Ensure UV maps are properly assigned
- **Image Paths**: Check if texture images are in the same directory

## 📚 Additional Resources

- **Blender Documentation**: https://docs.blender.org/
- **glTF 2.0 Specification**: https://www.khronos.org/gltf/
- **Trimesh Documentation**: https://trimsh.org/

## 🔗 Related Files

- **GLB Export Code**: `dust3r/utils/viz_demo.py` → `convert_scene_output_to_glb()`
- **Demo Script**: `demo.py`
- **Visualization Utils**: `dust3r/viz.py`

---

**Last Updated**: Based on MonST3R output structure and Blender 3.0+ compatibility
