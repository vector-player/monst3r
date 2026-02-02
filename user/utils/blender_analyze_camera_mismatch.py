"""
Blender Script to Analyze Camera Geometry vs Camera Objects

This script compares the camera geometry imported from GLB with the camera objects
created by blender_import_cameras_from_glb.py to identify transformation mismatches.

Usage:
1. Import GLB file into Blender
2. Run blender_import_cameras_from_glb.py to create camera objects
3. Run this script to analyze differences
"""

import bpy
from mathutils import Vector, Matrix, Euler
import math

def analyze_camera_mismatch():
    """Analyze differences between camera geometry and camera objects"""
    print("=" * 60)
    print("Analyzing Camera Geometry vs Camera Objects")
    print("=" * 60)
    
    # Find camera geometry objects (from GLB import)
    # Look for small meshes that are likely camera cones
    camera_geometries = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            # Camera cones are typically small meshes
            if len(mesh.vertices) < 50 and len(mesh.vertices) > 4:
                # Check if it's in a collection that might contain cameras
                in_world_collection = any('world' in c.name.lower() for c in obj.users_collection)
                if in_world_collection or len(obj.users_collection) == 0:
                    camera_geometries.append(obj)
    
    print(f"Found {len(camera_geometries)} camera geometry objects")
    
    # Find camera objects (from our script)
    camera_objects = []
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            in_monst3r_collection = any('MonST3R' in c.name for c in obj.users_collection)
            if in_monst3r_collection:
                camera_objects.append(obj)
    
    print(f"Found {len(camera_objects)} camera objects in MonST3R_Cameras collection")
    print()
    
    if len(camera_geometries) == 0:
        print("ERROR: No camera geometry found. Make sure GLB file is imported.")
        return
    
    if len(camera_objects) == 0:
        print("ERROR: No camera objects found. Run blender_import_cameras_from_glb.py first.")
        return
    
    # Sort both lists (try to match by order)
    camera_geometries.sort(key=lambda x: x.name)
    camera_objects.sort(key=lambda x: int(x.name.split('_')[-1]) if x.name.split('_')[-1].isdigit() else 0)
    
    # Compare first few cameras
    num_to_compare = min(5, len(camera_geometries), len(camera_objects))
    print(f"Comparing first {num_to_compare} cameras:")
    print()
    
    for i in range(num_to_compare):
        geom = camera_geometries[i]
        cam = camera_objects[i] if i < len(camera_objects) else None
        
        if cam is None:
            continue
        
        print(f"Camera {i+1}:")
        print(f"  Geometry: {geom.name}")
        print(f"    Location: {geom.location}")
        print(f"    Rotation (Euler): {geom.rotation_euler}")
        print(f"    Scale: {geom.scale}")
        print(f"    Matrix World:")
        mw_geom = geom.matrix_world
        for j in range(4):
            print(f"      [{j}] [{mw_geom[j][0]:8.4f} {mw_geom[j][1]:8.4f} {mw_geom[j][2]:8.4f} {mw_geom[j][3]:8.4f}]")
        
        print()
        print(f"  Camera Object: {cam.name}")
        print(f"    Location: {cam.location}")
        print(f"    Rotation (Quaternion): {cam.rotation_quaternion}")
        print(f"    Rotation (Euler): {cam.rotation_euler}")
        print(f"    Matrix World:")
        mw_cam = cam.matrix_world
        for j in range(4):
            print(f"      [{j}] [{mw_cam[j][0]:8.4f} {mw_cam[j][1]:8.4f} {mw_cam[j][2]:8.4f} {mw_cam[j][3]:8.4f}]")
        
        print()
        print("  Differences:")
        pos_diff = (geom.location - cam.location).length
        rot_diff_quat = (geom.rotation_euler.to_quaternion() - cam.rotation_quaternion).magnitude
        rot_diff_euler = (geom.rotation_euler - cam.rotation_euler).length
        
        print(f"    Position difference: {pos_diff:.6f}")
        print(f"    Rotation difference (quat): {rot_diff_quat:.6f}")
        print(f"    Rotation difference (euler): {rot_diff_euler:.6f}")
        
        # Analyze matrix differences
        print()
        print("  Matrix Analysis:")
        mw_diff = mw_geom - mw_cam
        print(f"    Translation difference: [{mw_diff[0][3]:.6f}, {mw_diff[1][3]:.6f}, {mw_diff[2][3]:.6f}]")
        
        # Extract rotation matrices
        R_geom = mw_geom.to_3x3()
        R_cam = mw_cam.to_3x3()
        R_diff = R_geom - R_cam
        print(f"    Rotation matrix difference (max): {max(abs(R_diff[i][j]) for i in range(3) for j in range(3)):.6f}")
        
        print()
        print("-" * 60)
        print()
    
    # Summary statistics
    if len(camera_geometries) == len(camera_objects):
        print("Summary Statistics:")
        pos_diffs = []
        rot_diffs = []
        
        for i in range(min(len(camera_geometries), len(camera_objects))):
            geom = camera_geometries[i]
            cam = camera_objects[i]
            pos_diff = (geom.location - cam.location).length
            rot_diff = (geom.rotation_euler.to_quaternion() - cam.rotation_quaternion).magnitude
            pos_diffs.append(pos_diff)
            rot_diffs.append(rot_diff)
        
        if pos_diffs:
            print(f"  Average position difference: {sum(pos_diffs)/len(pos_diffs):.6f}")
            print(f"  Max position difference: {max(pos_diffs):.6f}")
            print(f"  Average rotation difference: {sum(rot_diffs)/len(rot_diffs):.6f}")
            print(f"  Max rotation difference: {max(rot_diffs):.6f}")

if __name__ == "__main__":
    analyze_camera_mismatch()
