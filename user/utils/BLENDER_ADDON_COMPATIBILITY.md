# Blender photogrammetry_importer Addon Compatibility

## Overview

The `convert_to_colmap.py` script has been updated to ensure full compatibility with the Blender `photogrammetry_importer` addon. This document explains the key requirements and how the script addresses them.

## Critical Requirements

### 1. Image Names Must Contain Digits

**Requirement**: The Blender addon extracts frame numbers from image names to sort cameras for animation:
```python
key=lambda camera: int("".join(filter(str.isdigit, camera.get_relative_fp())))
```

**Solution**: The script always uses sequential naming with zero-padded numbers:
- `image_0001.png`, `image_0002.png`, etc.
- Or `images/image_0001.png` when using `--copy-images`

**Validation**: The script checks that image names contain digits and warns/fixes if they don't.

### 2. images.txt Format

**Requirement**: COLMAP format requires TWO lines per image:
- Line 1: `IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME`
- Line 2: `POINTS2D[]` data (can be empty, but line must exist)

**Solution**: The script always writes both lines, with an empty second line when no 2D points are available.

### 3. Camera Model: PINHOLE

**Requirement**: The addon expects PINHOLE camera model with exactly 4 parameters:
- `fx`: focal length in x direction
- `fy`: focal length in y direction
- `cx`: principal point x coordinate
- `cy`: principal point y coordinate

**Solution**: The script always writes PINHOLE cameras with validated parameters.

### 4. Required Files

**Requirement**: The addon checks for three files in the model directory:
- `cameras.txt`
- `images.txt`
- `points3D.txt`

**Solution**: The script always creates all three files, even if `points3D.txt` is empty (with proper header).

### 5. Image Path Resolution

**Requirement**: The addon resolves image paths relative to the COLMAP model directory.

**Solution**: 
- When `--copy-images` is used, images are written as `images/image_XXXX.png`
- Paths are always relative to the model directory
- Forward slashes are used for cross-platform compatibility

## MonST3R-Specific Enhancements

### Depth Map Support

The script now supports MonST3R depth maps (`frame_*.npy` files):
- Automatically detects `frame_XXXX.npy` files in the input directory
- Extracts 3D points from depth maps when GLB file is not available
- Matches depth maps with corresponding RGB images

### RGB Image Matching

For MonST3R format, the script attempts to match depth maps with RGB images:
- Tries multiple naming patterns: `frame_XXXX.png`, `rgb_XXXX.png`, `image_XXXX.png`
- Falls back gracefully if RGB images are not found

## Usage

### Basic Conversion
```bash
python convert_to_colmap.py --input demo_tmp/lady-running --output demo_tmp/colmap_output
```

### With Image Copying (Recommended for Blender)
```bash
python convert_to_colmap.py --input demo_tmp/lady-running --output demo_tmp/colmap_output --copy-images
```

The `--copy-images` flag:
- Copies images to `images/` subdirectory
- Ensures proper relative paths in `images.txt`
- Makes it easier for Blender to find images

## File Structure

After conversion, the output directory should contain:
```
colmap_output/
├── cameras.txt          # Camera intrinsics (PINHOLE model)
├── images.txt           # Camera poses and image metadata
├── points3D.txt         # 3D point cloud (optional)
└── images/              # (if --copy-images used)
    ├── image_0001.png
    ├── image_0002.png
    └── ...
```

## Blender Import Steps

1. **Select the COLMAP model directory** (containing `cameras.txt`, `images.txt`, `points3D.txt`)
2. **Set image directory** if images are in a subdirectory (e.g., `images/`)
3. **Import** - The addon will:
   - Parse camera poses and intrinsics
   - Create camera objects
   - Sort cameras by frame number (from image names)
   - Create camera animation
   - Load 3D points if available

## Troubleshooting

### Error: "Invalid colmap model / workspace"
- **Cause**: Missing required files or wrong directory selected
- **Solution**: Ensure `cameras.txt`, `images.txt`, and `points3D.txt` exist in the selected directory

### Error: "ValueError: invalid literal for int() with base 10: ''"
- **Cause**: Image name doesn't contain digits
- **Solution**: The script now validates and fixes this automatically

### Images Not Found
- **Cause**: Image paths in `images.txt` don't match actual file locations
- **Solution**: Use `--copy-images` to ensure images are in the correct location

## Validation

The script includes validation checks:
- Image names must contain digits (warns and fixes if not)
- Camera parameters are validated (warns if invalid)
- RGB values are clamped to [0, 255]
- All required files are created

## Notes

- The script prioritizes GLB files for 3D points, then depth maps, then creates empty points3D.txt
- Empty `points3D.txt` is valid - Blender addon handles it gracefully
- Image paths use forward slashes for cross-platform compatibility
- Sequential image naming ensures proper camera animation ordering
