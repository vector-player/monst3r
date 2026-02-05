# MonST3R Theoretical Foundation

## Table of Contents
1. [Overview](#overview)
2. [Coordinate Systems](#coordinate-systems)
3. [Camera Pose Representation](#camera-pose-representation)
4. [GLB Export Pipeline](#glb-export-pipeline)
5. [The 45° Rotation (rot45) Explained](#the-45-rotation-rot45-explained)
6. [Optical Center Alignment](#optical-center-alignment)
7. [Scene Normalization](#scene-normalization)
8. [GLB Import to Blender](#glb-import-to-blender)
9. [Transformation Chain Summary](#transformation-chain-summary)

---

## Overview

MonST3R (Monocular Scene Reconstruction) is a computer vision system that reconstructs 3D scenes from monocular image sequences. The system uses camera poses in **OpenCV convention** internally, but exports visualization data (GLB files) using **OpenGL convention** for compatibility with standard 3D viewers. When importing into Blender, additional coordinate system conversions are required.

This document explains the theoretical foundation of coordinate system conversions, the purpose of visualization transforms, and how to correctly extract camera poses from GLB files.

---

## Coordinate Systems

MonST3R involves three right-handed coordinate systems:

### 1. OpenCV (Computer Vision Convention)
- **+X**: Right
- **+Y**: Down
- **+Z**: Forward (into the scene)
- **Used for**: Internal camera pose representation (`pose_c2w`)

```
OpenCV Coordinate System:
        +Z (forward)
         |
         |
         +----> +X (right)
        /
       /
      +Y (down)
```

### 2. OpenGL (Graphics Convention)
- **+X**: Right
- **+Y**: Up
- **+Z**: Backward (toward viewer)
- **Used for**: GLB export and standard 3D graphics

```
OpenGL Coordinate System:
      +Y (up)
       |
       |
       +----> +X (right)
      /
     /
    +Z (backward, toward viewer)
```

### 3. Blender (3D Software Convention)
- **+X**: Right
- **+Y**: Forward
- **+Z**: Up
- **Used for**: Blender camera objects and scene representation

```
Blender Coordinate System:
      +Z (up)
       |
       |
       +----> +X (right)
      /
     /
    +Y (forward)
```

### Conversion Matrices

**OpenCV → OpenGL:**
```python
OPENGL = [[1,  0,  0, 0],
          [0, -1,  0, 0],
          [0,  0, -1, 0],
          [0,  0,  0, 1]]
```
This matrix:
- Keeps X unchanged
- Inverts Y (down → up)
- Inverts Z (forward → backward)

**OpenGL → Blender:**
Blender's glTF importer automatically handles this conversion when importing GLB files. The conversion involves:
- X remains unchanged
- Y (OpenGL up) → Z (Blender up)
- Z (OpenGL backward) → -Y (Blender forward)

---

## Camera Pose Representation

### Camera Space vs World Space

Understanding the difference between **camera space** and **world space** is fundamental to working with camera poses:

#### Camera Space (Local Coordinate Frame)
- **Origin**: Located at the camera's optical center
- **+X axis**: Points to the right (from camera's perspective)
- **+Y axis**: Points down (from camera's perspective, OpenCV convention)
- **+Z axis**: Points forward (into the scene, along optical axis)
- **Definition**: A coordinate system attached to the camera itself, where the camera is always at the origin looking down the +Z axis

#### World Space (Global Coordinate Frame)
- **Origin**: Fixed reference point in the 3D scene
- **Axes**: Defined by the scene's coordinate system (OpenCV convention: +X right, +Y down, +Z forward)
- **Definition**: A global coordinate system where all cameras and 3D points share the same reference frame

#### Key Differences

| Aspect | Camera Space | World Space |
|--------|-------------|-------------|
| **Origin** | Camera optical center | Fixed scene reference point |
| **Orientation** | Relative to camera | Fixed global orientation |
| **Mobility** | Moves with camera | Stationary |
| **Purpose** | Local camera frame | Global scene frame |

### Visual Representation

```
World Space (Global):
                    ┌─────────────┐
                    │   Scene     │
                    │   Origin    │
                    └──────┬──────┘
                           │
                           │  +Z (forward)
                           │   │
                           │   │
                    ┌──────▼───┐
                    │ Camera 1 │  Camera Space 1:
                    │ (c2w_1)  │  - Origin at Camera 1
                    └──────────┘  - +Z along optical axis
                           │
                           │
                    ┌──────▼───┐
                    │ Camera 2 │  Camera Space 2:
                    │ (c2w_2)  │  - Origin at Camera 2
                    └──────────┘  - +Z along optical axis
```

### Camera-to-World Transformation Matrix

MonST3R represents camera poses as **camera-to-world** (`c2w`) transformation matrices:

```python
pose_c2w = [[R11, R12, R13, tx],
            [R21, R22, R23, ty],
            [R31, R32, R33, tz],
            [0,   0,   0,   1 ]]
```

Where:
- **R** (3×3): Rotation matrix representing camera orientation in world space
- **t** (3×1): Translation vector representing camera position in world space

### Transformation Operations

#### Camera Space → World Space
The `pose_c2w` matrix transforms points from camera space to world space:

```python
P_world = pose_c2w @ P_camera
```

**Example:**
- A point at `(0, 0, 1)` in camera space (1 unit forward along optical axis)
- After transformation: `P_world = pose_c2w @ [0, 0, 1, 1]^T`
- Result: The same point expressed in world coordinates

#### World Space → Camera Space
The inverse transformation converts world points to camera space:

```python
pose_w2c = inv(pose_c2w)  # World-to-camera
P_camera = pose_w2c @ P_world
```

**Example:**
- A 3D point in world space
- After transformation: `P_camera = pose_w2c @ P_world`
- Result: The point's coordinates relative to the camera

### Physical Interpretation

#### Rotation Component (R)
The rotation matrix `R` encodes:
- **Camera orientation**: How the camera is rotated in world space
- **Column vectors**: The world-space directions of camera's local X, Y, Z axes
  - Column 1: World direction of camera's +X axis
  - Column 2: World direction of camera's +Y axis  
  - Column 3: World direction of camera's +Z axis (optical axis)

#### Translation Component (t)
The translation vector `t` encodes:
- **Camera position**: The location of camera's optical center in world space
- **Direct mapping**: `t = [tx, ty, tz]^T` is the world-space position of the camera

### Practical Example

Consider a camera viewing a scene:

```python
# Camera pose (c2w matrix)
pose_c2w = [[1,  0,  0,  5],   # Camera at x=5 in world space
            [0,  1,  0,  2],   # Camera at y=2 in world space
            [0,  0,  1,  3],   # Camera at z=3 in world space
            [0,  0,  0,  1]]   # Identity rotation (aligned with world axes)

# A point in camera space (1 unit forward along optical axis)
P_camera = [0, 0, 1, 1]  # Homogeneous coordinates

# Transform to world space
P_world = pose_c2w @ P_camera
# Result: [5, 2, 4, 1] - The point is now 1 unit forward from camera in world space

# Camera position in world space
camera_position = pose_c2w[:3, 3]  # [5, 2, 3]
```

### Why This Matters for MonST3R

1. **Internal Representation**: MonST3R stores camera poses as `c2w` matrices in OpenCV convention
2. **Point Projection**: To project 3D points to image coordinates, points must be in camera space
3. **Scene Reconstruction**: All cameras share the same world space, enabling multi-view reconstruction
4. **GLB Export**: Camera geometry is transformed from camera space to world space using `pose_c2w`

---

## GLB Export Pipeline

The GLB export process (`dust3r/utils/viz_demo.py` and `dust3r/viz.py`) involves multiple transformation steps:

### Step 1: Camera Geometry Creation

For each camera, a frustum cone is created and transformed:

```python
# Create cone geometry
height = max(screen_width/10, focal * screen_width / H)
width = screen_width * sqrt(0.5)  # = screen_width / sqrt(2)
cam = trimesh.creation.cone(width, height, sections=4)
```

The cone is a **4-sided square pyramid** with:
- **Tip** at origin (0, 0, 0)
- **Base** at z = height
- **Axis** along +Z

### Step 2: Visualization Transforms

Two visualization-only transforms are applied:

#### A. Aspect Ratio Transform (`aspect_ratio`)
```python
aspect_ratio = [[W/H, 0, 0, 0],
                [0,   1, 0, 0],
                [0,   0, 1, 0],
                [0,   0, 0, 1]]
```
- **Purpose**: Scale the frustum X-axis to match image aspect ratio (W/H)
- **Effect**: Makes the frustum match the actual image dimensions
- **Visualization-only**: Not part of camera pose

#### B. 45° Rotation (`rot45`)
```python
rot45 = [[cos(45°), -sin(45°), 0, 0],
         [sin(45°),  cos(45°), 0, 0],
         [0,         0,        1, -height],
         [0,         0,        0, 1]]
```
- **Purpose**: Rotate frustum 45° around Z-axis and translate tip to optical center
- **Effect**: 
  - Rotates the square base 45° for proper image plane orientation
  - Translates cone tip by `-height` along Z to position optical center
- **Visualization-only**: Not part of camera pose

### Step 3: Coordinate System Conversion

```python
transform = pose_c2w @ OPENGL @ aspect_ratio @ rot45
```

This transform chain:
1. Starts with `pose_c2w` (OpenCV convention)
2. Converts to OpenGL convention via `OPENGL`
3. Applies visualization transforms (`aspect_ratio`, `rot45`)

### Step 4: Scene Normalization

After all cameras are added, the entire scene is normalized:

```python
rot_y180 = Rotation.from_euler('y', 180°).as_matrix()
scene_transform = inv(cams2world[0] @ OPENGL @ rot_y180)
scene.apply_transform(scene_transform)
```

This:
- Normalizes the scene relative to the first camera
- Applies a 180° Y-rotation for better visualization orientation
- Ensures the first camera is at a canonical position

### Final Camera Geometry Transform

The final transform applied to camera geometry in the GLB file is:

```python
T_final = inv(cams2world[0] @ OPENGL @ rot_y180) @ (c2w @ OPENGL @ aspect_ratio @ rot45)
```

---

## The 45° Rotation (rot45) Explained

### Why 45°?

The 45° rotation serves a specific geometric purpose:

1. **Cone Geometry**: The frustum is created as a 4-sided square pyramid (`sections=4`)
2. **Vertex Selection**: The image plane uses specific cone vertices `[4, 5, 1, 3]` to form a square
3. **Orientation**: Without rotation, the square base is axis-aligned; the 45° rotation aligns these vertices correctly for the image plane

```
Before rot45 (axis-aligned):
     +Y
      |
      |
  +---+---+---> +X
      |
      |
      
After rot45 (rotated 45°):
     +Y
      |
      \
       \
    +---+---> +X
       /
      /
```

### Mathematical Details

```python
rot45[:3, :3] = Rotation.from_euler('z', 45°).as_matrix()
rot45[2, 3] = -height  # Translation component
```

The rotation matrix around Z-axis:
```
R_z(45°) = [[cos(45°), -sin(45°), 0],
            [sin(45°),  cos(45°), 0],
            [0,         0,        1]]
         = [[√2/2, -√2/2, 0],
            [√2/2,  √2/2, 0],
            [0,     0,    1]]
```

The translation `-height` along Z positions the cone tip (optical center) at the correct location relative to the image plane.

### Why It's Visualization-Only

The `rot45` transform is **NOT** part of the camera pose because:
- It only affects the frustum cone geometry
- The camera's actual orientation is determined by `pose_c2w`
- The optical center position is preserved via the translation component
- When extracting camera poses, `rot45` must be removed from orientation

---

## Optical Center Alignment

### Cone Tip = Optical Center

The optical center (camera position) is aligned with the cone tip through the translation component of `rot45`:

```python
rot45[2, 3] = -height
```

This means:
- **Cone tip** (origin before transform) → **Optical center** (after translation)
- The camera position is extracted from `T_final[:3, 3]` (translation component)

### Visual Representation

```
Before transform:
    Cone tip at (0, 0, 0)
    Cone base at (0, 0, height)
    
After rot45 translation:
    Cone tip at (0, 0, -height) → Optical center
    Cone base at (0, 0, 0)
    
After full transform T_final:
    Optical center = T_final[:3, 3]
```

### Extraction Method

When importing cameras from GLB:

```python
# Position: Extract from final transform translation
pos_camera = T_final[:3, 3]  # This is the optical center

# Orientation: Remove visualization transforms
T_no_rot45 = T_final @ inv(rot45)
T_no_vis = T_no_rot45 @ inv(aspect_ratio)
R_camera = T_no_vis[:3, :3]  # Camera rotation matrix
```

---

## Scene Normalization

### Purpose

Scene normalization ensures:
1. **Consistent coordinate frame**: All cameras relative to first camera
2. **Better visualization**: 180° Y-rotation for standard viewing angle
3. **Numerical stability**: Normalized coordinates prevent large values

### Process

```python
# Normalization transform
normalization = inv(cams2world[0] @ OPENGL @ rot_y180)

# Applied to entire scene
scene.apply_transform(normalization)
```

This means:
- First camera (`cams2world[0]`) becomes the reference frame
- Scene is rotated 180° around Y for better orientation
- All subsequent cameras are relative to this normalized frame

### Effect on Camera Transforms

After normalization, camera geometry transforms become:

```
T_final = normalization @ (c2w @ OPENGL @ aspect_ratio @ rot45)
```

Where:
```
normalization = inv(cams2world[0] @ OPENGL @ rot_y180)
```

---

## GLB Import to Blender

### Automatic Coordinate Conversion

When Blender imports a GLB file:
1. **glTF importer** automatically converts OpenGL → Blender coordinates
2. Camera geometry is imported with correct orientation
3. **BUT**: Camera objects need manual creation with correct poses

### Camera Pose Extraction

To extract camera poses from GLB geometry:

#### Method 1: Direct Geometry Transform (Ground Truth)
```python
# Extract from imported GLB geometry
T_geometry = camera_geometry.matrix_world
pos = T_geometry[:3, 3]
R = T_geometry[:3, :3]
```

#### Method 2: Reverse Engineering (Computation)
```python
# Reconstruct from pose_c2w
T_final = normalization @ (c2w @ OPENGL @ aspect_ratio @ rot45)

# Extract position (optical center)
pos = T_final[:3, 3]

# Extract orientation (remove visualization transforms)
T_no_rot45 = T_final @ inv(rot45)
T_no_vis = T_no_rot45 @ inv(aspect_ratio)
R_camera = T_no_vis[:3, :3]
```

### Correct Extraction (METHOD 4)

The recommended method extracts both position and orientation consistently:

```python
# Position: From final transform
pos_camera = T_final[:3, 3]

# Orientation: Remove visualization transforms
geometry_no_rot45 = T_final @ inv(rot45)
camera_orientation = geometry_no_rot45 @ inv(aspect_ratio)
R_camera = camera_orientation[:3, :3]
quat_camera = R_camera.to_quaternion()
```

This ensures:
- Position matches optical center (cone tip)
- Orientation excludes visualization-only transforms
- Consistent extraction from same transform frame

---

## Transformation Chain Summary

### Complete Pipeline

```
OpenCV Camera Pose (pose_c2w)
    ↓
[OPENGL] → Convert to OpenGL convention
    ↓
[aspect_ratio] → Scale X-axis for aspect ratio (visualization)
    ↓
[rot45] → Rotate 45° + translate -height (visualization)
    ↓
Camera Geometry Transform (per camera)
    ↓
[normalization] → Normalize scene relative to first camera
    ↓
Final Geometry Transform (T_final) → Stored in GLB
    ↓
[Blender glTF Import] → Auto-convert OpenGL → Blender
    ↓
Blender Camera Geometry
```

### Mathematical Formulation

**GLB Export:**
```
T_geometry = inv(cams2world[0] @ OPENGL @ rot_y180) @ (c2w @ OPENGL @ aspect_ratio @ rot45)
```

**Camera Pose Extraction:**
```
pos_camera = T_geometry[:3, 3]
T_no_rot45 = T_geometry @ inv(rot45)
T_no_vis = T_no_rot45 @ inv(aspect_ratio)
R_camera = T_no_vis[:3, :3]
```

**Blender Camera Object:**
```python
camera.location = pos_camera  # Optical center
camera.rotation_quaternion = R_camera.to_quaternion()  # Without visualization transforms
```

---

## Key Takeaways

1. **Coordinate Systems**: Three right-handed systems (OpenCV, OpenGL, Blender) require careful conversion
2. **Visualization Transforms**: `rot45` and `aspect_ratio` are visualization-only and must be removed when extracting camera poses
3. **Optical Center**: Positioned at cone tip via `rot45` translation component
4. **Scene Normalization**: Normalizes coordinates relative to first camera for stability
5. **Blender Import**: Automatic OpenGL→Blender conversion for geometry, but camera objects need manual pose extraction

---

## References

- **MonST3R Codebase**: `dust3r/viz.py`, `dust3r/utils/viz_demo.py`
- **Blender Import Script**: `user/utils/blender_import_cameras_from_glb.py`
- **Coordinate System Conventions**: Standard computer vision and graphics conventions

---

## Appendix: Visual Diagrams

### Transformation Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenCV Camera Pose                       │
│                  (pose_c2w: c2w matrix)                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   OPENGL      │  Convert: OpenCV → OpenGL
                    │   Matrix      │  (Invert Y and Z)
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ aspect_ratio  │  Scale X by W/H
                    │  (visualize)  │  (Visualization only)
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    rot45      │  Rotate 45° + translate
                    │  (visualize)  │  (Visualization only)
                    └───────┬───────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │  Camera Geometry Transform  │
              │  (per camera)               │
              └──────────────┬──────────────┘
                             │
                             ▼
                    ┌───────────────┐
                    │ normalization │  Normalize relative to
                    │  (scene-wide) │  first camera
                    └───────┬───────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   Final Transform (T_final) │
              │   Stored in GLB file        │
              └──────────────┬──────────────┘
                             │
                             ▼
                    ┌───────────────┐
                    │ Blender Import│  Auto-convert:
                    │  (glTF)       │  OpenGL → Blender
                    └───────┬───────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   Blender Camera Geometry   │
              │   (Extract pose from this)  │
              └─────────────────────────────┘
```

### Camera Cone Geometry

```
Before transforms:
                    ┌─────────┐
                   /│         │\
                  / │         │ \
                 /  │         │  \
                /   │         │   \
               /    │         │    \
              /     │         │     \
             /      │         │      \
            /       │         │       \
           └────────┴─────────┴────────┘
           Base (z = height)
           
           Tip (z = 0) = Origin

After rot45:
                    ┌─────────┐
                   /│         │\
                  / │         │ \
                 /  │         │  \
                /   │         │   \
               /    │         │    \
              /     │         │     \
             /      │         │      \
            /       │         │       \
           └────────┴─────────┴────────┘
           Base (z = 0)
           
           Tip (z = -height) = Optical Center
           
           (Rotated 45° around Z-axis)
```

### Coordinate System Comparison

```
OpenCV:                    OpenGL:                    Blender:
      +Z (forward)               +Y (up)                     +Z (up)
       |                          |                           |
       |                          |                           |
       +----> +X (right)          +----> +X (right)          +----> +X (right)
      /                          /                           /
     /                          /                           /
    +Y (down)                  +Z (backward)               +Y (forward)
```

---

*Document created: 2026-02-05*
*Last updated: 2026-02-05*
