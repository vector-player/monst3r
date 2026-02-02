# Fix Blender Import Camera from GLB

## Problem Statement

The camera objects created by `blender_import_cameras_from_glb.py` were not matching the camera geometry imported from GLB files. Since the GLB import looks correct, the issue was in the matrix conversion logic used to transform camera poses from MonST3R's coordinate system to Blender's coordinate system.

## GLB Export Process

Understanding how MonST3R exports camera geometry to GLB is crucial for fixing the conversion:

1. **Individual camera geometry transform**: `pose_c2w @ OPENGL @ aspect_ratio @ rot45`
   - `pose_c2w`: Camera-to-world matrix from TUM trajectory
   - `OPENGL`: `[[1,0,0,0], [0,-1,0,0], [0,0,-1,0], [0,0,0,1]]` (inverts Y and Z)
   - `aspect_ratio`: `[[W/H,0,0,0], [0,1,0,0], [0,0,1,0], [0,0,0,1]]` (scales X by W/H)
   - `rot45`: 45° rotation around Z + translation `-height` along Z
   - `height = max(screen_width/10, focal * screen_width / H)`

2. **Scene normalization transform**: `inv(cams2world[0] @ OPENGL @ rot_y180)`
   - Applied to entire scene after all geometries are added
   - Normalizes scene relative to first camera

3. **Final camera geometry transform**: `inv(cams2world[0] @ OPENGL @ rot_y180) @ (pose_c2w @ OPENGL @ aspect_ratio @ rot45)`

## Debugging Strategy

A systematic approach was designed to identify and fix the matrix conversion issue:

### Phase 1: Extract Ground Truth from GLB Geometry
Extract the actual transforms from imported GLB geometry as ground truth.

### Phase 2: Compute Expected Transforms Step-by-Step
Compute transforms step-by-step matching the GLB export process.

### Phase 3: Systematic Comparison
Compare ground truth vs computed transforms to identify where errors occur.

### Phase 4: Fix Implementation
Update the conversion logic based on comparison findings.

### Phase 5: Validation
Verify that fixes produce correct results.

## Scripts Overview

The following scripts were created to implement this debugging strategy:

1. **`blender_extract_glb_camera_transforms.py`** - Extract ground truth from GLB geometry
2. **`blender_compute_expected_transforms.py`** - Compute expected transforms step-by-step
3. **`blender_compare_transforms.py`** - Compare ground truth vs computed transforms
4. **`blender_import_cameras_from_glb.py`** - Main script (updated with fixes)
5. **`blender_analyze_camera_mismatch.py`** - Quick analysis tool (existing)

## Usage Instructions

### Prerequisites

1. **Blender** installed and accessible
2. **MonST3R output directory** containing:
   - `pred_traj.txt` - Camera trajectory in TUM format
   - `pred_intrinsics.txt` - Camera intrinsics
   - `scene.glb` - GLB file with camera geometry
   - `rgb_imgs/` - Image directory (optional, for image size detection)

### Step 1: Import GLB File

1. Open Blender
2. Go to **File → Import → glTF 2.0 (.glb/.gltf)**
3. Select your `scene.glb` file
4. The camera geometry (cones) should now be visible in the scene

### Step 2: Extract Ground Truth Transforms

**Script**: `blender_extract_glb_camera_transforms.py`

**Purpose**: Extract `matrix_world` transforms from GLB camera geometries as ground truth.

**Usage**:
1. Open Blender Scripting workspace
2. Open the script: **File → Open → select `blender_extract_glb_camera_transforms.py`**
3. Run the script (Alt+P or click Run button)

**Output**:
- Creates `glb_camera_transforms.json` in the same directory as your Blender file
- Contains:
  - `num_cameras`: Number of cameras found
  - `transforms`: List of camera transforms with:
    - `name`: Object name
    - `position`: Camera position [x, y, z]
    - `rotation_quaternion`: Rotation as quaternion [w, x, y, z]
    - `rotation_euler`: Rotation as Euler angles [x, y, z]
    - `matrix_world`: Full 4x4 transformation matrix
    - `matrix_world_3x3`: Rotation matrix (3x3)

**Example Output**:
```json
{
  "num_cameras": 50,
  "transforms": [
    {
      "index": 0,
      "name": "Camera_0000",
      "position": [0.0, 0.0, 0.0],
      "rotation_quaternion": [1.0, 0.0, 0.0, 0.0],
      ...
    }
  ]
}
```

### Step 3: Compute Expected Transforms

**Script**: `blender_compute_expected_transforms.py`

**Purpose**: Compute camera transforms step-by-step matching the GLB export process.

