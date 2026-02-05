# Blender Curve Path Animation with Rotation

## Overview

`blender_curve_pos_rot.py` is a Blender script that creates an animated camera trajectory visualization using a curve-based approach. Unlike traditional keyframe animation, this script uses Blender's **Follow Path** constraint to create smooth, editable path animations with synchronized quaternion rotations.

### Key Features

- **Curve-based Path**: Creates a NURBS curve from trajectory positions for smooth, editable paths
- **Follow Path Constraint**: Uses Blender's constraint system for natural path following
- **Synchronized Rotations**: Quaternion rotations are keyframed and move in sync with the curve
- **TUM Format Support**: Reads standard TUM trajectory format (timestamp tx ty tz qx qy qz qw)
- **Automatic Setup**: Creates all necessary objects, constraints, and keyframes automatically

## Requirements

- **Blender 2.8+** (tested with Blender 3.0+)
- **Python 3.x** (included with Blender)
- **Trajectory file** in TUM format

## Installation

No installation required! Simply place `blender_curve_pos_rot.py` in your Blender scripts directory or run it directly.

## Usage

### Method 1: Interactive Mode (Recommended for First-Time Users)

1. **Open Blender**
2. **Switch to Scripting workspace** (top menu bar)
3. **Open the script**: `File → Open → select blender_curve_pos_rot.py`
4. **Modify the trajectory file path** (optional):
   ```python
   TRAJECTORY_FILE = r"path/to/your/pred_traj.txt"
   ```
5. **Run the script**: Press `Alt+P` or click the "Run Script" button
6. **View the animation**: Press `Space` to play or scrub the timeline

### Method 2: Command-Line Mode

```bash
blender --background --python blender_curve_pos_rot.py -- pred_traj.txt
```

Or with a full path:

```bash
blender --background --python blender_curve_pos_rot.py -- /path/to/pred_traj.txt
```

**Note**: The `--` separator tells Blender where script arguments end and your arguments begin.

### Method 3: Command-Line with Output File

```bash
blender --background --python blender_curve_pos_rot.py -- pred_traj.txt -o //render_ -a
```

This will render the animation automatically.

## Trajectory File Format

The script expects trajectory files in **TUM format**:

```
timestamp tx ty tz qx qy qz qw
```

Where:
- `timestamp`: Time in seconds (used for frame mapping)
- `tx ty tz`: Camera position (translation) in 3D space
- `qx qy qz qw`: Camera orientation as quaternion (TUM format)

### Example Trajectory File

```
0.0 -0.108736 0.027248 -0.113183 0.902629 0.022985 0.410309 0.127983
1.0 -0.104799 0.026974 -0.110957 0.906046 0.022251 0.402839 0.127698
2.0 -0.100792 0.026711 -0.108961 0.910274 0.020927 0.393741 0.126218
...
```

### Format Notes

- **Whitespace-separated** values (spaces or tabs)
- **Comments** starting with `#` are ignored
- **Empty lines** are skipped
- **Quaternion format**: TUM uses (qx, qy, qz, qw), converted to Blender's (w, x, y, z) internally

## Configuration Options

You can customize the script behavior by modifying these constants at the top of the file:

```python
# Trajectory file path
TRAJECTORY_FILE = r"path/to/pred_traj.txt"

# Object names
CURVE_OBJECT_NAME = "TrajectoryCurve"
EMPTY_OBJECT_NAME = "CurveFollower"

# Empty object appearance
EMPTY_DISPLAY_TYPE = 'ARROWS'  # Options: 'PLAIN_AXES', 'ARROWS', 'SINGLE_ARROW', 
                                #          'CIRCLE', 'CUBE', 'SPHERE', 'CONE'
EMPTY_SIZE = 0.1  # Display size of empty object

# Curve quality
CURVE_RESOLUTION = 64  # Points per segment (higher = smoother but slower)
```

## How It Works

