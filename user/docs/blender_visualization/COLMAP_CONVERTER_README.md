# COLMAP Converter Script

## Overview

`convert_to_colmap.py` converts MonST3R reconstruction results to COLMAP format.

## Usage

### Basic Usage (Default Output)

```bash
python convert_to_colmap.py --input demo_tmp/lady-running
```

This will create COLMAP files in `demo_tmp/output/` (sibling directory of input).

### Custom Output Path

```bash
python convert_to_colmap.py --input demo_tmp/lady-running --output colmap_output
```

### Limit Number of Points

```bash
python convert_to_colmap.py --input demo_tmp/lady-running --max-points 50000
```

## Arguments

- `--input <path>` (required): Path to MonST3R output directory
  - Must contain: `pred_traj.txt`, `pred_intrinsics.txt`
  - Optional: `scene.glb`, `depth_maps/`, `rgb_imgs/`

- `--output <path>` (optional): Path to COLMAP output directory
  - Default: Sibling directory of input named `output/`
  - Example: If input is `demo_tmp/lady-running`, output is `demo_tmp/output/`

- `--max-points <number>` (optional): Maximum number of 3D points to extract
  - Default: 100000
  - Used to limit memory usage for large scenes

## Output Files

The script generates three COLMAP format files:

1. **cameras.txt** - Camera parameters
   - Format: `CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]`
   - Uses PINHOLE model with fx, fy, cx, cy

2. **images.txt** - Image poses and names
   - Format: `IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME`
   - Converts from TUM format (qx qy qz qw) to COLMAP format (qw qx qy qz)

3. **points3D.txt** - 3D point cloud
   - Format: `POINT3D_ID, X, Y, Z, R, G, B, ERROR, TRACK[]`
   - Extracted from GLB file or depth maps

## Conversion Details

### Camera Poses
- **Input**: TUM format (`pred_traj.txt`)
  - Format: `timestamp tx ty tz qx qy qz qw`
- **Output**: COLMAP format (`images.txt`)
  - Format: `IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME`
  - Quaternion order converted: TUM (qx qy qz qw) → COLMAP (qw qx qy qz)

### Camera Intrinsics
- **Input**: 3x3 K matrix (`pred_intrinsics.txt`)
  - Format: `fx 0 cx 0 fy cy 0 0 1` (9 values per line)
- **Output**: COLMAP PINHOLE model (`cameras.txt`)
  - Format: `CAMERA_ID, PINHOLE, WIDTH, HEIGHT, fx, fy, cx, cy`

### 3D Points
- **Source 1**: GLB file (`scene.glb`) - Preferred
  - Extracts vertices and colors from 3D model
- **Source 2**: Depth maps (`depth_maps/`) - Fallback
  - Backprojects depth maps to 3D using camera poses and intrinsics
  - Requires RGB images for colors

## Examples

### Example 1: Basic Conversion

```bash
cd /root/monst3r
python user/docs/blender_visualization/convert_to_colmap.py \
    --input demo_tmp/lady-running
```

Output: `demo_tmp/output/` with COLMAP files

### Example 2: Custom Output Location

```bash
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output /path/to/colmap/model
```

### Example 3: Limit Points for Large Scene

```bash
python convert_to_colmap.py \
    --input demo_tmp/large-sequence \
    --max-points 50000
```

## Using with COLMAP

After conversion, you can use the files with COLMAP:

### Convert to Binary Format

```bash
colmap model_converter \
    --input_path demo_tmp/output \
    --output_path demo_tmp/output \
    --output_type BIN
```

### View in COLMAP GUI

```bash
colmap gui --database_path database.db --image_path images/
```

Then import the model from `demo_tmp/output/`

## Requirements

- Python 3.6+
- numpy
- scipy
- trimesh (for GLB parsing)
- PIL or OpenCV (for image handling, optional)

Install dependencies:
```bash
pip install numpy scipy trimesh pillow opencv-python
```

## Troubleshooting

### No 3D Points Extracted

- Check if `scene.glb` exists
- Check if `depth_maps/` directory exists
- Points will be empty if neither source is available

### Image Files Not Found

- Script will use placeholder names if images not found
- Ensure `rgb_imgs/` directory exists with images
- Or images should be in the input directory

### Mismatched Poses and Intrinsics

- Script automatically truncates to minimum length
- Warning message will indicate if counts don't match

## File Structure

```
Input (MonST3R):
demo_tmp/lady-running/
├── pred_traj.txt          ← Camera poses (TUM format)
├── pred_intrinsics.txt    ← Camera intrinsics
├── scene.glb              ← 3D model (optional)
├── depth_maps/            ← Depth maps (optional)
└── rgb_imgs/              ← RGB images (optional)

Output (COLMAP):
demo_tmp/output/
├── cameras.txt            ← Camera parameters
├── images.txt             ← Image poses
└── points3D.txt           ← 3D point cloud
```

## Notes

- The script handles quaternion conversion automatically
- Image dimensions are detected from files or estimated from intrinsics
- 3D points are sampled if too many (controlled by `--max-points`)
- Empty `points3D.txt` is created if no points can be extracted

---

**Last Updated:** After creating COLMAP converter script
