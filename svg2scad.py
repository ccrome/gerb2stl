from __future__ import division
import inflateutils.svgpath.shader as shader
import inflateutils.svgpath.parser as parser
import inflateutils.svgpath.path as svgpath
import sys
import getopt
import cmath
import math
from pathlib import Path
from inflateutils.exportmesh import *
from inflateutils.formatdecimal import decimal
from random import sample
import argparse
quiet = False

def closed(path):
    return path[-1] == path[0]
    
def inside(z, path):
    for p in path:
        if p == z:
            return False
    try:
        phases = sorted((cmath.phase(p-z) for p in path))
        # make a ray that is relatively far away from any points
        if len(phases) == 1:
            # should not happen
            bestPhase = phases[0] + math.pi
        else:    
            bestIndex = max( (phases[i+1]-phases[i],i) for i in range(len(phases)-1))[1]
            bestPhase = (phases[bestIndex+1]+phases[bestIndex])/2.
        ray = cmath.rect(1., bestPhase)
        rotatedPath = tuple((p-z) / ray for p in path)
        # now we just need to check shiftedPath's intersection with the positive real line
        s = 0
        for i,p2 in enumerate(rotatedPath):
            p1 = rotatedPath[i-1]
            if p1.imag == p2.imag:
                # horizontal lines can't intersect positive real line once phase selection was done
                continue
                # (1/m)y + xIntercept = x
            reciprocalSlope = (p2.real-p1.real)/(p2.imag-p1.imag)
            xIntercept = p2.real - reciprocalSlope * p2.imag
            if xIntercept == 0:
                return False # on boundary
            if xIntercept > 0 and p1.imag * p2.imag < 0:
                if p1.imag < 0:
                    s += 1
                else:
                    s -= 1
        return s != 0
            
    except OverflowError:
        return False
    
def nestedPaths(path1, path2, pointsToCheck=3):
    if not closed(path2):
        return False
    k = min(pointsToCheck, len(path1))
    for point in sample(path1, k):
        if inside(point, path2):
            return True
    return False
    
def comparePaths(path1,path2,pointsToCheck=3):
    """
    open paths before closed paths
    outer paths come before inner ones
    otherwise, top to bottom bounds, left to right
    """
    
    if closed(path1) and not closed(path2):
        return 1
    elif closed(path2) and not closed(path1):
        return -1
    if nestedPaths(path1, path2, pointsToCheck=pointsToCheck):
        return 1
    elif nestedPaths(path2, path1, pointsToCheck=pointsToCheck):
        return -1
    y1 = max(p.imag for p in path1)
    y2 = max(p.imag for p in path2)
    if y1 == y2:
        return comparison(min(p.real for p in path1),min(p.real for p in path2))
    else:
        return comparison(y1,y2)

def getLevels(paths):
    level = []
    empty = True
    nextPaths = paths[:]
    for i in range(len(paths)):
        path = paths[i]
        if path is None:
            continue
        empty = False
        outer = True
        if closed(path):
            for j in range(len(paths)):
                if j != i and paths[j] is not None and nestedPaths(path, paths[j]):
                    outer = False
                    break
        if outer:
            level.append(path)
            nextPaths[i] = None

    if empty:
        return []
    else:
        return [level] + getLevels(nextPaths)
        
def message(string):
    if not quiet:
        sys.stderr.write(string + "\n")
    
def sortedApproximatePaths(paths,error=0.1):
    def approximate(path):
        p = path.linearApproximation(error=error)
        p.originalPath = path
        return p
    
    paths = [approximate(path) for path in paths if len(path)]
    
    def key(path):
        top = min(min(line.start.imag,line.end.imag) for line in path)
        left = min(min(line.start.real,line.end.real) for line in path)
        return (top,left)
        
    return sorted(paths, key=key)

class SubPath(list):
    pass

class PolygonData(object):
    def __init__(self,color,fillColor):
        self.bounds = [float("inf"),float("inf"),float("-inf"),float("-inf")]
        self.color = color
        self.fillColor = fillColor
        self.pointLists = []
        
    def updateBounds(self,z):
        self.bounds[0] = min(self.bounds[0], z.real)
        self.bounds[1] = min(self.bounds[1], z.imag)
        self.bounds[2] = max(self.bounds[2], z.real)
        self.bounds[3] = max(self.bounds[3], z.imag)

    def getAnchor(self, mode):
        if mode[0] == "a":
            return 0j
        elif mode[0] == 'l':
            return complex(self.bounds[0],self.bounds[1])
        else: # mode[0] == 'c':
            return complex(0.5*(self.bounds[0]+self.bounds[2]),0.5*(self.bounds[1]+self.bounds[3]))
    
