# How to Show Moving Point Cloud During Timeline in Blender

## Overview

MonST3R produces a **time-varying dynamic point cloud** along with per-frame camera poses and intrinsics. This document explains how to visualize per-frame point clouds in Blender with timeline animation.

## Current Implementation

### How MonST3R Exports Point Clouds

1. **Single Combined GLB Export** (`dust3r/utils/viz_demo.py`):
   - The `convert_scene_output_to_glb()` function creates a single GLB file with all point clouds combined:
   ```python
   # Line 26-29: Combines all frames into one point cloud
   pts = np.concatenate([p[m] for p, m in zip(pts3d, mask)])
   col = np.concatenate([p[m] for p, m in zip(imgs, mask)])
   pct = trimesh.PointCloud(pts.reshape(-1, 3), colors=col.reshape(-1, 3))
   scene.add_geometry(pct)
   ```

2. **Per-Frame Data Saved** (`dust3r/cloud_opt/base_opt.py`):
   - Depth maps: `frame_XXXX.npy` files (line 364)
   - RGB images: `frame_XXXX.png` files (line 345)
   - Dynamic masks: `dynamic_mask_X.png` files (line 351)
   - Camera poses: `pred_traj.txt` (TUM format)
   - Camera intrinsics: `pred_intrinsics.txt`

### Camera Animation (Already Implemented)

The codebase already has camera animation support:
- `user/utils/blender_import_cameras_from_glb.py` creates animated cameras with keyframes
- Uses `bpy.context.scene.frame_set()` and `keyframe_insert()` for animation

## Solution: Per-Frame Point Cloud Visualization

To show a **moving point cloud** during timeline, you need to create separate point cloud objects for each frame and control their visibility with keyframes.

### Approach 1: Per-Frame Point Cloud Objects with Visibility Keyframes

Create a Blender script that:

1. **Loads per-frame point clouds** from depth maps or saved data
2. **Creates separate point cloud objects** for each frame
3. **Sets visibility keyframes** so only one point cloud is visible per frame

```python
import bpy
import numpy as np
from dust3r.utils.geometry import depthmap_to_pts3d

def create_per_frame_pointclouds(output_dir, num_frames):
    """
    Create separate point cloud objects for each frame with visibility animation.
    """
    # Load depth maps and images
    depth_maps = []
    rgb_images = []
    for i in range(num_frames):
        depth = np.load(f'{output_dir}/frame_{i:04d}.npy')
        rgb = bpy.data.images.load(f'{output_dir}/frame_{i:04d}.png')
        depth_maps.append(depth)
        rgb_images.append(rgb)
    
    # Load camera poses and intrinsics
    poses = parse_tum_trajectory(f'{output_dir}/pred_traj.txt')
    intrinsics = parse_intrinsics(f'{output_dir}/pred_intrinsics.txt')
    
    # Create collection for point clouds
    collection = bpy.data.collections.new("PerFramePointClouds")
    bpy.context.scene.collection.children.link(collection)
    
    # Create point cloud object for each frame
    for frame_idx in range(num_frames):
        # Convert depth map to 3D points
        depth = depth_maps[frame_idx]
        K = intrinsics[frame_idx]  # 3x3 intrinsics matrix
        pose = poses[frame_idx]    # camera-to-world transform
        
        pts3d = depthmap_to_pts3d(depth, K, cam2world=pose)
        colors = rgb_images[frame_idx].pixels  # Get RGB colors
        
        # Create mesh object for this frame's point cloud
        mesh_name = f"PointCloud_Frame_{frame_idx:04d}"
        mesh = bpy.data.meshes.new(mesh_name)
        
        # Convert to mesh vertices (point cloud as mesh)
        vertices = pts3d.reshape(-1, 3)
        mesh.from_pydata(vertices, [], [])
        
        # Create object
        obj = bpy.data.objects.new(mesh_name, mesh)
        collection.objects.link(obj)
        
        # Set visibility keyframes
        # Hide all frames except current one
        for f in range(num_frames):
            bpy.context.scene.frame_set(f + 1)
            obj.hide_viewport = (f != frame_idx)
            obj.hide_render = (f != frame_idx)
            obj.keyframe_insert(data_path="hide_viewport", frame=f + 1)
            obj.keyframe_insert(data_path="hide_render", frame=f + 1)
    
    # Set timeline range
    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = num_frames
```

