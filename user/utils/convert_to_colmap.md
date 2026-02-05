# COLMAP Conversion Demo - Complete Example with Depth Maps

## Quick Start Command

```bash
# Convert MonST3R output to COLMAP format with depth maps and image copying
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps \
    --max-points 100000

# If cameras point opposite to movement direction in Blender, add:
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps \
    --fix-camera-orientation \
    --max-points 100000
```

## Detailed Example

### Step 1: Check Input Directory Structure

```bash
# Verify MonST3R output files exist
ls demo_tmp/lady-running/

# Should show:
# - pred_traj.txt          (camera trajectory)
# - pred_intrinsics.txt    (camera intrinsics)
# - scene.glb              (3D model, optional)
# - frame_0000.npy         (depth maps)
# - frame_0001.npy
# - frame_0002.npy
# - ...
# - rgb_imgs/              (RGB images directory, optional)
# - conf_*.npy             (confidence maps, optional)
```

### Step 2: Run Conversion

```bash
# Full conversion with all options
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps \
    --max-points 100000
```

**What this does:**
- Converts camera poses from `pred_traj.txt` → `images.txt`
- Converts intrinsics from `pred_intrinsics.txt` → `cameras.txt`
- Extracts 3D points from:
  1. `scene.glb` (if available) - **preferred method**
  2. `frame_*.npy` depth maps (if GLB not available) - **MonST3R format**
  3. `depth_maps/` directory (if available) - standard format
- Copies images to `images/` subdirectory with sequential names
- **Converts depth maps** (`frame_*.npy` → `.geometric.bin`) for Blender addon (if `--copy-depth-maps` used)
- Creates `points3D.txt` with 3D point cloud

### Step 3: Verify Output

```bash
# Check output directory
ls -la demo_tmp/colmap_output/

# Should contain:
# - cameras.txt            (required)
# - images.txt             (required)
# - points3D.txt           (required, can be empty)
# - images/                (if --copy-images used)
#   - image_0001.png
#   - image_0002.png
#   - ...
# - stereo/                (if --copy-depth-maps used)
#   └── depth_maps/
#       └── images/        (matches images/ subdirectory)
#           ├── image_0001.png.geometric.bin
#           ├── image_0002.png.geometric.bin
#           └── ...

### Step 4: Verify File Contents

```bash
# Check cameras.txt (should show PINHOLE cameras)
head -5 demo_tmp/colmap_output/cameras.txt

# Check images.txt (should show image paths with digits)
head -10 demo_tmp/colmap_output/images.txt

# Check points3D.txt (should show 3D points if extraction succeeded)
head -5 demo_tmp/colmap_output/points3D.txt
```

## Interactive Mode

If you don't provide `--input`, the script will prompt you:

```bash
python convert_to_colmap.py --copy-images --max-points 100000

# You'll be prompted:
# [INPUT] Enter path to MonST3R output directory: demo_tmp/lady-running
# [OUTPUT] Output directory (default: demo_tmp/colmap): [press Enter for default]
```

## Command-Line Options

### Required Arguments

- `--input <path>`: Path to MonST3R output directory
  - Must contain `pred_traj.txt` and `pred_intrinsics.txt`
  - Optional: `scene.glb`, `frame_*.npy` depth maps, `rgb_imgs/`

### Optional Arguments

- `--output <path>`: COLMAP output directory (default: sibling directory named `colmap/`)
- `--copy-images`: Copy images to `images/` subdirectory with sequential names (recommended for Blender)
- `--copy-depth-maps`: Convert and copy MonST3R depth maps (`frame_*.npy`) to COLMAP binary format (`.geometric.bin`) in `stereo/depth_maps/` directory for Blender addon
- `--fix-camera-orientation`: Apply 180 degree rotation around Y axis to fix camera orientation (use if cameras point opposite to movement direction in Blender)
- `--max-points <number>`: Maximum number of 3D points to extract (default: 100000)

## Complete Example with All Options

```bash
# Full conversion with custom output and maximum points
python convert_to_colmap.py \
    --input /path/to/monst3r/output/lady-running \
    --output /path/to/colmap/output \
    --copy-images \
    --copy-depth-maps \
    --max-points 50000

# With camera orientation fix (if cameras point wrong direction)
python convert_to_colmap.py \
    --input /path/to/monst3r/output/lady-running \
    --output /path/to/colmap/output \
    --copy-images \
    --copy-depth-maps \
    --fix-camera-orientation \
    --max-points 50000