def extractPaths(paths, offset, tolerance=0.1, baseName="svg", colors=True, levels=False, absolute=False, align="center"):
    polygons = []

    paths = sortedApproximatePaths(paths, error=tolerance )
    
    for i,path in enumerate(paths):
        color = None
        fillColor = None
        if colors:
            if path.svgState.fill is not None:
                fillColor = path.svgState.fill
            if path.svgState.stroke is not None:
                color = path.svgState.stroke
        polygon = PolygonData(color,fillColor)
        polygon.strokeWidth = path.svgState.strokeWidth;
        polygons.append(polygon)
        for j,subpath0 in enumerate(path.originalPath.breakup()):
            subpath = subpath0.linearApproximation(error=tolerance)
            points = [subpath[0].start+offset]
            polygon.updateBounds(points[-1])
            for line in subpath:
                points.append(line.end+offset)
                polygon.updateBounds(points[-1])
            if subpath.closed and points[0] != points[-1]:
                points.append(points[0])
            sp = SubPath(points)
            sp.originalPath = subpath0
            polygon.pointLists.append(sp)
        if not absolute:
            for points in polygon.pointLists:
                for j in range(len(points)):
                    points[j] -= polygon.getAnchor(align)
                
        if levels:
            polygon.levels = getLevels(polygon.pointLists)
            polygon.pointLists = flattenLevels(polygon.levels)

    return polygons
    
def toNestedPolygons(levels, name, i=0, indent=4):
    def spaces():
        return ' '*indent
    out = ""
    if len(levels)>1:
        out += spaces() + "difference() {\n"
        indent += 2
    if len(levels[0])>1:
        out += spaces() + "union() {\n"
        indent += 2
    for poly in levels[0]:
        if closed(poly):
            out += spaces() + "polygon(points=%s);\n" % name(i)
        i += 1
    if len(levels[0])>1:
        indent -= 2
        out += spaces() + "}\n"
    if len(levels)>1:
        out += toNestedPolygons(levels[1:], name, i=i, indent=indent)
        indent -= 2
        out += spaces() + "}\n"
    return out
    
def flattenLevels(levels):
    out = []
    for level in levels:
        out += level
    return out

def getBezier(path,offset,cpMode):
    didBezier = False
    b = []
    
    def addCoords(t,z):
        z += offset
        b.append("/*%s*/[%s,%s]" % (t,decimal(z.real),decimal(z.imag)))
        
    def addCP(cp,node):
        if cpMode[0] == 'a':
            addCoords("CP",cp)
        else: 
            delta=cp-node
            if cpMode[0] == 'p':
                b.append("/*CP*/POLAR(%s,%s)"
                         % (decimal(abs(delta)),decimal(math.atan2(delta.imag,delta.real)*180/math.pi)))
            else:
                b.append("/*CP*/OFFSET([%s,%s])" 
                         % (decimal(delta.real),decimal(delta.imag)))
    
    def addLine(start,end):
        addCoords("N",start)
        #addCoords("CP",(2*start+end)/3)
        #addCoords("CP",end)
        b.append("LINE()")
        b.append("LINE()")

    last = None
    for p in path:
        if isinstance(p,svgpath.CubicBezier):
            addCoords("N",p.start)
            addCP(p.control1,p.start)
            addCP(p.control2,p.end)
            last = p.end
            didBezier = True
        elif isinstance(p,svgpath.Line):
            addLine(p.start,p.end)
            last = p.end
        elif isinstance(p,svgpath.QuadraticBezier):
            addCoords("N",p.start)
            addCP(p.start+(2./3)*(p.control-p.start),p.start)
            addCP(p.end+(2./3)*(p.control-p.end),p.end)
            last = p.end
            didBezier = True
        else:
            return None
        
    if last is None or not didBezier:
        return None
    
    if path.closed and last != path.point(0):
        addLine(last,path.point(0))
        last = path.point(0)

    addCoords("N",last)
    
    return ",".join(b)

def parse_args():
    parser = argparse.ArgumentParser(description="Convert SVG to OpenSCAD geometry.")
    parser.add_argument("filename", help="Input SVG file")
    parser.add_argument("--align", choices=["center", "lowerleft", "absolute"], default="center", help="Object alignment mode, default=center")
    parser.add_argument("--bezier", choices=["none", "absolute", "offset", "polar"], default="none", help="Bezier control point style, default=none")
    parser.add_argument("--tolerance", type=float, default=0.1, help="Linearization tolerance in mm, default=0.1")
    parser.add_argument("--no-ribbons", action="store_false", help="Make ribbons out of outlined paths")
    parser.add_argument("--no-polygons", action="store_false", help="Make polygons out of shaded paths")
    parser.add_argument("--width", type=float, default=0, help="Ribbon width override, default=0")
    parser.add_argument("--height", type=float, default=0.05, help="Extrusion height (0 = 2D), in mm, default=0.05")
    parser.add_argument("--no-colors", dest="colors", action="store_false", help="Omit colors from output")
    parser.add_argument("--name", default="svg", help="Base name for OpenSCAD variables/modules")
    parser.add_argument("--center-page", action="store_true", help="Put the center of the SVG at (0,0,0)")
    parser.add_argument("-o", "--output", type=Path, help="Output file to write to.")
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        print(f"{args.output} already exists.  not overwriting!")
        exit(1)
    return args

