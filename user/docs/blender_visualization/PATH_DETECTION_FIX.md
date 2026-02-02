# Path Detection Error Fix

## 🔍 Problem Analysis

**Error Message:**
```
✗ GLB file not found: D:\demo_tmp\lady-running\scene.glb
  MonST3R root detected: D:\
  DEMO_TMP_DIR: D:\demo_tmp\lady-running
```

**Root Cause:**
1. When Blender runs the script via `exec()` or copy-paste, `__file__` is not available
2. The fallback logic checks for `demo_tmp` directory starting from current working directory
3. Blender's working directory is `D:\Program Files\Blender Foundation\Blender 4.4`
4. The script checked `D:\demo_tmp` and found it exists (possibly unrelated directory)
5. It incorrectly identified `D:\` as MonST3R root
6. Actual MonST3R root is `D:\ProgramData\monst3r`

## ✅ Fix Applied

### Improved Path Detection

1. **Check Common Windows Locations First:**
   - `D:\ProgramData\monst3r` (most common)
   - `C:\monst3r`
   - `D:\monst3r`
   - `~\monst3r` (user home)

2. **More Robust Verification:**
   - Not just checking if `demo_tmp` exists
   - Also verifies MonST3R-specific files/directories:
     - `demo_tmp/lady-running` (common sequence)
     - `demo.py` (MonST3R script)
     - `dust3r/` (MonST3R module)

3. **Better Error Messages:**
   - Shows detected paths for debugging
   - Automatically searches common locations
   - Provides exact fix instructions if file is found

## 🚀 Quick Fix

### Option 1: Edit Script (Recommended)

Open `blender_import_monst3r.py` and find this line (~57):

```python
DEMO_TMP_DIR = os.path.join(MONST3R_ROOT, "demo_tmp", "lady-running")
```

Change it to:

```python
DEMO_TMP_DIR = r"D:\ProgramData\monst3r\demo_tmp\lady-running"
```

### Option 2: Manual Import (Fastest)

Since path detection can be tricky, just import manually:

1. In Blender: `File` → `Import` → `glTF 2.0 (.glb/.gltf)`
2. Navigate to: `D:\ProgramData\monst3r\demo_tmp\lady-running\scene.glb`
3. Click `Import`

## 📋 Verification

After fixing, the script should show:
```
✓ GLB file imported successfully
```

If you still see errors, check:
1. File actually exists: `D:\ProgramData\monst3r\demo_tmp\lady-running\scene.glb`
2. Path is correct (no typos)
3. File permissions allow reading

## 🔧 Why This Happens

**Technical Explanation:**
- Blender's Python environment doesn't have `__file__` when using `exec()` or copy-paste
- `os.getcwd()` returns Blender's installation directory, not script location
- Path detection must rely on heuristics and common locations
- Windows has many possible installation paths

**Best Practice:**
- Use absolute paths for reliability
- Or set `DEMO_TMP_DIR` explicitly in the script
- Manual import is always reliable

---

**Status:** Fixed in latest version of script
**Last Updated:** After improving path detection logic
