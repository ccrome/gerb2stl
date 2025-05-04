import subprocess
import logging
from pathlib import Path
import logging
import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, "svg2scad"))

import svg2scad as svg2scad

def gerber_to_svg(
        gerber_path,
        svg_path):
    cmd = ["gerbv",
           "-x", "svg",
           "-o", svg_path,
           gerber_path
           ]
    logging.info(f"running {' '.join(cmd)}")
    e = subprocess.run(cmd, check=True, capture_output=True, cwd="svg2scad")
    logging.info(f"results: {e}")

def svg_to_stl(
        svg_path,
        output_path,
        center_page=False,
        tolerance=0.1,
        name="svg",
        colors=False,
        no_polygons=False,
        align="center",
):
    """
    Dummy implementation. Replace this with actual logic:
    - Parse Svg
    - Generate OpenSCAD
    - Call OpenSCAD CLI to output STL
    """
    svg_path_p = Path(svg_path)
    if not svg_path_p.exists():
        logging.error(f"path {svg_path} does not exist for some reason.... ")
        return

    logging.info(f"converting {svg_path} to {output_path}")

    scad_path = f"{svg_path}.scad"

    cmd = ["python", "svg2scad.py",
           "-o",  scad_path,
           svg_path
           ]
    logging.info(f"running {' '.join(cmd)}")
    e = subprocess.run(cmd, check=True, capture_output=True, cwd="svg2scad")
    logging.info(f"results: {e}")
    
    cmd = ["openscad", "-o", output_path, scad_path]
    logging.info(f'Running {" ".join(cmd)}')
    
    e = subprocess.run(cmd, check=True, capture_output=True)
    
    if Path(output_path).exists():
        logging.info(f"Successfully created {output_path}")
    else:

        logging.error(f"did not create {output_path}.  The error from subprocess.run was {e}")
