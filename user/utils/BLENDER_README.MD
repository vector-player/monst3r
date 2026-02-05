# Blender Utilities for MonST3R - Complete Guide

This document provides a comprehensive overview of all Blender-related utilities in the `user/utils/` directory, explaining their purposes, theoretical foundations, scope of application, and when/how to use them.

## Table of Contents

1. [Overview](#overview)
2. [Core Import Scripts](#core-import-scripts)
3. [Debugging and Analysis Tools](#debugging-and-analysis-tools)
4. [Visualization Tools](#visualization-tools)
5. [Format Conversion Tools](#format-conversion-tools)
6. [Workflow Recommendations](#workflow-recommendations)
7. [Theoretical Foundations](#theoretical-foundations)

---

## Overview

MonST3R generates 3D reconstructions with camera poses, depth maps, and 3D geometry. These Blender utilities provide multiple approaches for importing, visualizing, and analyzing MonST3R results in Blender, each optimized for different use cases.

### Key Concepts

- **GLB Export Process**: MonST3R exports results as GLB files containing camera geometry (cones) and 3D scene geometry
- **Coordinate System Transformations**: Converting between MonST3R's coordinate system (Computer Vision convention) and Blender's coordinate system (OpenGL convention)
- **Camera Representation**: Two approaches - geometry-based (cones from GLB) and object-based (Blender camera objects)

---

## Core Import Scripts

### 1. `blender_import_monst3r.py`

**Purpose**: Basic import script for MonST3R results - imports GLB scene and creates camera objects from trajectory file.

**Scope of Application**:
- Quick visualization of MonST3R results
- Simple camera trajectory import
- Basic scene setup with lighting

**Theoretical Foundation**:
- Direct GLB import using Blender's built-in glTF importer
- TUM trajectory parsing (timestamp, position, quaternion)
- Simple quaternion-to-Euler conversion for camera rotation
- No coordinate system transformation (assumes basic compatibility)

**When to Use**:
- ✅ Quick visualization without precise camera alignment
- ✅ Simple scene setup
- ✅ When camera positions don't need to match GLB geometry exactly
- ❌ Not suitable when cameras must match GLB geometry precisely

**How to Use**:
```python
# Configure at top of script:
MONST3R_ROOT_PATH = "/path/to/monst3r"  # or None for auto-detection
SEQUENCE_NAME = "lady-running"
IMPORT_SCENE = True
IMPORT_CAMERAS = True
CREATE_ANIMATION = False  # Set True for animated camera sequence
SAMPLE_CAMERAS = 10  # Import every Nth camera

# Run in Blender Scripting workspace
```

**Limitations**:
- Does not account for GLB export transformations
- Camera positions may not match GLB geometry exactly
- No validation against GLB geometry

---

### 2. `blender_import_cameras_from_glb.py` ⭐ **RECOMMENDED**

**Purpose**: Advanced camera import script that creates Blender camera objects matching GLB geometry exactly.

**Scope of Application**:
- Precise camera import matching GLB geometry
- Camera animation creation
- Production-ready camera setup
- Validation against GLB geometry

**Theoretical Foundation**:
- **GLB Export Process Understanding**: Matches the exact transformation pipeline used in MonST3R's GLB export:
  1. Build camera-to-world (`c2w`) from TUM pose
  2. Apply `OPENGL` transform (inverts Y and Z axes)
  3. Apply `aspect_ratio` transform (scales X by W/H)
  4. Apply `rot45` transform (45° rotation + translation)
  5. Apply scene normalization transform
  
- **Coordinate System Conversion**:
  - TUM format: `qx qy qz qw` → Blender format: `w x y z`
  - Computer Vision convention (+Z forward, +Y down) → OpenGL convention (+Z up, +Y forward)
  
- **Scene Normalization**: Uses first camera as reference to normalize scene coordinates

**When to Use**:
- ✅ **Primary choice** for importing cameras
- ✅ When cameras must match GLB geometry exactly
- ✅ Production workflows requiring precise camera alignment
- ✅ Camera animation creation
- ✅ When validation is needed

**How to Use**:
```python
# Configure at top of script:
MONST3R_OUTPUT_DIR = "/path/to/monst3r/demo_tmp/lady-running"  # or None for auto-detection
CREATE_ANIMATION = True  # Create keyframe animation
CAMERA_SCALE = 1.0
CAMERA_COLLECTION_NAME = "MonST3R_Cameras"
SCREEN_WIDTH = 0.03  # Must match GLB export

# Run in Blender Scripting workspace
# Script automatically validates cameras against GLB geometry
```

**Features**:
- Automatic validation against GLB geometry
- Step-by-step transform computation matching GLB export
- Supports camera intrinsics for accurate frustum representation
- Creates organized camera collection
- Optional keyframe animation

**Output**:
- Camera objects in `MonST3R_Cameras` collection
- Validation report comparing cameras with GLB geometry
- Pass/fail indicators (✓/✗) for position and rotation differences

---

### 3. `blender_extract_cameras_from_glb_geometry.py`

**Purpose**: Extract camera objects directly from GLB geometry (camera cones) without using trajectory files.

**Scope of Application**:
- When trajectory files are missing or corrupted
- Reverse engineering camera poses from GLB geometry
- Validating GLB geometry structure
- Alternative import method

**Theoretical Foundation**:
- **Geometry Analysis**: Identifies camera cones by:
  - Small mesh size (< 50 vertices)
  - Cone-like structure (tip vertex with many edges)
  - Geometric analysis of cone shape
  
- **Camera Extraction**:
  - Tip vertex = camera optical center
  - Base center = image plane center
  - Look direction = from tip to base center
  - Rotation matrix from look direction

**When to Use**:
- ✅ When `pred_traj.txt` is unavailable
- ✅ Validating GLB geometry structure
- ✅ Reverse engineering camera poses
- ✅ Alternative import method
- ❌ Less precise than trajectory-based import
- ❌ May have ordering issues if geometry names are unclear

**How to Use**:
```python
# Configure at top of script:
CREATE_ANIMATION = True
CAMERA_COLLECTION_NAME = "Extracted_Cameras"
CONE_VERTEX_COUNT_THRESHOLD = 20
SORT_BY_POSITION = True  # Sort by trajectory position (more reliable)

# Run in Blender Scripting workspace
# Requires GLB file to be imported first
```

**Limitations**:
- Depends on GLB geometry structure
- Camera ordering may be ambiguous
- Less precise than trajectory-based methods
- No intrinsics information

---

## Debugging and Analysis Tools

### 4. `blender_extract_glb_camera_transforms.py`

**Purpose**: Extract ground truth camera transforms from imported GLB geometry for debugging.

**Scope of Application**:
- Debugging camera transformation issues
- Creating ground truth reference data
- Validating GLB import correctness
- Comparison baseline generation

**Theoretical Foundation**:
- Extracts `matrix_world` transforms directly from Blender objects
- Represents ground truth camera positions/orientations as they appear in Blender
- Saves transforms in JSON format for comparison

**When to Use**:
- ✅ Debugging camera transformation errors
- ✅ Creating comparison baselines
- ✅ Validating GLB import
- ✅ Step 1 of debugging workflow

**How to Use**:
```python
# No configuration needed
# Run in Blender Scripting workspace after importing GLB file
# Output: glb_camera_transforms.json
```

**Output Format**:
```json
{
  "num_cameras": 50,
  "transforms": [
    {
      "index": 0,
      "name": "Camera_0000",
      "position": [x, y, z],
      "rotation_quaternion": [w, x, y, z],
      "rotation_euler": [x, y, z],
      "matrix_world": [[4x4 matrix]],
      "matrix_world_3x3": [[3x3 rotation matrix]]
    }
  ]
}
```

---

### 5. `blender_compute_expected_transforms.py`

**Purpose**: Compute expected camera transforms step-by-step matching GLB export process.

**Scope of Application**:
- Debugging transformation pipeline
- Understanding GLB export process
- Step-by-step transform computation
- Comparison with ground truth

**Theoretical Foundation**:
- **Step-by-Step Transform Pipeline**:
  1. `step1_c2w`: Build camera-to-world from TUM pose
  2. `step2_c2w_opengl`: Apply OPENGL transform
  3. `step3_c2w_opengl_aspect`: Apply aspect ratio scaling
  4. `step4_geometry_transform`: Apply rot45 transform
  5. `step5_final_transform`: Apply scene normalization
  
- **Matrix Mathematics**:
  - Quaternion to rotation matrix conversion
  - Matrix multiplication order matters
  - Scene normalization using first camera

**When to Use**:
- ✅ Debugging transformation errors
- ✅ Understanding GLB export process
- ✅ Step 2 of debugging workflow
- ✅ Identifying which transformation step introduces errors

**How to Use**:
```python
# Configure at top of script:
MONST3R_OUTPUT_DIR = "/path/to/monst3r/output"  # or None for auto-detection
SCREEN_WIDTH = 0.03  # Must match GLB export

# Run in Blender Scripting workspace
# Output: computed_transforms.json
```

**Output Format**:
```json
{
  "num_cameras": 50,
  "transforms": [
    {
      "index": 0,
      "step1_c2w": [[4x4 matrix]],
      "step2_c2w_opengl": [[4x4 matrix]],
      "step3_c2w_opengl_aspect": [[4x4 matrix]],
      "step4_geometry_transform": [[4x4 matrix]],
      "step5_final_transform": [[4x4 matrix]],
      "position": [x, y, z],
      "rotation_quaternion": [w, x, y, z],
      "matrix_world": [[4x4 matrix]]
    }
  ]
}
```

---

### 6. `blender_compare_transforms.py`

**Purpose**: Systematically compare ground truth transforms with computed transforms to identify errors.

**Scope of Application**:
- Debugging camera transformation issues
- Identifying systematic errors
- Validating transformation pipeline
- Error pattern analysis

**Theoretical Foundation**:
- **Comparison Metrics**:
  - Position difference: Euclidean distance
  - Rotation difference: Quaternion distance (accounts for q = -q equivalence)
  - Matrix difference: Element-wise comparison
  
- **Error Analysis**:
  - Identifies problematic cameras
  - Detects systematic errors
  - Provides detailed per-camera comparison

**When to Use**:
- ✅ Step 3 of debugging workflow
- ✅ After extracting ground truth and computing expected transforms
- ✅ Identifying transformation errors
- ✅ Validating fixes

**How to Use**:
```python
# Requires:
# - glb_camera_transforms.json (from script #4)
# - computed_transforms.json (from script #5)

# Run in Blender Scripting workspace
# Output: transform_comparison_report.txt
```

**Output**:
- Detailed comparison report
- Summary statistics (average, max, min differences)
- List of problematic cameras
- Error pattern analysis

---

### 7. `blender_analyze_camera_differences.py`

**Purpose**: Quick analysis tool comparing camera geometry with camera objects in Blender scene.

**Scope of Application**:
- Quick validation after camera import
- Visual comparison of geometry vs objects
- Matrix difference analysis
- Transformation debugging

**Theoretical Foundation**:
- Direct comparison of Blender object transforms
- Matrix difference computation
- Position and rotation difference metrics

**When to Use**:
- ✅ Quick validation after importing cameras
- ✅ Visual debugging in Blender
- ✅ Understanding transformation differences
- ❌ Less detailed than systematic comparison tools

**How to Use**:
```python
# Configure at top of script:
CAMERA_GEOMETRY_COLLECTION = None  # None = search all objects
CAMERA_OBJECTS_COLLECTION = "MonST3R_Cameras"

# Run in Blender Scripting workspace
# Requires both GLB geometry and camera objects to exist
```

---

### 8. `blender_analyze_camera_mismatch.py`

**Purpose**: Simplified analysis tool for comparing camera geometry with camera objects.

**Scope of Application**:
- Quick validation
- Simple comparison
- Basic debugging

**Theoretical Foundation**:
- Similar to `blender_analyze_camera_differences.py` but simplified
- Focuses on first few cameras
- Provides summary statistics

**When to Use**:
- ✅ Quick validation
- ✅ Simple comparison needs
- ❌ Less comprehensive than other analysis tools

**How to Use**:
```python
# No configuration needed
# Run in Blender Scripting workspace
# Requires both GLB geometry and camera objects
```

---

## Visualization Tools

### 9. `blender_animated_opengl_pointcloud.py` ⭐ **VISUALIZATION**

**Purpose**: Create animated point cloud visualization that updates per frame based on MonST3R depth maps.

**Scope of Application**:
- Dynamic 3D visualization
- Per-frame point cloud rendering
- Large point cloud visualization
- Real-time animation

**Theoretical Foundation**:
- **Depth-to-Point Conversion**:
  - Uses camera intrinsics to convert depth maps to 3D points
  - Applies camera-to-world transformation
  - Filters valid points (non-zero depth)
  
- **OpenGL Rendering**:
  - GPU-accelerated point rendering
  - Efficient batch rendering for large point clouds
  - Frame change handlers for automatic updates
  
- **Dynamic Masking**:
  - Optional filtering using dynamic masks
  - Per-frame point cloud updates

**When to Use**:
- ✅ Visualizing dynamic scenes
- ✅ Per-frame point cloud animation
- ✅ Large point cloud rendering
- ✅ Real-time visualization
- ✅ Combined with camera animation

**How to Use**:
```python
# Configure at top of script:
MONST3R_OUTPUT_DIR = "/path/to/monst3r/output"  # or None for auto-detection
POINT_SIZE = 2
USE_DYNAMIC_MASK = False
MASK_THRESHOLD = 0.5
SUBSAMPLE_POINTS = 1  # Use every Nth point
MAX_POINTS_PER_FRAME = 100000

# Run in Blender Scripting workspace
# Scrub timeline or press Space to see animation
```

**Requirements**:
- `frame_XXXX.npy` - Depth maps
- `frame_XXXX.png` - RGB images
- `pred_traj.txt` - Camera poses
- `pred_intrinsics.txt` - Camera intrinsics (optional)

**Features**:
- Automatic frame change handling
- GPU-accelerated rendering
- Optional dynamic mask filtering
- Point subsampling for performance
- Works with photogrammetry_importer addon or standalone

---

## Format Conversion Tools

### 10. `convert_to_colmap.py`

**Purpose**: Convert MonST3R output to COLMAP format for use with Blender's photogrammetry_importer addon.

**Scope of Application**:
- COLMAP format conversion
- Photogrammetry workflow integration
- Camera animation in Blender
- Standard format export

**Theoretical Foundation**:
- **COLMAP Format**:
  - `cameras.txt`: Camera intrinsics (PINHOLE model)
  - `images.txt`: Camera poses and image metadata (two lines per image)
  - `points3D.txt`: 3D point cloud
  
- **Coordinate System Conversion**:
  - TUM format → COLMAP format
  - Quaternion conversion
  - Camera orientation fixes to match GLB export

**When to Use**:
- ✅ Using Blender's photogrammetry_importer addon
- ✅ COLMAP workflow integration
- ✅ Standard format export
- ✅ Camera animation in Blender addon

**How to Use**:
```bash
# Basic conversion
python convert_to_colmap.py --input demo_tmp/lady-running --output colmap_output

# With image copying (recommended for Blender)
python convert_to_colmap.py --input demo_tmp/lady-running --output colmap_output --copy-images

# With depth maps
python convert_to_colmap.py --input demo_tmp/lady-running --output colmap_output --copy-images --copy-depth-maps
```

**Output Structure**:
```
colmap_output/
├── cameras.txt          # Camera intrinsics (PINHOLE)
├── images.txt           # Camera poses and image metadata
├── points3D.txt         # 3D point cloud
└── images/              # (if --copy-images used)
    ├── image_0001.png
    ├── image_0002.png
    └── ...
```

**Features**:
- Automatic image name validation (must contain digits)
- COLMAP format compliance
- Camera orientation fixes
- Depth map support
- RGB image matching

---

## Workflow Recommendations

### Standard Import Workflow

**For most users** - Quick and reliable:

```
1. Import GLB file into Blender
   File → Import → glTF 2.0 → select scene.glb

2. Run blender_import_cameras_from_glb.py
   → Creates camera objects matching GLB geometry
   → Validates automatically
   → Shows pass/fail status

3. (Optional) Run blender_animated_opengl_pointcloud.py
   → Adds animated point cloud visualization
   → Updates per frame
```

### Debugging Workflow

**When cameras don't match GLB geometry**:

```
1. Import GLB file into Blender

2. Run blender_extract_glb_camera_transforms.py
   → Creates glb_camera_transforms.json (ground truth)

3. Run blender_compute_expected_transforms.py
   → Creates computed_transforms.json (expected)

4. Run blender_compare_transforms.py
   → Creates transform_comparison_report.txt
   → Identifies problematic cameras and error patterns

5. Analyze report to identify root cause

6. Fix blender_import_cameras_from_glb.py if needed

7. Re-run blender_import_cameras_from_glb.py
   → Validates automatically
```

### COLMAP Workflow

**For photogrammetry_importer addon users**:

```
1. Run convert_to_colmap.py
   python convert_to_colmap.py --input demo_tmp/lady-running --output colmap_output --copy-images

2. In Blender, install photogrammetry_importer addon

3. Import COLMAP model
   Add-ons → Import → COLMAP → Select colmap_output directory

4. Camera animation will be automatically created
```

### Visualization Workflow

**For dynamic visualization**:

```
1. Import GLB file and cameras (standard workflow)

2. Run blender_animated_opengl_pointcloud.py
   → Creates animated point cloud

3. Scrub timeline or press Space
   → Point cloud updates per frame
   → Cameras animate together
```

---

## Theoretical Foundations

### Coordinate System Transformations

MonST3R uses **Computer Vision (CV) convention**:
- +Z forward (into scene)
- +Y down
- +X right

Blender uses **OpenGL convention**:
- +Z up
- +Y forward
- +X right

**OPENGL Transform Matrix**:
```
OPENGL = [[1,  0,  0, 0],
          [0, -1,  0, 0],
          [0,  0, -1, 0],
          [0,  0,  0, 1]]
```

This matrix inverts Y and Z axes to convert from CV to OpenGL convention.

### GLB Export Process

The GLB export process applies transformations in this order:

1. **Camera-to-World (`c2w`)**: From TUM pose (position + quaternion)
2. **OPENGL Transform**: Coordinate system conversion
3. **Aspect Ratio**: Scales X axis by W/H (for frustum aspect ratio)
4. **Rot45**: 45° rotation around Z + translation `-height` along Z
   - `height = max(screen_width/10, focal * screen_width / H)`
5. **Scene Normalization**: `inv(first_c2w_opengl @ rot_y180)`
   - Normalizes scene relative to first camera

**Final Transform**:
```
T_final = inv(cams2world[0] @ OPENGL @ rot_y180) @ (c2w @ OPENGL @ aspect_ratio @ rot45)
```

### Quaternion Formats

**TUM Format**: `qx qy qz qw` (scalar last)
**Blender Format**: `w x y z` (scalar first)

**Conversion**:
```python
# TUM to Blender
quat_blender = Quaternion([quat_tum[3], quat_tum[0], quat_tum[1], quat_tum[2]])
```

### Camera Geometry Representation

Camera cones in GLB represent:
- **Tip vertex**: Camera optical center
- **Base vertices**: Image plane corners
- **Cone orientation**: Camera viewing direction

### Depth-to-Point Conversion

Converting depth maps to 3D points:

```
X_cam = (x - cx) * depth / fx
Y_cam = (y - cy) * depth / fy
Z_cam = depth

pts3d_cam = [X_cam, Y_cam, Z_cam]
pts3d_world = cam2world @ pts3d_cam
```

Where:
- `(x, y)`: Pixel coordinates
- `(cx, cy)`: Principal point
- `(fx, fy)`: Focal lengths
- `depth`: Depth value at pixel

---

## Summary Table

| Script | Purpose | Use Case | Precision | Complexity |
|--------|---------|----------|-----------|------------|
| `blender_import_monst3r.py` | Basic import | Quick visualization | Low | Low |
| `blender_import_cameras_from_glb.py` | ⭐ Precise camera import | Production workflows | High | Medium |
| `blender_extract_cameras_from_glb_geometry.py` | Extract from geometry | Missing trajectory files | Medium | Medium |
| `blender_extract_glb_camera_transforms.py` | Extract ground truth | Debugging | High | Low |
| `blender_compute_expected_transforms.py` | Compute expected transforms | Debugging | High | High |
| `blender_compare_transforms.py` | Compare transforms | Debugging | High | Medium |
| `blender_analyze_camera_differences.py` | Quick analysis | Validation | Medium | Low |
| `blender_analyze_camera_mismatch.py` | Simple analysis | Quick check | Medium | Low |
| `blender_animated_opengl_pointcloud.py` | ⭐ Animated visualization | Dynamic visualization | High | Medium |
| `convert_to_colmap.py` | COLMAP conversion | Addon integration | High | Medium |

---

## Quick Reference

### Most Common Use Cases

1. **Import cameras matching GLB geometry**: `blender_import_cameras_from_glb.py`
2. **Animated point cloud**: `blender_animated_opengl_pointcloud.py`
3. **COLMAP format**: `convert_to_colmap.py`
4. **Debugging cameras**: Use debugging workflow (scripts #4, #5, #6)

### File Requirements

**For camera import**:
- `pred_traj.txt` - Camera trajectory (TUM format)
- `pred_intrinsics.txt` - Camera intrinsics (optional)
- `scene.glb` - GLB file with geometry
- `rgb_imgs/` - RGB images (for image size detection)

**For animated point cloud**:
- `frame_XXXX.npy` - Depth maps
- `frame_XXXX.png` - RGB images
- `pred_traj.txt` - Camera poses
- `pred_intrinsics.txt` - Camera intrinsics (optional)

**For COLMAP conversion**:
- `pred_traj.txt` - Camera trajectory
- `pred_intrinsics.txt` - Camera intrinsics
- `scene.glb` or `frame_*.npy` - 3D points
- RGB images

---

## Additional Resources

- `BLENDER_ADDON_COMPATIBILITY.md` - COLMAP format compatibility details
- `fix_blender_import_camera_from_glb.md` - Detailed debugging guide
- `blender_animated_opengl_pointcloud.md` - Point cloud visualization guide
- `convert_to_colmap.md` - COLMAP conversion details

---

## Troubleshooting

### Common Issues

1. **Cameras don't match GLB geometry**
   - Use debugging workflow (scripts #4, #5, #6)
   - Check `SCREEN_WIDTH` matches GLB export
   - Verify image size detection

2. **Point cloud not updating**
   - Check timeline frame range
   - Verify frame data loaded correctly
   - Check Blender console for errors

3. **COLMAP import fails**
   - Ensure image names contain digits
   - Check `images.txt` format (two lines per image)
   - Verify camera model is PINHOLE

4. **Performance issues**
   - Reduce `MAX_POINTS_PER_FRAME`
   - Increase `SUBSAMPLE_POINTS`
   - Disable dynamic mask if enabled

---

*Last updated: Based on MonST3R utilities analysis*