### 1. Curve Creation

The script creates a **NURBS curve** with control points at each trajectory position:

```
Position 1 ── Position 2 ── Position 3 ── ... ── Position N
```

The curve uses `use_endpoint_u = True` to ensure it passes exactly through all control points.

### 2. Follow Path Constraint

A **Follow Path** constraint is added to the empty object:

- **Target**: The trajectory curve
- **Offset Factor**: Animated from 0.0 (start) to 1.0 (end)
- **Follow Curve**: Enabled for natural path following
- **Axes**: Configurable based on coordinate system

### 3. Rotation Synchronization

Quaternion rotations are keyframed on the empty object at the same frames as the path offset:

```
Frame 1: offset_factor=0.0, rotation_quaternion=(w1, x1, y1, z1)
Frame 2: offset_factor=0.1, rotation_quaternion=(w2, x2, y2, z2)
Frame 3: offset_factor=0.2, rotation_quaternion=(w3, x3, y3, z3)
...
```

### 4. Frame Mapping

Timestamps are converted to frame numbers:
- `frame = int(timestamp) + 1` (Blender frames start at 1)
- Offset factors are normalized: `(timestamp - min_timestamp) / duration`

## Use Cases

### 1. Camera Trajectory Visualization

Visualize reconstructed camera paths from SLAM, SfM, or MonST3R:

```bash
blender --background --python blender_curve_pos_rot.py -- pred_traj.txt
```

**Benefits**:
- Smooth, editable path
- Easy to adjust timing
- Can attach actual camera objects to the empty

### 2. Animation Preview

Preview camera movements before rendering:

1. Run the script to create the animation
2. Attach a camera object to the empty (parent or constraint)
3. Preview the camera movement
4. Adjust curve or timing as needed

### 3. Path Editing

Edit the trajectory path visually:

1. Run script to create curve
2. Enter **Edit Mode** on the curve object
3. Move control points to adjust path
4. Rotations automatically adjust (if using Follow Curve)

### 4. Multi-Camera Scenarios

Create multiple trajectories:

1. Run script for first trajectory
2. Rename objects (or modify script)
3. Run again for second trajectory
4. Compare or composite multiple paths

### 5. Export for Other Software

Use Blender as an intermediate step:

1. Create animation in Blender
2. Export to FBX/ABC/Alembic
3. Import into other 3D software
4. Maintain path and rotation data

## Coordinate System Considerations

### MonST3R / OpenCV Convention

MonST3R uses **OpenCV coordinate system**:
- **+X**: Right
- **+Y**: Down  
- **+Z**: Forward (into scene)

### Blender Convention

Blender uses:
- **+X**: Right
- **+Y**: Forward
- **+Z**: Up

### Adjusting Axes

If the camera orientation looks incorrect, modify the constraint axes in the script:

```python
constraint.forward_axis = 'FORWARD_X'  # Try: FORWARD_X, FORWARD_Y, FORWARD_Z, FORWARD_NEG_X, etc.
constraint.up_axis = 'UP_Z'            # Try: UP_X, UP_Y, UP_Z, UP_NEG_X, etc.
```

Common combinations:
- **OpenCV → Blender**: `FORWARD_Z`, `UP_NEG_Y`
- **Standard**: `FORWARD_X`, `UP_Z`

## Troubleshooting

### Problem: "Trajectory file not found"

**Solution**: 
- Check the file path is correct
- Use absolute paths: `r"C:\full\path\to\file.txt"`
- On Linux/Mac: `"/home/user/path/to/file.txt"`

### Problem: Camera orientation is wrong

**Solution**:
- Adjust `forward_axis` and `up_axis` in the constraint
- Check coordinate system conversion
- Try different axis combinations

### Problem: Animation is too fast/slow

**Solution**:
- Timestamps determine frame numbers: `frame = int(timestamp) + 1`
- If timestamps are 0, 1, 2, 3... frames will be 1, 2, 3, 4...
- Scale timestamps or adjust frame rate in Blender

