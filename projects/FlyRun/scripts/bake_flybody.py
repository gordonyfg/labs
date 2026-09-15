#!/usr/bin/env python3
"""
bake_flybody.py — Converts and optimizes the official DeepMind / Janelia fruitfly meshes
from TuragaLab/flybody into web-ready Three.js assets for FlyRun.
"""

import os
import sys
import json
import base64
import time
import numpy as np
import trimesh

CACHE_DIR = '/home/gordon-yeung/projects/FlyRun/data/flybody_raw'
OUT_DIR = '/home/gordon-yeung/projects/FlyRun/sim/web_runner'

# Coordinate transform center: center of thorax in flybody rest pose
X0, Y0, Z0 = -0.07, 0.0, 1.185

def to_three_coords(verts):
    """
    Transforms flybody coordinates to Three.js runner space:
      Three.js X (lateral)     = flybody Y - Y0
      Three.js Y (dorsal/up)   = flybody Z - Z0
      Three.js Z (forward/aft) = flybody X - X0
    """
    out = np.zeros_like(verts, dtype=np.float32)
    out[:, 0] = verts[:, 1] - Y0
    out[:, 1] = verts[:, 2] - Z0
    out[:, 2] = verts[:, 0] - X0
    return out

# Group mapping
GROUPS = {
    'body_chitin': [
        'thorax_body.obj', 'head_body.obj', 'rostrum_body.obj', 'haustellum_body.obj',
        'antenna_left_body.obj', 'antenna_right_body.obj',
        # Alternating amber tergites (T1, T3, T5)
        'abdomen_1_body.obj', 'abdomen_3_body.obj', 'abdomen_5_body.obj',
        # 6 articulated legs
        'coxa_T1_left_body.obj', 'femur_T1_left_body.obj', 'tibia_T1_left_body.obj',
        'tarsus_T1_1_left_body.obj', 'tarsus_T1_2_left_body.obj', 'tarsus_T1_3_left_body.obj',
        'coxa_T1_right_body.obj', 'femur_T1_right_body.obj', 'tibia_T1_right_body.obj',
        'tarsus_T1_1_right_body.obj', 'tarsus_T1_2_right_body.obj', 'tarsus_T1_3_right_body.obj',
        'coxa_T2_left_body.obj', 'femur_T2_left_body.obj', 'tibia_T2_left_body.obj',
        'tarsus_T2_1_left_body.obj', 'tarsus_T2_2_left_body.obj', 'tarsus_T2_3_left_body.obj',
        'coxa_T2_right_body.obj', 'femur_T2_right_body.obj', 'tibia_T2_right_body.obj',
        'tarsus_T2_1_right_body.obj', 'tarsus_T2_2_right_body.obj', 'tarsus_T2_3_right_body.obj',
        'coxa_T3_left_body.obj', 'femur_T3_left_body.obj', 'tibia_T3_left_body.obj',
        'tarsus_T3_1_left_body.obj', 'tarsus_T3_2_left_body.obj', 'tarsus_T3_3_left_body.obj',
        'coxa_T3_right_body.obj', 'femur_T3_right_body.obj', 'tibia_T3_right_body.obj',
        'tarsus_T3_1_right_body.obj', 'tarsus_T3_2_right_body.obj', 'tarsus_T3_3_right_body.obj',
    ],
    'body_abdomen_dark': [
        # Drosophila melanogaster distinctive dark abdominal bands & posterior tip
        'abdomen_2_body.obj', 'abdomen_4_body.obj', 'abdomen_6_body.obj',
        'abdomen_7_body.obj', 'abdomen_8_body.obj'
    ],
    'body_black': [
        'thorax_black.obj', 'head_black.obj', 'haustellum_black.obj',
        'antenna_left_black.obj', 'antenna_right_black.obj'
    ],
    'body_eyes': [
        'head_red.obj'
    ],
    'body_ocelli': [
        'head_ocelli.obj'
    ],
    'body_ventral': [
        'labrum_left_lower.obj', 'labrum_right_lower.obj',
        'abdomen_1_lower.obj', 'abdomen_2_lower.obj', 'abdomen_3_lower.obj', 'abdomen_4_lower.obj',
        'abdomen_5_lower.obj', 'abdomen_6_lower.obj', 'abdomen_7_lower.obj'
    ],
    'body_claws': [
        'tarsal_claw_T1_left_brown.obj', 'tarsal_claw_T1_right_brown.obj',
        'tarsal_claw_T2_left_brown.obj', 'tarsal_claw_T2_right_brown.obj',
        'tarsal_claw_T3_left_brown.obj', 'tarsal_claw_T3_right_brown.obj',
        'tarsus_T1_4_left_body.obj', 'tarsus_T1_4_right_body.obj',
        'tarsus_T2_4_left_body.obj', 'tarsus_T2_4_right_body.obj',
        'tarsus_T3_4_left_body.obj', 'tarsus_T3_4_right_body.obj',
        'rostrum_bristle-brown.obj'
    ],
    'wing_left_membrane': [
        'wing_left_membrane.obj'
    ],
    'wing_left_veins': [
        'wing_left_brown.obj'
    ],
    'wing_right_membrane': [
        'wing_right_membrane.obj'
    ],
    'wing_right_veins': [
        'wing_right_brown.obj'
    ],
    'haltere_left': [
        'haltere_left_body.obj'
    ],
    'haltere_right': [
        'haltere_right_body.obj'
    ]
}