def generate_scad_code(args, polygons, offset):
    scad = ""
    if args.bezier != 'none':
        scad += "use <bezier.scad>; // download from https://www.thingiverse.com/thing:2207518\n\n"
        scad += "bezier_precision = -%s;\n" % decimal(args.tolerance)
    if args.height > 0:
        if args.no_polygons:
            scad += "polygon_height_%s = %s;\n" % (args.name, decimal(args.height))
        if args.no_ribbons:
            scad += "ribbon_height_%s = %s;\n" % (args.name, decimal(args.height))
    if args.width > 0:
        scad += "width_%s = %s;\n" % (args.name, decimal(args.width))
    if len(scad):
        scad += "\n"

    def polyName(i): return args.name + "_" + str(i + 1)
    def subpathName(i, j): return polyName(i) + "_" + str(j + 1)

    for i, polygon in enumerate(polygons):
        if args.align[0] != 'a':
            scad += "position_%s = [%s,%s];\n" % (polyName(i), decimal(polygon.getAnchor(args.align).real), decimal(polygon.getAnchor(args.align).imag))
        scad += "size_%s = [%s,%s];\n" % (polyName(i), decimal(polygon.bounds[2]-polygon.bounds[0]), decimal(polygon.bounds[3]-polygon.bounds[1]))
        scad += "stroke_width_%s = %s;\n" % (polyName(i), decimal(polygon.strokeWidth))
        if args.colors:
            scad += "color_%s = %s;\n" % (polyName(i), describeColor(polygon.color))
            scad += "fillcolor_%s = %s;\n" % (polyName(i), describeColor(polygon.fillColor))

    for i, polygon in enumerate(polygons):
        scad += "// paths for %s\n" % polyName(i)
        for j, points in enumerate(polygon.pointLists):
            scad += "points_" + subpathName(i, j) + " = "
            b = args.bezier != 'none' and getBezier(points.originalPath, -polygon.getAnchor(args.align), args.bezier)
            if b:
                scad += "Bezier([" + b + "],precision=bezier_precision);"
            else:
                scad += "[ " + ','.join('[%s,%s]' % (decimal(point.real), decimal(point.imag)) for point in points) + " ];\n"
        scad += "\n"

    objectNames = []
    if args.no_ribbons:
        scad += """module ribbon(points, thickness=1) {
    p = points;
    union() {
        for (i=[1:len(p)-1]) {
            hull() {
                translate(p[i-1]) circle(d=thickness, $fn=8);
                translate(p[i]) circle(d=thickness, $fn=8);
            }
        }
    }
}

"""
        objectNames.append("ribbon")
        for i, polygon in enumerate(polygons):
            scad += "module ribbon_%s(width=%s) {\n" % (polyName(i), ("width_" + args.name) if args.width else ("stroke_width_" + polyName(i)))
            for j in range(len(polygon.pointLists)):
                scad += "  ribbon(points_%s, thickness=width);\n" % subpathName(i, j)
            scad += "}\n\n"

    if args.no_polygons:
        objectNames.append("polygon")
        for i, polygon in enumerate(polygons):
            scad += "module polygon_%s() {\n render(convexity=4) {\n" % polyName(i)
            scad += toNestedPolygons(polygon.levels, lambda j: "points_" + subpathName(i, j))
            scad += " }\n}\n\n"

    if args.height > 0:
        polygonExtrude = "linear_extrude(height=polygon_height_%s) " % args.name
        ribbonExtrude = "linear_extrude(height=ribbon_height_%s) " % args.name
    else:
        polygonExtrude = ribbonExtrude = ""

    for objectName in objectNames:
        for i in range(len(polygons)):
            c = "" if not args.colors else "//"
            if args.colors and objectName == 'polygon' and polygons[i].fillColor:
                c = "color(fillcolor_%s) " % polyName(i)
            elif args.colors and objectName == 'ribbon' and polygons[i].color:
                c = "color(color_%s) " % polyName(i)
            translate = "" if args.align[0] == 'a' else "translate(position_%s) " % polyName(i)
            extrude = polygonExtrude if objectName == 'polygon' else ribbonExtrude
            scad += c + extrude + translate + "%s_%s();\n" % (objectName, polyName(i))

    return scad

def main():
    args = parse_args()
    paths, lowerLeft, upperRight = parser.getPathsFromSVGFile(args.filename)
    offset = -0.5 * (lowerLeft + upperRight) if args.center_page else 0
    polygons = extractPaths(paths, offset, tolerance=args.tolerance, baseName=args.name,
                            colors=args.colors, levels=args.no_polygons, align=args.align)
    scad = generate_scad_code(args, polygons, offset)
    if args.output is None:
        print(scad)
    else:
        with args.output.open('w') as f:
            f.write(scad)

if __name__ == '__main__':
    main()