### Problem: Curve doesn't look smooth

**Solution**:
- Increase `CURVE_RESOLUTION` (e.g., 128 or 256)
- Use more trajectory points
- Switch to Bezier curve (modify script)

### Problem: Empty object doesn't follow curve

**Solution**:
- Check constraint is enabled (Properties → Constraints)
- Verify `offset_factor` is keyframed (check Graph Editor)
- Ensure curve is valid (no zero-length segments)

### Problem: Rotations are jittery

**Solution**:
- Check quaternion normalization in source data
- Increase frame rate or add more trajectory points
- Use Blender's interpolation modes (Graph Editor)

## Tips and Best Practices

### 1. Pre-processing Trajectory Data

- **Normalize timestamps** if they're not sequential
- **Remove duplicate points** to avoid curve artifacts
- **Validate quaternions** (should be normalized: ||q|| = 1)

### 2. Performance Optimization

- **Reduce curve resolution** for long trajectories
- **Use fewer keyframes** for preview (sample trajectory)
- **Disable viewport display** of curve for faster playback

### 3. Workflow Integration

```python
# Example: Batch process multiple trajectories
trajectories = ["traj1.txt", "traj2.txt", "traj3.txt"]
for traj in trajectories:
    # Modify TRAJECTORY_FILE or use command-line
    # Run script
    pass
```

### 4. Advanced Usage

**Attach a Camera Object**:

```python
# After running the script, in Blender:
# 1. Create a camera: Add → Camera
# 2. Parent camera to empty: Select camera → Select empty → Ctrl+P → Keep Transform
# 3. Camera will follow the path with rotations
```

**Export Animation**:

```python
# In Blender:
# 1. Select empty object
# 2. File → Export → FBX
# 3. Check "Selected Objects" and "Animation"
```

### 5. Comparison with Other Scripts

| Feature | `blender_animate_positions.py` | `blender_animate_pos_rot.py` | `blender_curve_pos_rot.py` |
|---------|-------------------------------|------------------------------|----------------------------|
| Path Type | Keyframes | Keyframes | Curve |
| Editable Path | ❌ | ❌ | ✅ |
| Smooth Interpolation | Limited | Limited | Excellent |
| Rotation Support | ❌ | ✅ | ✅ |
| Constraint-based | ❌ | ❌ | ✅ |
| Use Case | Simple animation | Standard animation | Advanced editing |

## Example Workflow

### Complete Example: Lady-Running Demo

```bash
# 1. Navigate to MonST3R directory
cd /path/to/monst3r

# 2. Run script with trajectory file
blender --background --python user/utils/blender_curve_pos_rot.py -- \
    demo_tmp/lady-running/pred_traj.txt

# 3. Open resulting .blend file (if saved) or view in Blender
blender output.blend

# 4. Play animation (Space key)
# 5. Adjust curve if needed (Edit Mode on curve object)
# 6. Export or render as needed
```

## Output

After running the script, you'll have:

1. **TrajectoryCurve**: NURBS curve object following the path
2. **CurveFollower**: Empty object with Follow Path constraint
3. **Animation**: Keyframed path offset and rotations
4. **Frame Range**: Set to match trajectory duration

## Related Scripts

- `blender_animate_positions.py`: Simple position keyframe animation
- `blender_animate_pos_rot.py`: Position + rotation keyframe animation
- `viser_4d_visualization.py`: Interactive web-based 4D visualization

## License

This script is part of the MonST3R project. Refer to the main project license.

## Support

For issues or questions:
1. Check this documentation
2. Review the script comments
3. Check MonST3R project documentation
4. Review Blender's Follow Path constraint documentation

## Changelog

### Version 1.0
- Initial release
- Curve-based path animation
- Follow Path constraint integration
- Quaternion rotation support
- TUM format trajectory parsing
