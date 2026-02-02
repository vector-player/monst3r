"""
Blender Script to Extract Camera Transforms from GLB Geometry

This script extracts the matrix_world transforms from camera cone geometries
in the imported GLB file. These transforms serve as ground truth for comparison
with computed transforms.

Usage:
1. Import GLB file into Blender (File → Import → glTF 2.0)
2. Open Blender Scripting workspace
3. Open this script: File → Open → select this script
4. Run the script (Alt+P or click Run button)

The script will:
- Find camera cone geometries in imported GLB
- Extract matrix_world for each camera geometry
- Extract position (cone tip) and orientation
- Save transforms to JSON file: glb_camera_transforms.json
"""

import bpy
import bmesh
import json
import os
from mathutils import Vector, Matrix, Quaternion, Euler
import math
import re

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_FILE = "glb_camera_transforms.json"  # Output JSON file path
CONE_VERTEX_COUNT_THRESHOLD = 50  # Maximum vertices for a cone mesh

# ============================================================================
# GEOMETRY ANALYSIS FUNCTIONS
# ============================================================================

def is_camera_cone(mesh_obj):
    """Check if a mesh object is a camera cone geometry"""
    if mesh_obj.type != 'MESH':
        return False
    
    mesh = mesh_obj.data
    if len(mesh.vertices) > CONE_VERTEX_COUNT_THRESHOLD:
        return False
    
    # Check if it looks like a cone (has a vertex with many edges)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    
    # Find vertex with most edges (likely the tip)
    max_edges = 0
    for vert in bm.verts:
        edge_count = len(vert.link_edges)
        if edge_count > max_edges:
            max_edges = edge_count
    
    bm.free()
    
    # Camera cones typically have a tip with 4+ edges
    return max_edges >= 4

def extract_camera_info_from_cone(cone_obj):
    """Extract camera position and orientation from cone geometry
    
    Returns:
        dict with keys: position, rotation_quaternion, rotation_euler, matrix_world
    """
    mesh = cone_obj.data
    world_matrix = cone_obj.matrix_world
    
    # Get vertices in world space
    vertices_world = [world_matrix @ Vector(v.co) for v in mesh.vertices]
    
    # Find tip vertex (vertex farthest from centroid)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    
    # Calculate centroid
    centroid = Vector([0, 0, 0])
    for vert in bm.verts:
        centroid += Vector(vert.co)
    centroid /= len(bm.verts)
    
    # Find tip (vertex farthest from centroid)
    tip_local = None
    max_distance = 0
    for vert in bm.verts:
        dist = (Vector(vert.co) - centroid).length
        if dist > max_distance:
            max_distance = dist
            tip_local = Vector(vert.co)
    
    # Transform tip to world space (this is the camera center)
    tip_world = world_matrix @ tip_local
    
    # Extract rotation from matrix_world
    rotation_matrix = world_matrix.to_3x3()
    rotation_quat = rotation_matrix.to_quaternion()
    rotation_euler = rotation_matrix.to_euler('XYZ')
    
    bm.free()
    
    return {
        'name': cone_obj.name,
        'position': [tip_world.x, tip_world.y, tip_world.z],
        'rotation_quaternion': [rotation_quat.w, rotation_quat.x, rotation_quat.y, rotation_quat.z],
        'rotation_euler': [rotation_euler.x, rotation_euler.y, rotation_euler.z],
        'matrix_world': [[world_matrix[i][j] for j in range(4)] for i in range(4)],
        'matrix_world_3x3': [[rotation_matrix[i][j] for j in range(3)] for i in range(3)],
        'location': [cone_obj.location.x, cone_obj.location.y, cone_obj.location.z],
        'scale': [cone_obj.scale.x, cone_obj.scale.y, cone_obj.scale.z],
    }

def extract_number_from_name(name):
    """Extract number from object name for sorting"""
    match = re.search(r'\d+', name)
    if match:
        return int(match.group())
    return 0

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def extract_glb_camera_transforms():
    """Extract matrix_world transforms from GLB camera geometries"""
    print("=" * 60)
    print("Extracting Camera Transforms from GLB Geometry")
    print("=" * 60)
    
    # Find camera geometry objects (from GLB import)
    camera_geometries = []
    for obj in bpy.data.objects:
        if is_camera_cone(obj):
            camera_geometries.append(obj)
    
    print(f"Found {len(camera_geometries)} camera geometry objects")
    
    if len(camera_geometries) == 0:
        print("ERROR: No camera geometry found. Make sure GLB file is imported.")
        return None
    
    # Sort cameras by name (try to extract numbers)
    camera_geometries.sort(key=lambda x: extract_number_from_name(x.name))
    
    # Extract transforms
    transforms = []
    for i, geom_obj in enumerate(camera_geometries):
        print(f"Processing camera {i+1}/{len(camera_geometries)}: {geom_obj.name}")
        camera_info = extract_camera_info_from_cone(geom_obj)
        camera_info['index'] = i
        transforms.append(camera_info)
    
    # Save to JSON
    output_path = os.path.join(os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.getcwd(), OUTPUT_FILE)
    with open(output_path, 'w') as f:
        json.dump({
            'num_cameras': len(transforms),
            'transforms': transforms,
            'source': 'GLB geometry (ground truth)',
        }, f, indent=2)
    
    print(f"\nSaved {len(transforms)} camera transforms to: {output_path}")
    print(f"Output file: {output_path}")
    
    # Print summary
    print("\nSummary:")
    print(f"  Total cameras: {len(transforms)}")
    if transforms:
        first = transforms[0]
        print(f"  First camera: {first['name']}")
        print(f"    Position: [{first['position'][0]:.6f}, {first['position'][1]:.6f}, {first['position'][2]:.6f}]")
        print(f"    Rotation (quat): [{first['rotation_quaternion'][0]:.6f}, {first['rotation_quaternion'][1]:.6f}, {first['rotation_quaternion'][2]:.6f}, {first['rotation_quaternion'][3]:.6f}]")
    
    return transforms

if __name__ == "__main__":
    extract_glb_camera_transforms()
