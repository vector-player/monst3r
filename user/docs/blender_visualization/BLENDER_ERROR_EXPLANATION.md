# Blender Import Script Error Explanation

## Error Analysis

When running `blender_import_monst3r.py`, you encountered several issues. Here's what happened and how they're fixed:

## 🔍 Error Breakdown

### 1. **COLMAP Import Error** (Harmless - Can Ignore)

```
ERROR: Invalid colmap model / workspace
AssertionError: Invalid colmap model / workspace
```

**What happened:**
- A Blender addon (`photogrammetry_importer`) tried to auto-detect the file format
- It attempted to parse the directory as COLMAP format and failed
- This is harmless - the addon just moves on to try other formats

**Status:** ✅ **Safe to ignore** - This doesn't affect GLB import

### 2. **GLB Import Actually Succeeded!** ✅

Despite the error message later, the GLB file **was successfully imported**:
```
INFO: Blender create Mesh node geometry_0
INFO: Blender create Mesh node geometry_1
...
INFO: Blender create Mesh node geometry_130
INFO: glTF import finished in 1.09s
```

**What happened:**
- All 131 geometries were imported successfully
- The scene is in Blender, ready to view!

**Status:** ✅ **Success** - Your scene is imported

### 3. **Path Resolution Error** ❌ (Fixed)

```
✗ GLB file not found: D:\demo_tmp\lady-running\scene.glb
Warning: Trajectory file not found: D:\demo_tmp\lady-running\pred_traj.txt
```

**What happened:**
- Script couldn't detect MonST3R root directory correctly
- Resolved to wrong path: `D:\demo_tmp\` instead of `D:\ProgramData\monst3r\demo_tmp\`
- This happened because `__file__` wasn't available when using `exec()`

**Root Cause:**
- When you copy-paste or use `exec()` to run the script, `__file__` is not defined
- Fallback logic was using `os.getcwd()` which was `D:\` instead of script directory

**Fix Applied:**
- ✅ Improved path detection with multiple fallback strategies
- ✅ Checks common Windows locations (`D:\ProgramData\monst3r`)
- ✅ Better error messages showing detected paths
- ✅ Clear instructions for manual path override

### 4. **Viewport Framing Error** ❌ (Fixed)

```
ValueError: 1-2 args execution context is supported
```

**What happened:**
- Blender 4.4 changed the API for context overrides
- Old syntax `bpy.ops.view3d.view_all(override)` is no longer valid
- The operator call failed when trying to auto-frame the scene

**Root Cause:**
- Blender 4.4 requires using `bpy.context.temp_override()` instead of passing dict directly

**Fix Applied:**
- ✅ Updated to use `temp_override()` context manager (Blender 4.4 compatible)
- ✅ Added fallback handling if framing fails
- ✅ Graceful error message if auto-framing doesn't work

## ✅ Fixes Applied

### Path Detection Improvements

1. **Better Fallback Logic:**
   ```python
   # Now checks multiple possible locations:
   - Current directory
   - Common Windows paths (D:\ProgramData\monst3r)
   - Parent directories
   - Explicit detection of demo_tmp folder
   ```

2. **Clear Error Messages:**
   - Shows detected MonST3R root
   - Shows computed DEMO_TMP_DIR
   - Provides instructions for manual override

3. **Windows Path Support:**
   - Handles Windows paths correctly
   - Detects `D:\ProgramData\monst3r` automatically

### Viewport Framing Fix

1. **Blender 4.4 Compatibility:**
   ```python
   # Old (doesn't work in 4.4):
   bpy.ops.view3d.view_all(override)
   
   # New (works in 4.4):
   with bpy.context.temp_override(**override):
       bpy.ops.view3d.view_all()
   ```

2. **Graceful Fallback:**
   - If auto-framing fails, shows helpful message
   - User can press `Home` key manually

## 🎯 Current Status

### What Works Now:
- ✅ GLB import (was already working)
- ✅ Path detection (improved)
- ✅ Viewport framing (fixed for Blender 4.4)
- ✅ Better error messages
- ✅ Windows path support

### What to Do:

1. **If paths are still wrong:**
   ```python
   # Edit the script and set absolute path:
   DEMO_TMP_DIR = r"D:\ProgramData\monst3r\demo_tmp\lady-running"
   ```

2. **If GLB import worked:**
   - Your scene is already imported!
   - Press `Home` to frame all objects
   - Press `Z` to change viewport shading

3. **If camera trajectory import failed:**
   - Check that `pred_traj.txt` exists in the demo_tmp directory
   - Or disable camera import: `IMPORT_CAMERAS = False`

## 📝 Quick Fix Guide

### Option 1: Use Absolute Path (Recommended)

Edit the script and change:
```python
# From:
DEMO_TMP_DIR = os.path.join(MONST3R_ROOT, "demo_tmp", "lady-running")

# To:
DEMO_TMP_DIR = r"D:\ProgramData\monst3r\demo_tmp\lady-running"
```

### Option 2: Run from Correct Directory

Before running the script in Blender:
1. Set Blender's working directory to MonST3R root
2. Or use `os.chdir()` in the script

### Option 3: Manual Import (Simplest)

Since GLB import already works:
1. Use Blender's built-in import: `File` → `Import` → `glTF 2.0`
2. Navigate to: `D:\ProgramData\monst3r\demo_tmp\lady-running\scene.glb`
3. Import manually

## 🔧 Troubleshooting

### Path Still Wrong?

1. **Check detected paths:**
   - Script now prints detected MonST3R root
   - Verify it matches your actual location

2. **Set absolute path:**
   ```python
   DEMO_TMP_DIR = r"D:\ProgramData\monst3r\demo_tmp\lady-running"
   ```

3. **Verify files exist:**
   ```python
   import os
   print(os.path.exists(r"D:\ProgramData\monst3r\demo_tmp\lady-running\scene.glb"))
   ```

### Viewport Framing Still Fails?

- Press `Home` key manually to frame all objects
- Or use `View` → `Frame All` from menu

### Camera Trajectory Not Loading?

1. Check file exists: `pred_traj.txt` in demo_tmp directory
2. Check file format: Should be TUM format (timestamp tx ty tz qx qy qz qw)
3. Disable if not needed: `IMPORT_CAMERAS = False`

## 📊 Summary

| Issue | Status | Impact |
|-------|--------|--------|
| COLMAP error | ✅ Harmless | None - can ignore |
| GLB import | ✅ Working | Success - scene imported |
| Path detection | ✅ Fixed | Better detection + fallbacks |
| Viewport framing | ✅ Fixed | Blender 4.4 compatible |
| Error messages | ✅ Improved | More helpful diagnostics |

## ✅ Conclusion

**Good News:** Your GLB file was successfully imported! All 131 geometries are in Blender.

**Fixed Issues:**
- ✅ Path detection now works better
- ✅ Viewport framing compatible with Blender 4.4
- ✅ Better error messages for troubleshooting

**Next Steps:**
1. If paths are still wrong, set `DEMO_TMP_DIR` to absolute path
2. Press `Home` to frame the scene
3. Press `Z` to change viewport shading to see textures

---

**Last Updated:** After fixing Blender 4.4 compatibility issues