### Approach 2: Update Point Cloud Data Per Frame (More Efficient)

Use Blender's frame change handler to update point cloud data dynamically:

```python
import bpy
import numpy as np

# Store point cloud data per frame
point_cloud_data = {}

def load_point_cloud_data(output_dir, num_frames):
    """Pre-load all point cloud data"""
    global point_cloud_data
    for i in range(num_frames):
        depth = np.load(f'{output_dir}/frame_{i:04d}.npy')
        rgb = load_image(f'{output_dir}/frame_{i:04d}.png')
        # Convert to 3D points...
        point_cloud_data[i] = {'vertices': pts3d, 'colors': colors}

@bpy.app.handlers.persistent
def update_pointcloud_on_frame_change(scene):
    """Update point cloud when frame changes"""
    current_frame = scene.frame_current - 1  # 0-indexed
    
    if current_frame in point_cloud_data:
        # Get or create point cloud object
        obj = bpy.data.objects.get("AnimatedPointCloud")
        if obj is None:
            mesh = bpy.data.meshes.new("AnimatedPointCloud")
            obj = bpy.data.objects.new("AnimatedPointCloud", mesh)
            bpy.context.scene.collection.objects.link(obj)
        
        # Update mesh data
        data = point_cloud_data[current_frame]
        mesh = obj.data
        mesh.clear_geometry()
        mesh.from_pydata(data['vertices'], [], [])

# Register handler
bpy.app.handlers.frame_change_pre.append(update_pointcloud_on_frame_change)
```

### Approach 3: Using OpenGL Point Cloud Handler (Recommended for Large Point Clouds)

The codebase already has OpenGL point cloud rendering (`user/utils/photogrammetry_importer/opengl/draw_manager.py`). You can extend it to update per frame:

```python
from photogrammetry_importer.opengl.draw_manager import DrawManager

def create_animated_opengl_pointcloud(output_dir, num_frames):
    """
    Create animated OpenGL point cloud that updates per frame.
    """
    draw_manager = DrawManager.get_singleton()
    
    # Load all frame data
    frame_data = []
    for i in range(num_frames):
        depth = np.load(f'{output_dir}/frame_{i:04d}.npy')
        rgb = load_image(f'{output_dir}/frame_{i:04d}.png')
        # Convert to points...
        frame_data.append({'coords': pts3d, 'colors': colors})
    
    # Create empty object as anchor
    anchor = bpy.data.objects.new("PointCloudAnchor", None)
    bpy.context.scene.collection.objects.link(anchor)
    
    # Store frame data in anchor custom properties
    anchor["frame_data"] = frame_data
    
    # Register draw callback that reads current frame
    def draw_callback(context):
        current_frame = context.scene.frame_current - 1
        if 0 <= current_frame < len(frame_data):
            data = frame_data[current_frame]
            # Update draw manager with current frame data
            draw_manager.register_points_draw_callback(
                anchor, data['coords'], data['colors'], point_size=2
            )
    
    # Register handler
    bpy.types.SpaceView3D.draw_handler_add(
        draw_callback, (), 'WINDOW', 'POST_VIEW'
    )
```

## Key Files Reference

1. **Point Cloud Export**: `dust3r/utils/viz_demo.py` - `convert_scene_output_to_glb()`
2. **Per-Frame Data Saving**: `dust3r/cloud_opt/base_opt.py` - `save_depth_maps()`, `save_rgb_imgs()`
3. **Camera Animation**: `user/utils/blender_import_cameras_from_glb.py`
4. **OpenGL Point Cloud**: `user/utils/photogrammetry_importer/opengl/draw_manager.py`

