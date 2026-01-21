using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

namespace RevitCivilConnector.services
{
    public static class VegetationScatterService
    {
        public static void ScatterVegetation(Document doc, List<Curve> boundaryLoop, VegetationScatterConfig config)
        {
            // 1. Calculate Bounding Box
            XYZ min = new XYZ(double.MaxValue, double.MaxValue, double.MaxValue);
            XYZ max = new XYZ(double.MinValue, double.MinValue, double.MinValue);
            
            // Assume planar loop roughly. We use XY for inclusion. Z from average?
            // Or assume lines are at correct Z.
            // We'll perform inclusion in 2D (XY).
            
            double sumZ = 0;
            int pts = 0;

            foreach(Curve c in boundaryLoop)
            {
                // Sampling points for bbox
                XYZ p0 = c.GetEndPoint(0);
                XYZ p1 = c.GetEndPoint(1);
                UpdateMinMax(p0, ref min, ref max);
                UpdateMinMax(p1, ref min, ref max);
                sumZ += p0.Z + p1.Z;
                pts += 2;
            }
            
            double avgZ = (pts > 0) ? sumZ / pts : 0;
            
            // 2. Determine Count
            int itemsToPlace = 0;
            if (config.UseFixedCount)
            {
                itemsToPlace = config.TotalCount;
            }
            else
            {
                // Calc Area (Approx via BBox or exact Polygon Area?)
                // Simple: Box Area? No. Polygon Area.
                double area = CalculatePolygonAreaXY(boundaryLoop);
                // Spacing S -> Area per item = S*S.
                double itemArea = config.Spacing * config.Spacing; // (Meters * Meters assuming internal units match?)
                // Wait, config.Spacing is usually Meters.
                // boundaryLoop is in Internal Units (Feet).
                // Config Spacing input was "2.0" (Meters).
                
                double spacingFt = UnitUtils.ConvertToInternalUnits(config.Spacing, UnitTypeId.Meters);
                double itemAreaFt = spacingFt * spacingFt;
                
                if (itemAreaFt < 0.001) itemAreaFt = 1.0;
                itemsToPlace = (int)(area / itemAreaFt);
            }
            
            if (itemsToPlace < 1) return;
            if (itemsToPlace > 5000) itemsToPlace = 5000; // Safety limit

            Random rnd = new Random();
            List<XYZ> validPoints = new List<XYZ>();
            
            // 3. Generate Points
            // Method: Random Sampling in BBox until accepted.
            // Safety: Max iterations = 10 * needed.
            
            int needed = itemsToPlace;
            int maxIter = needed * 50; 
            int iter = 0;
            
            double boxW = max.X - min.X;
            double boxH = max.Y - min.Y;

            while (validPoints.Count < needed && iter < maxIter)
            {
                iter++;
                double rx = min.X + rnd.NextDouble() * boxW;
                double ry = min.Y + rnd.NextDouble() * boxH;
                XYZ pTest = new XYZ(rx, ry, avgZ);
                
                if (IsPointInPolygon(pTest, boundaryLoop))
                {
                    validPoints.Add(pTest);
                }
            }
            
            // 4. Place Instances
            // Ensure symbols active
            foreach(var sym in config.SelectedFamilies)
            {
                if (!sym.IsActive) sym.Activate();
            }

            foreach(XYZ p in validPoints)
            {
                // Pick random family
                FamilySymbol sym = config.SelectedFamilies[rnd.Next(config.SelectedFamilies.Count)];
                
                // Determine Z location
                XYZ location = p;
                
                // Try to find a surface using RayTracing
                View3D view3D = null;
                if (doc.ActiveView is View3D v3) view3D = v3;
                else
                {
                    view3D = new FilteredElementCollector(doc)
                        .OfClass(typeof(View3D))
                        .Cast<View3D>()
                        .FirstOrDefault(x => !x.IsTemplate);
                }

                if (view3D != null)
                {
                    try
                    {
                        List<BuiltInCategory> cats = new List<BuiltInCategory> { BuiltInCategory.OST_Topography, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs, BuiltInCategory.OST_Site };
                        ElementMulticategoryFilter filter = new ElementMulticategoryFilter(cats);
                        ReferenceIntersector ri = new ReferenceIntersector(filter, FindReferenceTarget.Element, view3D);
                        
                        // Shoot ray from high up
                        XYZ rayOrigin = new XYZ(p.X, p.Y, p.Z + 500); // 500ft up
                        XYZ rayDir = new XYZ(0,0,-1);
                        ReferenceWithContext res = ri.FindNearest(rayOrigin, rayDir);
                        
                        if (res != null)
                        {
                            location = res.GetReference().GlobalPoint;
                        }
                    }
                    catch { /* Fallback to avgZ */ }
                }

                try
                {
                    FamilyInstance fi = doc.Create.NewFamilyInstance(location, sym, Autodesk.Revit.DB.Structure.StructuralType.NonStructural);
                    
                    // Rotation
                    if (config.RandomRotation)
                    {
                        double angle = rnd.NextDouble() * 2 * Math.PI;
                        Line axis = Line.CreateBound(location, location + XYZ.BasisZ);
                        ElementTransformUtils.RotateElement(doc, fi.Id, axis, angle);
                    }
                    
                    // Scale (Height Parameter)
                    Parameter heightParam = fi.LookupParameter("Height");
                    if (heightParam != null && heightParam.IsReadOnly == false)
                    {
                         // Basic random factor assumption
                         // double sFactor = config.MinScale + rnd.NextDouble() * (config.MaxScale - config.MinScale);
                    }
                }
                catch { } // Skip failed placement
            }
        }

        private static void UpdateMinMax(XYZ p, ref XYZ min, ref XYZ max)
        {
            if (p.X < min.X) min = new XYZ(p.X, min.Y, min.Z);
            if (p.Y < min.Y) min = new XYZ(min.X, p.Y, min.Z);
            if (p.Z < min.Z) min = new XYZ(min.X, min.Y, p.Z);

            if (p.X > max.X) max = new XYZ(p.X, max.Y, max.Z);
            if (p.Y > max.Y) max = new XYZ(max.X, p.Y, max.Z);
            if (p.Z > max.Z) max = new XYZ(max.X, max.Y, p.Z);
        }

        private static bool IsPointInPolygon(XYZ p, List<Curve> loop)
        {
            // Ray Casting algorithm (Jordan Curve Theorem)
            // Ray towards X+
            int intersections = 0;
            
            foreach(Curve c in loop)
            {
                XYZ p1 = c.GetEndPoint(0);
                XYZ p2 = c.GetEndPoint(1);
                
                // check if segment straddles the ray in Y
                bool straddle = (p1.Y > p.Y) != (p2.Y > p.Y);
                
                if (straddle)
                {
                    // Compute X intersection
                    // x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                    double xInt = p1.X + (p.Y - p1.Y) * (p2.X - p1.X) / (p2.Y - p1.Y);
                    
                    if (p.X < xInt)
                    {
                        intersections++;
                    }
                }
            }
            
            return (intersections % 2) == 1;
        }
        
        private static double CalculatePolygonAreaXY(List<Curve> loop)
        {
            // Shoelace formula
            double area = 0;
            foreach(Curve c in loop)
            {
                XYZ p1 = c.GetEndPoint(0);
                XYZ p2 = c.GetEndPoint(1);
                area += (p1.X * p2.Y - p2.X * p1.Y);
            }
            return Math.Abs(area) / 2.0;
        }
    }
}