```

## Depth Map Extraction Priority

The script tries to extract 3D points in this order:

1. **GLB file** (`scene.glb`) - Fastest, most accurate
2. **MonST3R depth maps** (`frame_*.npy`) - Detected automatically
3. **Standard depth maps** (`depth_maps/` directory) - If available
4. **Empty points3D.txt** - Created if no depth data available

## Depth Maps for Blender Addon

### Overview

The Blender `photogrammetry_importer` addon can read depth maps from COLMAP data, but they must be in a specific format and location. Use the `--copy-depth-maps` flag to convert MonST3R depth maps for use with the addon.

### How the Addon Reads Depth Maps

**Expected Location:**
- For COLMAP workspace: `stereo/depth_maps/` directory
- If images are in `images/` subdirectory: `stereo/depth_maps/images/`
- Example: `colmap_output/stereo/depth_maps/images/`

**File Format:**
- Format: COLMAP binary format (`.geometric.bin` or `.photometric.bin`)
- Structure:
  - Header: `width&height&channels&` (text, channels=1 for depth)
  - Data: float32 array in Fortran order (column-major)

**File Naming:**
- Must match image names from `images.txt`
- Pattern: `{image_name}.geometric.bin`
- Example: If `images.txt` has `images/image_0001.png`, addon looks for `stereo/depth_maps/images/image_0001.png.geometric.bin`
- Priority: `.geometric.bin` is checked first, then `.photometric.bin`

**Matching Process:**
The addon matches depth maps to cameras by:
1. Reading image name from `images.txt` (e.g., `images/image_0001.png`)
2. Looking for `{image_name}.geometric.bin` in `stereo/depth_maps/`
3. If images are in `images/` subdirectory, depth maps should be in `stereo/depth_maps/images/`

### Converting MonST3R Depth Maps

**Command:**
```bash
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps
```

**What Happens:**
1. Finds MonST3R depth maps: Looks for `frame_*.npy` files in input directory
2. Converts format: Converts `.npy` → `.geometric.bin` (COLMAP binary format)
3. Matches to images: Maps `frame_0000.npy` → `image_0001.png` (by index)
4. Creates structure: Places in `stereo/depth_maps/` (or `stereo/depth_maps/images/`)

**Output Structure:**
After conversion with `--copy-depth-maps`:
```
colmap_output/
├── cameras.txt
├── images.txt
├── points3D.txt
├── images/
│   ├── image_0001.png
│   └── ...
└── stereo/
    └── depth_maps/
        └── images/              # Matches images/ subdirectory
            ├── image_0001.png.geometric.bin
            ├── image_0002.png.geometric.bin
            └── ...
```

### Using Depth Maps in Blender

**Step 1: Import COLMAP Workspace**
1. Open Blender
2. Go to **File > Import > Photogrammetry > Colmap**
3. **Select the workspace directory**: `colmap_output/` (not a subdirectory)
4. The addon will detect the workspace structure automatically

**Step 2: Enable Depth Maps**
1. In the import dialog, check **"Add Depth Maps (EXPERIMENTAL)"**
2. Optional settings:
   - **Depth Map Display Sparsity**: Controls point density (default: 10)
   - **Use Default Depth Map Color**: Use single color or colorize by camera
   - **Depth Map IDs or Names**: Filter which depth maps to show

**Step 3: Import**
The addon will:
- Load cameras from `cameras.txt`
- Load poses from `images.txt`
- **Match depth maps** to cameras by image name
- Display depth maps as point clouds in Blender

### Important Notes

**Depth Maps Are Optional:**
- The addon works fine **without** depth maps
- `points3D.txt` already contains 3D points extracted from depth maps
- Depth maps in Blender are mainly for **visualization/debugging**

**Why Convert Depth Maps?**
Depth maps in Blender allow you to:
- **Visualize** per-camera depth information
- **Debug** camera poses and depth estimation
- **Compare** different depth estimation methods
- **Export** depth maps for other uses

**Format Conversion:**
- **MonST3R Format** (`frame_*.npy`): NumPy array, shape (H, W), float32, depth in meters
- **COLMAP Format** (`.geometric.bin`): Binary format with header `width&height&1&`, float32 array in Fortran order

## Example Output

```
============================================================
MonST3R to COLMAP Converter
============================================================
Input directory: demo_tmp/lady-running
Output directory: demo_tmp/colmap_output

Parsing trajectory file...
  Found 65 camera poses
Parsing intrinsics file...
  Found 65 camera intrinsics
Finding image files...
  Found 65 image files
Getting image dimensions...
Extracting 3D points...
  Trying GLB file...
  Extracted 50000 points from GLB file

Writing COLMAP files...
  Writing cameras.txt...
  Copying images to demo_tmp/colmap_output/images...
    Copied 65 images
  Using image_base_dir: demo_tmp/colmap_output/images
  Images will be written with 'images/' prefix in images.txt
  Writing images.txt...
  Writing points3D.txt...

============================================================
Conversion complete!
============================================================

COLMAP files written to: demo_tmp/colmap_output
  - cameras.txt (65 cameras)
  - images.txt (65 images)
  - points3D.txt (50000 points)

Note: Images have been copied to demo_tmp/colmap_output/images/
  The images.txt file references these copied images.

If --fix-camera-orientation was used:
============================================================
Camera Orientation Fix Applied
============================================================
Applied 180 degree rotation around Y axis to camera poses.
This fixes cameras pointing opposite to movement direction.

