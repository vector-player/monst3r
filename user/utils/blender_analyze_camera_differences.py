"""
Blender Script to Analyze Differences Between Camera Geometry and Camera Objects

This script compares the camera geometry (imported from GLB) with the camera objects
created by blender_import_cameras_from_glb.py to identify transformation errors.

Usage:
1. Import GLB file into Blender
2. Run blender_import_cameras_from_glb.py to create camera objects
3. Run this script to analyze differences
4. Use the output to fix transformation issues
"""

import bpy
from mathutils import Vector, Matrix
import math

# ============================================================================
# CONFIGURATION
# ============================================================================

CAMERA_GEOMETRY_COLLECTION = None  # None = search all objects, or specify collection name
CAMERA_OBJECTS_COLLECTION = "MonST3R_Cameras"  # Collection with camera objects

# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def find_camera_geometries():
    """Find camera cone geometries in the scene"""
    geometries = []
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            # Check if it's a small mesh (likely camera cone)
            if len(obj.data.vertices) < 50:  # Camera cones are small
                geometries.append(obj)
    return geometries

def find_camera_objects():
    """Find camera objects in the specified collection"""
    cameras = []
    if CAMERA_OBJECTS_COLLECTION in bpy.data.collections:
        collection = bpy.data.collections[CAMERA_OBJECTS_COLLECTION]
        for obj in collection.objects:
            if obj.type == 'CAMERA':
                cameras.append(obj)
    return cameras

def extract_camera_center_from_geometry(geom_obj):
    """Extract camera center (cone tip) from geometry"""
    mesh = geom_obj.data
    world_matrix = geom_obj.matrix_world
    
    # Get vertices in world space
    vertices_world = [world_matrix @ Vector(v.co) for v in mesh.vertices]
    
    # Find tip (vertex farthest from centroid)
    centroid = sum(vertices_world, Vector([0, 0, 0])) / len(vertices_world)
    
    tip_world = None
    max_distance = 0
    for v in vertices_world:
        dist = (v - centroid).length
        if dist > max_distance:
            max_distance = dist
            tip_world = v
    
    return tip_world

def extract_camera_orientation_from_geometry(geom_obj):
    """Extract camera orientation from geometry"""
    mesh = geom_obj.data
    world_matrix = geom_obj.matrix_world
    
    # Get rotation matrix from world matrix
    # The geometry's local Z axis (after transform) represents camera viewing direction
    R_geometry = world_matrix.to_3x3()
    
    return R_geometry

def analyze_differences():
    """Analyze differences between geometry and camera objects"""
    print("=" * 80)
    print("Camera Geometry vs Camera Objects Analysis")
    print("=" * 80)
    
    # Find geometries and cameras
    geometries = find_camera_geometries()
    cameras = find_camera_objects()
    
    print(f"\nFound {len(geometries)} camera geometries")
    print(f"Found {len(cameras)} camera objects")
    
    if len(geometries) == 0 or len(cameras) == 0:
        print("ERROR: Need both geometry and camera objects to compare")
        return
    
    # Sort both by name or position
    geometries.sort(key=lambda x: x.name)
    cameras.sort(key=lambda x: x.name)
    
    # Compare first few cameras
    num_to_compare = min(5, len(geometries), len(cameras))
    print(f"\nComparing first {num_to_compare} cameras:")
    print("-" * 80)
    
    for i in range(num_to_compare):
        geom = geometries[i]
        cam = cameras[i]
        
        # Get geometry transform
        geom_matrix = geom.matrix_world
        geom_pos = Vector(geom_matrix.translation)
        geom_rot = geom_matrix.to_3x3()
        
        # Get camera object transform
        cam_pos = Vector(cam.location)
        cam_rot = cam.matrix_world.to_3x3()
        
        # Calculate differences
        pos_diff = (geom_pos - cam_pos).length
        rot_diff_matrix = geom_rot @ cam_rot.transposed()
        rot_diff_angle = rot_diff_matrix.to_euler()
        rot_diff_angle_deg = math.degrees(max(abs(rot_diff_angle.x), abs(rot_diff_angle.y), abs(rot_diff_angle.z)))
        
        print(f"\nCamera {i}:")
        print(f"  Geometry: {geom.name}")
        print(f"  Camera Object: {cam.name}")
        print(f"  Position difference: {pos_diff:.6f}")
        print(f"  Rotation difference: {rot_diff_angle_deg:.2f} degrees")
        print(f"  Geometry position: ({geom_pos.x:.4f}, {geom_pos.y:.4f}, {geom_pos.z:.4f})")
        print(f"  Camera position:   ({cam_pos.x:.4f}, {cam_pos.y:.4f}, {cam_pos.z:.4f})")
        
        # Analyze transformation matrices
        print(f"\n  Geometry matrix_world:")
        for row in geom_matrix:
            print(f"    [{row[0]:8.4f} {row[1]:8.4f} {row[2]:8.4f} {row[3]:8.4f}]")
        
        print(f"\n  Camera matrix_world:")
        for row in cam.matrix_world:
            print(f"    [{row[0]:8.4f} {row[1]:8.4f} {row[2]:8.4f} {row[3]:8.4f}]")
        
        # Calculate what transformation would match
        if i == 0:
            print(f"\n  Transformation analysis:")
            # What transform would convert cam to geom?
            T_cam_to_geom = geom_matrix @ cam.matrix_world.inverted()
            print(f"  Transform from camera to geometry:")
            for row in T_cam_to_geom:
                print(f"    [{row[0]:8.4f} {row[1]:8.4f} {row[2]:8.4f} {row[3]:8.4f}]")
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)

# ============================================================================
# RUN SCRIPT
# ============================================================================

if __name__ == "__main__":
    analyze_differences()
