using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

namespace RevitCivilConnector.services
{
    public static class PatternGenService
    {
        public static FillPattern CreateFillPattern(PatternConfig config)
        {
            // Create Target
            FillPatternTarget target = config.IsModelPattern ? FillPatternTarget.Model : FillPatternTarget.Drafting;
            FillPattern fp = new FillPattern(config.Name, target, FillPatternHostOrientation.ToView); 

            List<FillGrid> grids = new List<FillGrid>();
            
            double w = config.TileWidth;
            double h = config.TileHeight;

            foreach (var line in config.Lines)
            {
                double dx = line.End.X - line.Start.X;
                double dy = line.End.Y - line.Start.Y;
                double len = Math.Sqrt(dx * dx + dy * dy);
                if (len < 0.000001) continue;

                double angle = Math.Atan2(dy, dx);
                // Normalized Tangent
                double tx = dx / len;
                double ty = dy / len;
                // Normalized Normal (-y, x)
                double nx = -ty;
                double ny = tx;

                // Candidate Vectors for Tile Repetition
                List<UV> candidates = new List<UV>
                {
                    new UV(w, 0),
                    new UV(0, h),
                    new UV(w, h),
                    new UV(-w, h)
                };

                // 1. Find Transverse Vector (Normal - determines spacing between lines)
                UV vTrans = null;
                double minNormalProj = double.MaxValue;

                foreach(var v in candidates)
                {
                    double projN = Math.Abs(v.U * nx + v.V * ny);
                    if (projN > 0.000001 && projN < minNormalProj)
                    {
                        minNormalProj = projN;
                        vTrans = v;
                    }
                }

                if (vTrans == null) vTrans = new UV(w, 0); 

                double offset = vTrans.U * nx + vTrans.V * ny;
                double shift = vTrans.U * tx + vTrans.V * ty;
                
                if (offset < 0)
                {
                    // Ensure Offset positive by flipping generator logic if needed
                    // Actually, PAT format uses Absolute offset, but Shift depends on direction
                    // If offset is negative, we just flip sign.
                    // But Shift must correspond to the SAME vector.
                    // If Offset comes from V, and dot product is negative, then vector separates lines in opposite direction.
                    // Distance is abs().
                    // Shift is V dot Tangent. 
                    // If we use 'abs(offset)', we are effectively using V or -V depending on which points 'up'.
                    // If V dot N < 0, we use -V. Then Offset > 0. And Shift = (-V) dot T.
                    offset = -offset;
                    shift = -shift;
                }

                // 2. Find Longitudinal Vector (Tangent - determines repetition along the line)
                UV vLong = null;
                double bestLongProj = double.MaxValue;
                double minLongNormalProj = double.MaxValue;

                foreach (var v in candidates)
                {
                    double projN = Math.Abs(v.U * nx + v.V * ny);
                    double projT = Math.Abs(v.U * tx + v.V * ty);

                    // We want projN to be close to 0 (Parallel).
                    if (projN < 0.001)
                    {
                         if(projT > 0.001)
                         {
                             // Pick smallest repetition that fits?
                             if(projT < bestLongProj)
                             {
                                 bestLongProj = projT;
                                 vLong = v;
                             }
                         }
                    }
                }
                
                // Segments
                List<double> segments = new List<double>();
               
                if (vLong != null)
                {
                    // Found a valid repeat along the line
                    double period = Math.Abs(vLong.U * tx + vLong.V * ty);
                    
                    // Dash = len. Space = Period - len.
                    double space = -(period - len);
                    if (space > -0.000001) space = -0.000001; // Avoid 0 space?
                    
                    segments.Add(len);
                    segments.Add(space);
                }
                else
                {
                    // No parallel repeat vector found.
                    // Treat as line with large spacing? Or Infinite?
                    // User drew a SEGMENT. If no repeat along line, it shouldn't allow infinite.
                    // We use the "Single Blip" hack.
                    // Space = -10000 (Very large gap).
                    segments.Add(len);
                    segments.Add(-10000.0);
                }
                
                // Construct FillGrid
                FillGrid fg = new FillGrid();
                fg.Angle = angle;
                fg.Origin = new UV(line.Start.X, line.Start.Y);
                fg.Offset = offset;
                fg.Shift = shift;
                fg.SetSegments(segments);

                grids.Add(fg);
            }

            fp.SetFillGrids(grids);
            
            return fp;
        }
    }
}