If cameras still point wrong direction, try without --fix-camera-orientation
```

## Using with Blender

After conversion, import in Blender:

1. **Select COLMAP workspace directory**: `demo_tmp/colmap_output/` (not a subdirectory)
2. **Set image directory**: `demo_tmp/colmap_output/images/` (if using `--copy-images`)
3. **Enable depth maps** (optional): Check "Add Depth Maps (EXPERIMENTAL)" if `--copy-depth-maps` was used
4. **Import** - The addon will:
   - Load cameras with correct poses
   - Create camera animation (sorted by frame numbers in image names)
   - Display 3D point cloud (if available)
   - Display depth maps as point clouds (if enabled and available)

**Camera Orientation**: If cameras point opposite to the movement direction after import, re-run the conversion with `--fix-camera-orientation` flag and re-import.

## Troubleshooting

### No Depth Maps Found

If depth maps aren't detected for 3D point extraction, check:
```bash
# Look for MonST3R depth maps
ls demo_tmp/lady-running/frame_*.npy

# Look for standard depth maps
ls demo_tmp/lady-running/depth_maps/
```

### Depth Maps Not Found in Blender

**Symptoms**: Blender addon doesn't find depth maps

**Causes**:
1. Depth maps not converted (missing `--copy-depth-maps` flag)
2. Wrong directory structure
3. Image names don't match

**Solution**:
```bash
# Re-run conversion with --copy-depth-maps
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps
```

### Depth Maps Don't Match Cameras

**Symptoms**: Depth maps appear at wrong locations or don't match cameras

**Causes**:
- Frame numbering mismatch (frame_0000.npy vs image_0001.png)
- Image names changed after depth map conversion

**Solution**:
- Ensure `--copy-images` is used (maintains consistent naming)
- Check that number of depth maps matches number of images

### Empty Depth Maps in Blender

**Symptoms**: Depth maps load but show no points

**Causes**:
- Invalid depth values (NaN, Inf, negative)
- Depth map format conversion error

**Solution**:
- Check depth map values: `np.load('frame_0000.npy')`
- Verify conversion succeeded: Check `.bin` files exist
- Try different depth map display sparsity in Blender

### Empty points3D.txt

This is normal if:
- No GLB file available
- No depth maps found
- Depth map extraction failed

The file will still be created with proper header - Blender addon handles empty files gracefully.

### Images Not Found

Ensure `--copy-images` is used, or manually verify image paths in `images.txt` match actual file locations.

### Cameras Pointing Wrong Direction

**Symptoms**: Cameras in Blender point opposite to the movement direction (e.g., looking backward along the trajectory)

**Cause**: Coordinate system mismatch between MonST3R and COLMAP/Blender conventions

**Solution**:
```bash
# Re-run conversion with --fix-camera-orientation flag
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --fix-camera-orientation

# Then re-import in Blender
```

**Note**: If cameras still point wrong direction after using `--fix-camera-orientation`, try without the flag. The orientation fix applies a 180-degree rotation around the Y axis, which may not be needed for all datasets.

## Advanced: Using MonST3R Depth Maps Directly

If you have `frame_*.npy` files but no GLB:

```bash
# The script automatically detects frame_*.npy files for 3D point extraction
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --max-points 100000

# The script will:
# 1. Try GLB first (if available)
# 2. Fall back to frame_*.npy depth maps for points3D.txt
# 3. Match with RGB images from rgb_imgs/ directory

# To also convert depth maps for Blender addon:
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps \
    --max-points 100000
```

## Notes

- **Image naming**: Always uses sequential names (`image_0001.png`) for Blender compatibility
- **Depth maps for 3D points**: Automatically detects MonST3R format (`frame_*.npy`) for extracting points3D.txt
- **Depth maps for Blender**: Use `--copy-depth-maps` to convert `.npy` → `.geometric.bin` format for Blender addon
- **RGB matching**: Tries multiple patterns to match depth maps with RGB images
- **Validation**: Checks image names contain digits (required for Blender animation)
- **Depth map location**: Blender addon expects depth maps in `stereo/depth_maps/` directory structure
- **Depth map naming**: Must match image names from `images.txt` (e.g., `images/image_0001.png.geometric.bin`)
- **Camera orientation**: If cameras point wrong direction in Blender, use `--fix-camera-orientation` flag to apply 180-degree Y-axis rotation

## Summary

### Quick Reference

**Basic conversion:**
```bash
python convert_to_colmap.py --input demo_tmp/lady-running --copy-images
```

**With depth maps for Blender:**
```bash
python convert_to_colmap.py --input demo_tmp/lady-running --copy-images --copy-depth-maps
```

**With camera orientation fix:**
```bash
python convert_to_colmap.py --input demo_tmp/lady-running --copy-images --fix-camera-orientation
```

**Complete conversion:**
```bash
python convert_to_colmap.py \
    --input demo_tmp/lady-running \
    --output demo_tmp/colmap_output \
    --copy-images \
    --copy-depth-maps \
    --fix-camera-orientation \
    --max-points 100000
```

### Output Files

- `cameras.txt` - Camera intrinsics (PINHOLE model)
- `images.txt` - Camera poses and image metadata
- `points3D.txt` - 3D point cloud (extracted from GLB or depth maps)
- `images/` - Copied images (if `--copy-images` used)
- `stereo/depth_maps/` - Converted depth maps (if `--copy-depth-maps` used)