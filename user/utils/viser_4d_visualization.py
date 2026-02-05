#!/usr/bin/env python3
"""
4D Visualization for MonST3R using Viser

This script creates an interactive 4D visualization of camera trajectories:
- 3D spatial trajectory (x, y, z positions)
- Camera orientations (quaternions visualized as coordinate frames)
- Time dimension (animated playback with slider control)
- Optional scene mesh loading from GLB file

Usage:
    python viser_4d_visualization.py --trajectory pred_traj.txt [--scene scene.glb] [--port 8080]
"""

import argparse
import numpy as np
import viser
import time
from pathlib import Path
from typing import Optional, Tuple, List


def parse_trajectory_file(filepath: str) -> List[Tuple[float, np.ndarray, np.ndarray]]:
    """Parse trajectory file with format: timestamp tx ty tz qx qy qz qw (TUM format)
    
    Returns:
        List of (timestamp, position, quaternion) tuples
    """
    trajectories = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 8:
                timestamp = float(parts[0])
                tx, ty, tz = float(parts[1]), float(parts[2]), float(parts[3])
                qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                position = np.array([tx, ty, tz])
                quaternion = np.array([qw, qx, qy, qz])  # Convert to w, x, y, z format
                trajectories.append((timestamp, position, quaternion))
    return trajectories