MAX_FACES = {
    'body_chitin': 10000,
    'body_abdomen_dark': 4000,
    'body_black': 8000,
    'body_eyes': 6000,
    'body_ocelli': 800,
    'body_ventral': 4000,
    'body_claws': 4000,
    'wing_left_membrane': 1500,
    'wing_left_veins': 3000,
    'wing_right_membrane': 1500,
    'wing_right_veins': 3000,
    'haltere_left': 800,
    'haltere_right': 800
}

def main():
    t0 = time.time()
    print("=== Baking Google DeepMind / Janelia Flybody Assets for FlyRun ===")
    
    wing_left_hinge = np.array([-0.492, 0.142, 0.135], dtype=np.float32)
    wing_right_hinge = np.array([0.492, 0.142, 0.135], dtype=np.float32)
    
    haltere_left_hinge = np.array([-0.264, -0.017, 0.405], dtype=np.float32)
    haltere_right_hinge = np.array([0.264, -0.017, 0.405], dtype=np.float32)
    
    hinges = {
        'wing_left_membrane': wing_left_hinge,
        'wing_left_veins': wing_left_hinge,
        'wing_right_membrane': wing_right_hinge,
        'wing_right_veins': wing_right_hinge,
        'haltere_left': haltere_left_hinge,
        'haltere_right': haltere_right_hinge,
    }
    
    processed_meshes = {}
    
    for gname, fnames in GROUPS.items():
        loaded = []
        for fn in fnames:
            p = os.path.join(CACHE_DIR, fn)
            if not os.path.exists(p):
                print(f"Warning: {p} does not exist!")
                continue
            m = trimesh.load(p, file_type='obj')
            loaded.append(m)
            
        if not loaded:
            print(f"Error: No meshes found for {gname}")
            continue
            
        combined = trimesh.util.concatenate(loaded)
        combined.vertices = to_three_coords(combined.vertices)
        
        if gname in hinges:
            combined.vertices -= hinges[gname]
            
        max_f = MAX_FACES.get(gname, 10000)
        if len(combined.faces) > max_f:
            ratio = 1.0 - (float(max_f) / len(combined.faces))
            combined = combined.simplify_quadric_decimation(percent=ratio)
            
        combined.fix_normals()
        processed_meshes[gname] = combined
        print(f"  [{gname:<20}] {len(combined.vertices):>5} verts, {len(combined.faces):>5} faces")
        
    total_verts = sum(len(m.vertices) for m in processed_meshes.values())
    total_faces = sum(len(m.faces) for m in processed_meshes.values())
    print(f"\nTotal Fly Model: {total_verts} vertices, {total_faces} triangles")
    
    # 1. Export GLB
    scene = trimesh.Scene()
    for name, mesh in processed_meshes.items():
        m_copy = mesh.copy()
        if name in hinges:
            m_copy.vertices += hinges[name]
        scene.add_geometry(m_copy, node_name=name, geom_name=name)
        
    glb_path = os.path.join(OUT_DIR, 'flybody.glb')
    with open(glb_path, 'wb') as f:
        f.write(scene.export(file_type='glb'))
    print(f"Exported GLB: {glb_path} ({os.path.getsize(glb_path) / 1024:.1f} KB)")
    
    # 2. Export Standalone JS Data File
    js_data = {}
    for name, mesh in processed_meshes.items():
        verts = mesh.vertices.astype(np.float32).flatten()
        faces = mesh.faces.astype(np.uint16).flatten()
        normals = mesh.vertex_normals.astype(np.float32).flatten()
        
        js_data[name] = {
            'verts': base64.b64encode(verts.tobytes()).decode('ascii'),
            'faces': base64.b64encode(faces.tobytes()).decode('ascii'),
            'normals': base64.b64encode(normals.tobytes()).decode('ascii'),
            'vertCount': len(mesh.vertices),
            'faceCount': len(mesh.faces),
            'hinge': [float(x) for x in hinges.get(name, [0.0, 0.0, 0.0])]
        }
        
    js_content = f"""/**
 * flybody_data.js — Canonical DeepMind / Janelia Fruit Fly 3D Model Data
 * Extracted from TuragaLab/flybody (Google DeepMind / HHMI Janelia)
 * Encoded as compact binary base64 buffers for instant zero-latency loading.
 */
window.FLYBODY_MODEL_DATA = {json.dumps(js_data, indent=2)};
"""
    js_path = os.path.join(OUT_DIR, 'flybody_data.js')
    with open(js_path, 'w') as f:
        f.write(js_content)
    print(f"Exported JS Data: {js_path} ({os.path.getsize(js_path) / 1024:.1f} KB)")
    
    print(f"\nBake completed successfully in {time.time() - t0:.2f}s!")

if __name__ == '__main__':
    main()
