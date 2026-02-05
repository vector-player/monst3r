# 4D Visualization for MonST3R using Viser

This script provides an interactive 4D visualization of camera trajectories from MonST3R reconstruction results.

## Features

- **3D Trajectory Visualization**: View the camera path in 3D space
- **Camera Orientations**: See camera coordinate frames at each pose
- **Camera Frustums**: Optional visualization of camera viewing frustums
- **Time-based Animation**: Animate through the trajectory with playback controls
- **Scene Mesh Loading**: Optionally load and display the reconstructed scene mesh (GLB format)
- **Interactive Controls**: 
  - Frame slider to jump to specific frames
  - Time slider to jump to specific timestamps
  - Play/Pause/Reset buttons for animation
  - Toggle visibility of frames, frustums, and trajectory
  - Adjustable playback speed

## Installation

Make sure you're in the `monst3r` conda environment:

```bash
conda activate monst3r
pip install viser
```

## Usage

### Basic Usage

```bash
python user/utils/viser_4d_visualization.py \
    --trajectory demo_tmp/lady-running/pred_traj.txt \
    --port 8080
```

### With Scene Mesh

```bash
python user/utils/viser_4d_visualization.py \
    --trajectory demo_tmp/lady-running/pred_traj.txt \
    --scene demo_tmp/lady-running/scene.glb \
    --port 8080
```

### Auto-play on Startup

```bash
python user/utils/viser_4d_visualization.py \
    --trajectory demo_tmp/lady-running/pred_traj.txt \
    --scene demo_tmp/lady-running/scene.glb \
    --port 8080 \
    --auto-play
```

## Arguments

- `--trajectory`: Path to trajectory file (required)
  - Format: TUM format (`timestamp tx ty tz qx qy qz qw`)
- `--scene`: Path to GLB scene mesh file (optional)
- `--port`: Port for viser server (default: 8080)
- `--auto-play`: Start animation automatically on load

## Trajectory File Format

The trajectory file should be in TUM format:
```
timestamp tx ty tz qx qy qz qw
```

Where:
- `timestamp`: Time in seconds
- `tx ty tz`: Camera position (translation)
- `qx qy qz qw`: Camera orientation (quaternion)

## Controls

Once the visualization opens in your browser:

1. **Frame Slider**: Jump to a specific frame number
2. **Time Slider**: Jump to a specific timestamp
3. **Play Button**: Start animation playback
4. **Pause Button**: Pause animation
5. **Reset Button**: Return to the first frame
6. **Show Frames**: Toggle visibility of coordinate frames
7. **Show Frustums**: Toggle visibility of camera frustums
8. **Show Trajectory**: Toggle visibility of trajectory path
9. **Speed Slider**: Adjust playback speed (0.1x to 5.0x)
10. **Playing Checkbox**: Toggle animation state

## Coordinate System

The visualization uses the coordinate system from the trajectory file. MonST3R typically uses:
- **OpenCV convention**: +X right, +Y down, +Z forward
- Camera quaternions are in TUM format (qx, qy, qz, qw) and converted to viser format (w, x, y, z)

## Example: Lady-Running Demo

```bash
cd /root/monst3r
conda activate monst3r
python user/utils/viser_4d_visualization.py \
    --trajectory demo_tmp/lady-running/pred_traj.txt \
    --scene demo_tmp/lady-running/scene.glb \
    --port 8080
```

Then open your browser to: `http://localhost:8080`

## Notes

- The server runs until you press Ctrl+C
- Multiple clients can connect to the same server
- The visualization is synchronized across all connected clients
- Camera frustums use a default FOV of 60° and aspect ratio of 16:9
- Adjust frustum scale in the code if needed (default: 0.05)

## Troubleshooting

**Port already in use**: Change the port with `--port` argument

**Scene mesh not loading**: Check that the GLB file exists and is a valid mesh file

**Trajectory not displaying**: Verify the trajectory file format matches TUM format

**Animation not working**: Check that the trajectory has valid timestamps