def visualize_trajectory_4d(trajectory_file: str, scene_file: Optional[str] = None, 
                            port: int = 8080, auto_play: bool = False):
    """Create 4D visualization of camera trajectory
    
    Args:
        trajectory_file: Path to trajectory file (TUM format)
        scene_file: Optional path to GLB scene file
        port: Port for viser server
        auto_play: Whether to auto-play animation on startup
    """
    # Parse trajectory
    print(f"Loading trajectory from: {trajectory_file}")
    trajectories = parse_trajectory_file(trajectory_file)
    print(f"Loaded {len(trajectories)} camera poses")
    
    if len(trajectories) == 0:
        raise ValueError("No trajectories found in file")
    
    # Extract data
    timestamps = np.array([t[0] for t in trajectories])
    positions = np.array([t[1] for t in trajectories])
    quaternions = np.array([t[2] for t in trajectories])
    
    # Normalize timestamps to start from 0
    timestamps = timestamps - timestamps[0]
    duration = timestamps[-1] - timestamps[0]
    
    print(f"Trajectory duration: {duration:.2f} seconds")
    print(f"Position range: X[{positions[:, 0].min():.3f}, {positions[:, 0].max():.3f}], "
          f"Y[{positions[:, 1].min():.3f}, {positions[:, 1].max():.3f}], "
          f"Z[{positions[:, 2].min():.3f}, {positions[:, 2].max():.3f}]")
    
    # Create viser server
    server = viser.ViserServer(port=port, label="MonST3R 4D Visualization")
    print(f"Viser server started on port {port}")
    print(f"Open browser to: http://localhost:{port}")
    
    # Load scene mesh if provided
    if scene_file and Path(scene_file).exists():
        print(f"Loading scene mesh from: {scene_file}")
        try:
            import trimesh
            mesh = trimesh.load(scene_file)
            if isinstance(mesh, trimesh.Scene):
                # If it's a scene, get the first mesh
                mesh = list(mesh.geometry.values())[0]
            
            # Add mesh to scene
            server.scene.add_mesh_trimesh(
                "scene_mesh",
                mesh=mesh,
            )
            print("Scene mesh loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load scene mesh: {e}")
    
    # Draw trajectory path as line segments
    # Format: (N, 2, 3) where N is number of segments, each segment has 2 points (start, end)
    trajectory_segments = np.zeros((len(positions) - 1, 2, 3))
    for i in range(len(positions) - 1):
        trajectory_segments[i, 0] = positions[i]
        trajectory_segments[i, 1] = positions[i+1]
    
    server.scene.add_line_segments(
        "camera_trajectory",
        points=trajectory_segments.tolist(),
        colors=(0, 255, 0),  # Green trajectory
        line_width=3.0,
    )
    
    # Create camera frames and frustums for all poses
    frame_names = []
    frustum_names = []
    
    for i, (pos, quat) in enumerate(zip(positions, quaternions)):
        frame_name = f"camera_frame_{i}"
        frustum_name = f"camera_frustum_{i}"
        frame_names.append(frame_name)
        frustum_names.append(frustum_name)
        
        # Add coordinate frame
        server.scene.add_frame(
            frame_name,
            wxyz=quat,  # Viser expects numpy array (w, x, y, z)
            position=pos,
            axes_length=0.05,
            axes_radius=0.005,
        )
        
        # Add camera frustum
        # Note: OpenCV convention uses +Z forward, but viser might use different convention
        # We'll use a small frustum scale
        server.scene.add_camera_frustum(
            frustum_name,
            wxyz=quat,  # Viser expects numpy array (w, x, y, z)
            position=pos,
            fov=60.0,  # Field of view in degrees
            aspect=16/9,  # Aspect ratio
            scale=0.05,  # Scale of frustum
            color=(255, 100, 100),  # Light red
        )
    
    # GUI Controls
    # Current frame index
    current_frame = server.gui.add_slider(
        "Frame",
        min=0,
        max=len(trajectories) - 1,
        step=1,
        initial_value=0,
    )
    
    # Time slider
    time_slider = server.gui.add_slider(
        "Time (s)",
        min=0.0,
        max=float(duration),
        step=0.01,
        initial_value=0.0,
    )
    
    # Playback controls
    play_button = server.gui.add_button("▶ Play")
    pause_button = server.gui.add_button("⏸ Pause")
    reset_button = server.gui.add_button("⏮ Reset")
    
    # Toggle controls
    show_frames = server.gui.add_checkbox("Show Frames", initial_value=True)
    show_frustums = server.gui.add_checkbox("Show Frustums", initial_value=False)
    show_trajectory = server.gui.add_checkbox("Show Trajectory", initial_value=True)
    
    # Playback state (using checkbox as toggle)
    is_playing = server.gui.add_checkbox("Playing", initial_value=auto_play)
    playback_speed = server.gui.add_slider(
        "Speed",
        min=0.1,
        max=5.0,
        step=0.1,
        initial_value=1.0,
    )
    
    # Frame info display
    frame_info = server.gui.add_text("Info", initial_value="Frame: 0 / 0")
    
    # Store handles for visibility control
    frame_handles = {}
    frustum_handles = {}
    
    def update_frame(frame_idx: int):
        """Update visualization to show specific frame"""
        frame_idx = int(np.clip(frame_idx, 0, len(trajectories) - 1))
        
        # Update frame visibility
        for i, frame_name in enumerate(frame_names):
            visible = (i == frame_idx) if show_frames.value else False
            # Update frame visibility by removing and re-adding
            if visible and frame_name not in frame_handles:
                frame_handles[frame_name] = server.scene.add_frame(
                    frame_name,
                    wxyz=quaternions[i],
                    position=positions[i],
                    axes_length=0.05,
                    axes_radius=0.005,
                )
            elif not visible and frame_name in frame_handles:
                server.scene.remove_by_name(frame_name)
                del frame_handles[frame_name]
        
        # Update frustum visibility
        for i, frustum_name in enumerate(frustum_names):
            visible = (i == frame_idx) if show_frustums.value else False
            if visible and frustum_name not in frustum_handles:
                frustum_handles[frustum_name] = server.scene.add_camera_frustum(
                    frustum_name,
                    wxyz=quaternions[i],
                    position=positions[i],
                    fov=60.0,
                    aspect=16/9,
                    scale=0.05,
                    color=(255, 100, 100),
                )
            elif not visible and frustum_name in frustum_handles:
                server.scene.remove_by_name(frustum_name)
                del frustum_handles[frustum_name]
        
        # Update info
        pos = positions[frame_idx]
        t = timestamps[frame_idx]
        frame_info.value = f"Frame: {frame_idx}/{len(trajectories)-1} | Time: {t:.2f}s | Pos: [{pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f}]"
        
        # Update sliders (avoid recursion)
        if abs(current_frame.value - frame_idx) > 0.5:
            current_frame.value = frame_idx
        if abs(time_slider.value - float(t)) > 0.01:
            time_slider.value = float(t)
    
    # Callbacks
    @current_frame.on_update
    def _(_):
        update_frame(int(current_frame.value))
    
    @time_slider.on_update
    def _(_):
        # Find closest frame to time
        t = time_slider.value
        frame_idx = np.argmin(np.abs(timestamps - t))
        if abs(current_frame.value - frame_idx) > 0.5:
            update_frame(frame_idx)
    
    @play_button.on_click
    def _(_):
        is_playing.value = True
    
    @pause_button.on_click
    def _(_):
        is_playing.value = False
    
    @reset_button.on_click
    def _(_):
        is_playing.value = False
        update_frame(0)
    
    @show_frames.on_update
    def _(_):
        update_frame(int(current_frame.value))
    
    @show_frustums.on_update
    def _(_):
        update_frame(int(current_frame.value))
    
    @show_trajectory.on_update
    def _(_):
        if show_trajectory.value:
            # Re-add trajectory
            server.scene.add_line_segments(
                "camera_trajectory",
                points=trajectory_points.tolist(),
                colors=(0, 255, 0),
                line_width=3.0,
            )
        else:
            server.scene.remove_by_name("camera_trajectory")
    
    # Initialize all frames (but only show current one)
    for i, frame_name in enumerate(frame_names):
        frame_handles[frame_name] = server.scene.add_frame(
            frame_name,
            wxyz=quaternions[i],
            position=positions[i],
            axes_length=0.05,
            axes_radius=0.005,
        )
    
    # Initialize
    update_frame(0)
    
    # Animation loop
    last_time = time.time()
    current_time_value = 0.0
    
    print("\n" + "="*60)
    print("4D Visualization Ready!")
    print("="*60)
    print("Controls:")
    print("  - Frame slider: Jump to specific frame")
    print("  - Time slider: Jump to specific time")
    print("  - Play/Pause: Animate through trajectory")
    print("  - Reset: Return to first frame")
    print("  - Toggles: Show/hide frames, frustums, trajectory")
    print("="*60)
    print("\nPress Ctrl+C to stop the server")
    
    try:
        while True:
            time.sleep(0.01)  # Small delay to prevent busy waiting
            
            if is_playing.value:
                current_time = time.time()
                dt = (current_time - last_time) * playback_speed.value
                last_time = current_time
                
                current_time_value += dt
                if current_time_value > duration:
                    current_time_value = duration
                    is_playing.value = False  # Stop at end
                
                # Update time slider (which will trigger frame update)
                if abs(time_slider.value - current_time_value) > 0.01:
                    time_slider.value = float(current_time_value)
            else:
                last_time = time.time()
    
    except KeyboardInterrupt:
        print("\nShutting down server...")


def main():
    parser = argparse.ArgumentParser(description="4D Visualization for MonST3R")
    parser.add_argument(
        "--trajectory",
        type=str,
        required=True,
        help="Path to trajectory file (TUM format: timestamp tx ty tz qx qy qz qw)",
    )
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Optional path to GLB scene file",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for viser server (default: 8080)",
    )
    parser.add_argument(
        "--auto-play",
        action="store_true",
        help="Auto-play animation on startup",
    )
    
    args = parser.parse_args()
    
    visualize_trajectory_4d(
        trajectory_file=args.trajectory,
        scene_file=args.scene,
        port=args.port,
        auto_play=args.auto_play,
    )


if __name__ == "__main__":
    main()
