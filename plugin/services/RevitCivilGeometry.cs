using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.Models;

namespace RevitCivilConnector.Services
{
    public class RevitCivilGeometry
    {
        private UIApplication _uiApp;

        public RevitCivilGeometry(UIApplication uiApp)
        {
            _uiApp = uiApp;
        }

        public void CreateGeometry(List<CivilElement> elements, bool useSharedCoordinates)
        {
            Document doc = _uiApp.ActiveUIDocument.Document;

            using (Transaction t = new Transaction(doc, "Import Civil Data"))
            {
                t.Start();

                foreach (var el in elements)
                {
                    if (!el.IsSelected) continue;

                    if (el is CivilSurface surf)
                    {
                        CreateSurface(doc, surf, useSharedCoordinates);
                    }
                    else if (el is CivilAlignment align)
                    {
                        CreateAlignment(doc, align, useSharedCoordinates);
                    }
                }

                t.Commit();
            }
        }

        private void CreateSurface(Document doc, CivilSurface surface, bool shared)
        {
            try
            {
                // Robust Mesh Builder
                TessellatedShapeBuilder builder = new TessellatedShapeBuilder();
                builder.OpenConnectedFaceSet(true);

                // Transform setup
                Transform transform = Transform.Identity;
                if (shared)
                {
                   // LandXML coords are usually "Global/Shared". 
                   // Revit Internal = Inverse(SharedTransform) * Global
                   ProjectLocation loc = doc.ActiveProjectLocation;
                   if (loc != null)
                   {
                       // This transform converts Internal -> Shared
                       Transform internalToShared = loc.GetTotalTransform();
                       transform = internalToShared.Inverse;
                   }
                }

                List<XYZ> vertices = new List<XYZ>(3);
                foreach (var face in surface.Faces)
                {
                    if (face.Count != 3) continue;

                    vertices.Clear();
                    foreach (var pt in face)
                    {
                        XYZ raw = new XYZ(pt.X, pt.Y, pt.Z);
                        // Convert units if needed (LandXML usually meters? metric templates?)
                        // Revit internal is Feet. 
                        // Assuming LandXML is Metric (Meters).
                        // 1m = 3.28084 ft
                        raw = raw * 3.2808399; 
                        
                        if (shared) raw = transform.OfPoint(raw);
                        vertices.Add(raw);
                    }
                    
                    // Create Tessellated Face
                    builder.AddFace(new TessellatedFace(vertices, ElementId.InvalidElementId));
                }

                builder.CloseConnectedFaceSet();
                
                // Build
                builder.Target = TessellatedShapeBuilderTarget.Mesh;
                builder.Fallback = TessellatedShapeBuilderFallback.Salvage;
                builder.Build();
                
                TessellatedShapeBuilderResult result = builder.GetBuildResult();
                
                // DirectShape
                DirectShape ds = DirectShape.CreateElement(doc, new ElementId(BuiltInCategory.OST_Topography));
                ds.SetShape(result.GetGeometricalObjects());
                ds.Name = surface.Name;
            }
            catch (Exception ex)
            {
                // Robust: Don't crash entire import, just log/skip
                 System.Diagnostics.Debug.WriteLine($"Error creating surface {surface.Name}: {ex.Message}");
            }
        }

        private void CreateAlignment(Document doc, CivilAlignment align, bool shared)
        {
            try 
            {
                 if (align.Points.Count < 2) return;
                 
                 Transform transform = Transform.Identity;
                 if (shared)
                 {
                      ProjectLocation loc = doc.ActiveProjectLocation;
                      if (loc != null) transform = loc.GetTotalTransform().Inverse;
                 }

                 List<GeometryObject> curves = new List<GeometryObject>();
                 
                 for(int i=0; i < align.Points.Count - 1; i++)
                 {
                     var p1 = align.Points[i];
                     var p2 = align.Points[i+1];
                     
                     XYZ start = new XYZ(p1.X, p1.Y, p1.Z) * 3.2808399;
                     XYZ end = new XYZ(p2.X, p2.Y, p2.Z) * 3.2808399;
                     
                     if (shared)
                     {
                         start = transform.OfPoint(start);
                         end = transform.OfPoint(end);
                     }
                     
                     if (start.IsAlmostEqualTo(end)) continue;
                     
                     curves.Add(Line.CreateBound(start, end));
                 }
                 
                 if (curves.Count > 0)
                 {
                     DirectShape ds = DirectShape.CreateElement(doc, new ElementId(BuiltInCategory.OST_GenericModel)); // Roads?
                     ds.SetShape(curves);
                     ds.Name = align.Name;
                 }
            }
            catch (Exception ex)
            {
                 System.Diagnostics.Debug.WriteLine($"Error creating alignment {align.Name}: {ex.Message}");
            }
        }
    }
}
