# COLMAP Import Error Explanation

## Error Summary

When importing COLMAP data into Blender using the `photogrammetry_importer` addon, two issues occurred:

1. **Image Path Resolution Error**: Images were not found at expected locations
2. **Parsing Error**: `ValueError: invalid literal for int() with base 10: ''`

## Error Details

### Issue 1: Image Path Resolution

**Error Messages:**
```
WARNING: Could not find image at D:\ProgramData\monst3r\demo_tmp\image_0001.png
WARNING: Could not find image at D:\ProgramData\monst3r\demo_tmp\image_0002.png
...
```

**Root Cause:**
- The Blender addon was looking for images at: `D:\ProgramData\monst3r\demo_tmp\image_0001.png`
- But images were actually located at: `D:\ProgramData\monst3r\demo_tmp\colmap_with_images\images\image_0001.png`
- The `images.txt` file was writing just the filename (`image_0001.png`) instead of the relative path (`images/image_0001.png`)

**Why This Happened:**
- The `write_colmap_images()` function was not correctly computing relative paths when images were copied to an `images/` subdirectory
- The Blender addon expects paths in `images.txt` to be relative to the COLMAP model directory (where `images.txt` is located)

### Issue 2: Parsing Error

**Error Message:**
```
ValueError: invalid literal for int() with base 10: ''
```

**Location:**
- `camera_animation_utility.py`, line 375
- The addon tries to extract frame numbers from image names to create camera animation

**Root Cause:**
- The addon's parsing logic encountered an empty string when trying to extract a frame number
- This could happen if:
  - The image name in `images.txt` was empty or malformed
  - There was a mismatch between expected and actual image path format

## Fix Applied

### 1. Relative Path Computation

Updated `write_colmap_images()` to:
- Compute relative paths from the COLMAP model directory (where `images.txt` is located)
- Use `os.path.relpath()` to create proper relative paths
- Handle Windows path separators by converting to forward slashes (`/`)
- When images are in an `images/` subdirectory, write `images/image_0001.png` instead of just `image_0001.png`

### 2. Image Name Validation

Added safeguards to ensure:
- Image names are never empty
- Image names are properly trimmed
- Fallback to sequential naming if path computation fails

### 3. Correct Parameter Passing

Fixed the `image_base_dir` parameter:
- When `--copy-images` is used, pass `images_dir` to indicate images are in a subdirectory
- This helps the function write correct relative paths

## Code Changes

### Key Changes in `write_colmap_images()`:

```python
# Get the COLMAP model directory (where images.txt is located)
model_dir = os.path.dirname(os.path.abspath(output_path))

# Make path relative to COLMAP model directory
img_abs = os.path.abspath(img_file)
try:
    # Try to make relative to model directory
    img_rel = os.path.relpath(img_abs, model_dir)
    # Use forward slashes for cross-platform compatibility
    img_rel = img_rel.replace('\\', '/')
except ValueError:
    # If paths are on different drives (Windows), use absolute path
    img_rel = img_abs.replace('\\', '/')

# Ensure img_name is never empty (prevents parsing errors)
if not img_name or img_name.strip() == "":
    img_name = f"image_{i:04d}{ext}"
```

## Solution

### For Users

1. **Use `--copy-images` flag**: When converting MonST3R output to COLMAP format, use the `--copy-images` flag:
   ```bash
   python convert_to_colmap.py --input demo_tmp/lady-running --copy-images
   ```

2. **Verify `images.txt` format**: After conversion, check that `images.txt` contains relative paths:
   ```
   1 0.123456 0.234567 ... 1 images/image_0001.png
   ```
   Not:
   ```
   1 0.123456 0.234567 ... 1 image_0001.png
   ```

3. **Import in Blender**: When importing in Blender:
   - Select the COLMAP model directory (contains `cameras.txt`, `images.txt`, `points3D.txt`)
   - The addon will automatically look for images relative to this directory
   - If images are in `images/` subdirectory, the paths in `images.txt` should reflect this

## Expected Behavior After Fix

1. **Correct Image Paths**: `images.txt` will contain paths like `images/image_0001.png` (relative to COLMAP model directory)

2. **No Parsing Errors**: Image names will always be valid, preventing the `ValueError` when extracting frame numbers

3. **Successful Import**: The Blender addon will:
   - Find images at the correct locations
   - Parse image names correctly to extract frame numbers
   - Create camera animation successfully

## Testing

To verify the fix works:

1. Convert MonST3R output with `--copy-images`:
   ```bash
   python convert_to_colmap.py --input demo_tmp/lady-running --output demo_tmp/colmap_output --copy-images
   ```

2. Check `images.txt`:
   ```bash
   head -5 demo_tmp/colmap_output/images.txt
   ```
   Should show paths like `images/image_0001.png`

3. Import in Blender:
   - Open Blender
   - Install/enable `photogrammetry_importer` addon
   - Import COLMAP model from `demo_tmp/colmap_output`
   - Verify no warnings about missing images
   - Verify camera animation is created successfully

## Related Files

- `/root/monst3r/user/docs/blender_visualization/convert_to_colmap.py` - Conversion script
- `/root/monst3r/user/docs/blender_visualization/COLMAP_CONVERTER_README.md` - Usage documentation