**Configuration**:
- Set `MONST3R_OUTPUT_DIR` at the top of the script (or leave as `None` for auto-detection)
- Adjust `SCREEN_WIDTH` if needed (default: 0.03)

**Usage**:
1. Open Blender Scripting workspace
2. Open the script: **File → Open → select `blender_compute_expected_transforms.py`**
3. Configure `MONST3R_OUTPUT_DIR` if needed
4. Run the script (Alt+P or click Run button)

**Output**:
- Creates `computed_transforms.json` in the same directory as your Blender file
- Contains step-by-step transforms:
  - `step1_c2w`: Camera-to-world matrix from TUM pose
  - `step2_c2w_opengl`: After applying OPENGL transform
  - `step3_c2w_opengl_aspect`: After applying aspect_ratio
  - `step4_geometry_transform`: After applying rot45
  - `step5_final_transform`: After applying scene normalization
  - `position`: Final camera position
  - `rotation_quaternion`: Final rotation as quaternion
  - `matrix_world`: Final transformation matrix

**Example Output**:
```json
{
  "num_cameras": 50,
  "transforms": [
    {
      "index": 0,
      "step1_c2w": [[...], [...], [...], [...]],
      "step2_c2w_opengl": [[...], [...], [...], [...]],
      ...
      "position": [0.0, 0.0, 0.0],
      "rotation_quaternion": [1.0, 0.0, 0.0, 0.0],
      ...
    }
  ]
}
```

### Step 4: Compare Transforms

**Script**: `blender_compare_transforms.py`

**Purpose**: Systematically compare ground truth transforms with computed transforms to identify errors.

**Usage**:
1. Ensure `glb_camera_transforms.json` and `computed_transforms.json` exist (from Steps 2 and 3)
2. Open Blender Scripting workspace
3. Open the script: **File → Open → select `blender_compare_transforms.py`**
4. Run the script (Alt+P or click Run button)

**Output**:
- Creates `transform_comparison_report.txt` with detailed comparison
- Prints summary to console:
  - Average and max position differences
  - Average and max rotation differences
  - Matrix differences
  - List of problematic cameras

**Example Report**:
```
================================================================================
Camera Transform Comparison Report
================================================================================

Summary Statistics:
  Total cameras compared: 50
  Position differences:
    Average: 0.000123
    Max: 0.000456
    Min: 0.000001
  Rotation differences (quaternion):
    Average: 0.002345
    Max: 0.008901
    Min: 0.000012
  ...

Problematic Cameras (position diff > 0.001 or rotation diff > 0.01):
  Camera 5 (Camera_0005):
    Position diff: 0.001234
    Rotation diff: 0.012345
```

### Step 5: Import Cameras (Main Script)

**Script**: `blender_import_cameras_from_glb.py`

**Purpose**: Create Blender camera objects from MonST3R trajectory data, matching GLB geometry.

**Configuration** (at top of script):
- `MONST3R_OUTPUT_DIR`: Path to MonST3R output directory (or `None` for auto-detection)
- `CREATE_ANIMATION`: Create keyframe animation (default: `True`)
- `CAMERA_SCALE`: Scale factor for camera objects (default: `1.0`)
- `CAMERA_COLLECTION_NAME`: Collection name (default: `"MonST3R_Cameras"`)
- `SCREEN_WIDTH`: Camera frustum size (default: `0.03`)

**Usage**:
1. Import GLB file into Blender (if not already done)
2. Open Blender Scripting workspace
3. Open the script: **File → Open → select `blender_import_cameras_from_glb.py`**
4. Configure paths if needed
5. Run the script (Alt+P or click Run button)

**Output**:
- Creates camera objects in collection `MonST3R_Cameras`
- Sets camera positions and orientations matching GLB geometry
- Optionally creates keyframe animation
- **Automatically validates** cameras against GLB geometry:
  - Compares first 5 cameras
  - Reports position and rotation differences
  - Shows pass/fail indicators (✓/✗)

**Example Output**:
```
Reading camera poses from: /path/to/pred_traj.txt
Found 50 camera poses
Detected image size: 512x288
Created 50 camera objects!

Validation: Comparing with GLB geometry
Camera 1:
  Position diff: 0.000045 ✓
  Rotation diff: 0.001234 ✓
...

Summary (first 5 cameras):
  Average position difference: 0.000123 ✓
  Max position difference: 0.000456 ✓
  Average rotation difference: 0.002345 ✓
  Max rotation difference: 0.008901 ✓

✓ Validation PASSED: Cameras match GLB geometry!
```

### Step 6: Quick Analysis (Optional)

**Script**: `blender_analyze_camera_mismatch.py`

**Purpose**: Quick analysis tool to compare camera geometry with camera objects.

