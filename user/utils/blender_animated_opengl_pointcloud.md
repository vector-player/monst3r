# Animated OpenGL Point Cloud in Blender

This script creates an animated point cloud visualization in Blender that updates automatically as you scrub through the timeline.

## Quick Start

1. **Run MonST3R** to generate output (depth maps, poses, etc.)

2. **Open Blender** and go to Scripting workspace

3. **Edit the script** (`blender_animated_opengl_pointcloud.py`):
   ```python
   MONST3R_OUTPUT_DIR = "/path/to/your/monst3r/output"
   # e.g., "/root/monst3r/demo_tmp/lady-running"
   ```

4. **Run the script** (Alt+P or click Run button)

5. **Scrub timeline** or press Space to see the point cloud animate!

## Configuration Options

```python
# Point cloud settings
POINT_SIZE = 2              # Size of points in pixels
USE_DYNAMIC_MASK = False   # Filter using dynamic_mask_*.png files
MASK_THRESHOLD = 0.5       # Threshold for dynamic mask (0-1)
SUBSAMPLE_POINTS = 1       # Use every Nth point (1=all, 2=every other, etc.)
MAX_POINTS_PER_FRAME = 100000  # Limit points for performance
```

## Requirements

### Required Files in MonST3R Output Directory:
- `frame_XXXX.npy` - Depth maps (one per frame)
- `frame_XXXX.png` - RGB images (one per frame)
- `pred_traj.txt` - Camera poses (TUM format)
- `pred_intrinsics.txt` - Camera intrinsics (optional, uses defaults if missing)

### Optional Files:
- `dynamic_mask_X.png` - Dynamic masks (if `USE_DYNAMIC_MASK = True`)

## How It Works

1. **Loads all frame data** at startup (depth maps, RGB images, poses)
2. **Converts depth maps to 3D points** using camera poses and intrinsics
3. **Registers OpenGL draw handler** for efficient GPU rendering
4. **Updates point cloud** automatically when timeline frame changes
5. **Renders in 3D viewport** using Blender's OpenGL system

## Performance Tips

- **Reduce point count**: Set `SUBSAMPLE_POINTS = 2` or higher
- **Limit points**: Reduce `MAX_POINTS_PER_FRAME` if playback is slow
- **Use dynamic masks**: Set `USE_DYNAMIC_MASK = True` to filter dynamic objects
- **Close other applications**: Free up GPU memory for better performance

## Troubleshooting

### "No depth map files found"
- Check that `MONST3R_OUTPUT_DIR` is set correctly
- Ensure `frame_*.npy` files exist in the directory

### "Could not detect MonST3R output directory"
- Set `MONST3R_OUTPUT_DIR` explicitly in the script
- Or save your .blend file in the same directory as MonST3R output

### Point cloud not updating
- Check that timeline frame range is set correctly (should be 1 to num_frames)
- Try scrubbing timeline manually
- Check Blender console for errors

### Performance issues
- Reduce `MAX_POINTS_PER_FRAME`
- Increase `SUBSAMPLE_POINTS`
- Disable dynamic mask if enabled

## Example Output

After running the script, you should see:
- A collection named `AnimatedPointCloud` in the outliner
- An empty object `PointCloudAnchor` in that collection
- Point cloud visible in 3D viewport
- Point cloud updates when you change timeline frame

## Integration with Camera Animation

This script works well with `blender_import_cameras_from_glb.py`:
1. First import cameras using `blender_import_cameras_from_glb.py`
2. Then run this script to add animated point cloud
3. Both will animate together as you scrub timeline

## Technical Details

- Uses Blender's `gpu` module for OpenGL rendering
- Falls back to simplified handler if `photogrammetry_importer` addon not available
- Frame change handler uses `@persistent` decorator to survive file reload
- Point cloud data is stored per-frame and updated on demand
- Efficient GPU batch rendering for large point clouds
