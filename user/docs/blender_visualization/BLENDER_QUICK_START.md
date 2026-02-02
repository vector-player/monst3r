# Quick Start: Visualize MonST3R Results in Blender

## 🚀 Fastest Method (30 seconds)

1. **Open Blender** (version 2.8+)

2. **Import GLB**:
   - `File` → `Import` → `glTF 2.0 (.glb/.gltf)`
   - Select: `demo_tmp/{seq_name}/scene.glb`
   - Done! ✓

3. **View**:
   - Press `Z` → Select `Material Preview` or `Rendered`
   - Use middle mouse to navigate

## 📝 Using the Python Script (More Control)

1. **Open Blender** → Switch to `Scripting` workspace

2. **Open Script**:
   - `File` → `Open` → Select `blender_import_monst3r.py`

3. **Update Paths** (if needed):
   ```python
   # Script automatically detects MonST3R root directory
   # Default: demo_tmp/lady-running (relative to MonST3R root)
   # Or set absolute path:
   DEMO_TMP_DIR = "/root/monst3r/demo_tmp/lady-running"
   ```

4. **Run Script**: Press `Alt+P` or click ▶️ Run

5. **Result**: Scene + cameras imported with lighting setup

## 🎬 What Gets Imported

- ✅ **3D Scene**: Mesh or point cloud with textures
- ✅ **Camera Poses**: Visual camera frustums (if enabled)
- ✅ **Trajectory**: Camera positions over time
- ✅ **Lighting**: Automatic sun + area lights

## 📂 File Locations

```
demo_tmp/
└── {seq_name}/
    ├── scene.glb              ← Import this!
    ├── pred_traj.txt          ← Camera trajectory
    ├── pred_intrinsics.txt    ← Camera parameters
    └── [other outputs...]
```

## ⌨️ Blender Shortcuts

- `Z` - Viewport shading menu
- `N` - Properties panel
- `Home` - Frame all objects
- `Middle Mouse` - Rotate view
- `Shift + Middle Mouse` - Pan
- `Scroll` - Zoom
- `F12` - Render

## 🔧 Script Options

Edit these in `blender_import_monst3r.py`:

```python
IMPORT_SCENE = True          # Import GLB file
IMPORT_CAMERAS = True        # Import camera trajectory  
CREATE_ANIMATION = False     # Animate camera sequence
SAMPLE_CAMERAS = 10          # Import every Nth camera
```

## 📚 Full Documentation

See `BLENDER_VISUALIZATION_GUIDE.md` for:
- Detailed instructions
- Advanced visualization techniques
- Troubleshooting
- Animation setup

---

**Need Help?** Check the full guide: `BLENDER_VISUALIZATION_GUIDE.md`