**Usage**:
1. Import GLB file and run `blender_import_cameras_from_glb.py` first
2. Open Blender Scripting workspace
3. Open the script: **File → Open → select `blender_analyze_camera_mismatch.py`**
4. Run the script (Alt+P or click Run button)

**Output**:
- Prints detailed comparison of first 5 cameras
- Shows matrix differences
- Provides summary statistics

## Complete Workflow

For debugging camera conversion issues:

```
1. Import GLB file into Blender
   ↓
2. Run blender_extract_glb_camera_transforms.py
   → Creates glb_camera_transforms.json (ground truth)
   ↓
3. Run blender_compute_expected_transforms.py
   → Creates computed_transforms.json (expected)
   ↓
4. Run blender_compare_transforms.py
   → Creates transform_comparison_report.txt
   → Identifies problematic cameras and error patterns
   ↓
5. Analyze report to identify root cause
   ↓
6. Fix blender_import_cameras_from_glb.py if needed
   ↓
7. Run blender_import_cameras_from_glb.py
   → Creates camera objects
   → Validates automatically
   ↓
8. Verify cameras match GLB geometry
```

For normal usage (after fixes are verified):

```
1. Import GLB file into Blender
   ↓
2. Run blender_import_cameras_from_glb.py
   → Creates camera objects
   → Validates automatically
   → Shows pass/fail status
```

## Key Fixes Applied

The following fixes were applied to `blender_import_cameras_from_glb.py`:

1. **Aligned transformation logic** with step-by-step computation:
   - Step 1: Build `c2w` from TUM pose
   - Step 2: Apply `OPENGL`
   - Step 3: Apply `aspect_ratio`
   - Step 4: Apply `rot45`
   - Step 5: Apply scene normalization

2. **Fixed scene transform computation**:
   - Correctly computes `scene_transform_inv = inv(first_c2w_opengl @ rot_y180)`
   - Ensures first camera is used for normalization

3. **Improved rot45 handling**:
   - Correctly computes `height = max(screen_width/10, focal * screen_width / H)`
   - Properly applies translation `-height` along camera Z axis

4. **Added validation**:
   - Automatically compares created cameras with GLB geometry
   - Reports differences and pass/fail status

## Troubleshooting

### Issue: "No camera geometry found"

**Solution**:
- Ensure GLB file is imported into Blender
- Check that camera cones are visible in the scene
- Verify camera geometry objects exist (small meshes with < 50 vertices)

### Issue: "Trajectory file not found"

**Solution**:
- Set `MONST3R_OUTPUT_DIR` explicitly in the script
- Or ensure Blender file is saved in a directory where `pred_traj.txt` can be found
- Check that `pred_traj.txt` exists in the expected location

### Issue: "Image size not detected"

**Solution**:
- Ensure `rgb_imgs/` directory exists in MonST3R output directory
- Or manually set `image_size` in the script
- Default image size (512x288) will be used if detection fails

### Issue: Large position/rotation differences

**Solution**:
1. Run `blender_extract_glb_camera_transforms.py` to get ground truth
2. Run `blender_compute_expected_transforms.py` to compute expected
3. Run `blender_compare_transforms.py` to identify error step
4. Check the comparison report for systematic errors
5. Verify:
   - Matrix multiplication order
   - Quaternion conversion (TUM format: qx qy qz qw → Blender: w x y z)
   - Scene transform computation
   - rot45 application

### Issue: Cameras don't match GLB geometry

**Solution**:
- Check that `SCREEN_WIDTH` matches GLB export (default: 0.03)
- Verify image size is correctly detected
- Ensure focal length is correctly parsed from `pred_intrinsics.txt`
- Check that scene transform is computed from first camera

## Success Criteria

After fixes, cameras should match GLB geometry with:
- **Position differences**: < 0.001 units
- **Rotation differences**: < 0.01 radians

The validation in `blender_import_cameras_from_glb.py` automatically checks these criteria and reports pass/fail status.

## Files Created

All scripts are located in `/root/monst3r/user/utils/`:

- `blender_extract_glb_camera_transforms.py` - Extract ground truth
- `blender_compute_expected_transforms.py` - Compute expected transforms
- `blender_compare_transforms.py` - Compare transforms
- `blender_import_cameras_from_glb.py` - Main import script (updated)
- `blender_analyze_camera_mismatch.py` - Quick analysis tool
- `fix_blender_import_camera_from_glb.md` - This documentation

## References

- GLB export code: `dust3r/viz.py` and `dust3r/utils/viz_demo.py`
- Original plan: `.cursor/plans/fix_camera_matrix_conversion_mismatch_b63fe4b7.plan.md`
- Related documentation: `convert_to_colmap.md`, `BLENDER_ADDON_COMPATIBILITY.md`