## Implementation Steps

1. **Modify GLB Export** to save per-frame point clouds instead of combined:
   ```python
   # In convert_scene_output_to_glb(), save each frame separately
   for i in range(len(imgs)):
       pts = pts3d[i][mask[i]]
       col = imgs[i][mask[i]]
       pct = trimesh.PointCloud(pts, colors=col)
       scene_i = trimesh.Scene()
       scene_i.add_geometry(pct)
       scene_i.export(f'{outdir}/pointcloud_frame_{i:04d}.ply')
   ```

2. **Create Blender Import Script** that:
   - Loads per-frame PLY files or reconstructs from depth maps
   - Creates separate objects with visibility keyframes
   - Sets up timeline animation

3. **Alternative**: Use the existing OpenGL point cloud system and add frame update logic

## Implementation: OpenGL Point Cloud Handler

A complete implementation is available in:
**`user/utils/blender_animated_opengl_pointcloud.py`**

### Features

- ✅ Loads per-frame depth maps (`frame_XXXX.npy`) and RGB images (`frame_XXXX.png`)
- ✅ Converts depth maps to 3D point clouds using camera poses and intrinsics
- ✅ Uses OpenGL for efficient rendering of large point clouds
- ✅ Automatically updates point cloud when timeline frame changes
- ✅ Supports dynamic mask filtering (optional)
- ✅ Works with or without photogrammetry_importer addon

### Usage

1. **Set Configuration** (at top of script):
   ```python
   MONST3R_OUTPUT_DIR = "/path/to/monst3r/output"  # e.g., "./demo_tmp/lady-running"
   POINT_SIZE = 2  # Size of points
   USE_DYNAMIC_MASK = False  # Enable to filter using dynamic_mask_*.png
   SUBSAMPLE_POINTS = 1  # Use every Nth point (for performance)
   MAX_POINTS_PER_FRAME = 100000  # Limit points per frame
   ```

2. **Run in Blender**:
   - Open Blender Scripting workspace
   - Open `blender_animated_opengl_pointcloud.py`
   - Run script (Alt+P or click Run)
   - Scrub timeline or press Space to see animated point cloud

### How It Works

1. **Data Loading**: Script loads all per-frame depth maps, RGB images, camera poses, and intrinsics
2. **Point Cloud Conversion**: Converts each depth map to 3D points using camera parameters
3. **OpenGL Handler**: Uses Blender's OpenGL system to render points efficiently
4. **Frame Updates**: Registers a frame change handler that updates point cloud data when timeline changes
5. **Rendering**: Point cloud is drawn in 3D viewport using GPU acceleration

### Key Components

- **AnimatedPointCloudManager**: Main class that manages data loading and updates
- **Frame Change Handler**: `@persistent` decorator ensures handler survives file reload
- **OpenGL Draw Handler**: Either uses `photogrammetry_importer`'s DrawManager or simplified version
- **Depth to Points Conversion**: Uses `depthmap_to_pts3d()` function similar to MonST3R's code

### Performance Tips

- Set `SUBSAMPLE_POINTS > 1` to reduce point count (e.g., `SUBSAMPLE_POINTS = 2` uses every 2nd point)
- Set `MAX_POINTS_PER_FRAME` to limit points per frame
- Use `USE_DYNAMIC_MASK = True` to filter out dynamic objects (reduces point count)
- The OpenGL handler is GPU-accelerated and handles large point clouds efficiently

## Notes

- The README mentions visualizing "per-frame pointcloud" with viser (`--no_mask` flag)
- Current GLB export combines all frames into one static point cloud
- Per-frame visualization requires separate point cloud objects or dynamic updates
- For large point clouds, OpenGL rendering (Approach 3) is most efficient
- **The implemented solution uses Approach 3 (OpenGL handler) for best performance**
