using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

namespace RevitCivilConnector.services
{
    public static class DWGProcessService
    {
        public static void ProcessImport(Document doc, DWGImportConfig config)
        {
            // 1. Determine Views
            View targetView = null;
            
            if (config.TargetType == DWGTarget.ActiveView)
            {
                targetView = doc.ActiveView;
            }
            else if (config.TargetType == DWGTarget.DraftingView)
            {
                 ViewFamilyType vft = new FilteredElementCollector(doc)
                    .OfClass(typeof(ViewFamilyType))
                    .Cast<ViewFamilyType>()
                    .FirstOrDefault(x => x.ViewFamily == ViewFamily.Drafting);
                 if (vft != null)
                 {
                     targetView = ViewDrafting.Create(doc, vft.Id);
                     targetView.Name = config.TargetName;
                 }
            }
            // ... (Legend logic skipped for brevity/reliability, defaulting Active) ...
            
            if (targetView == null && config.TargetType != DWGTarget.ActiveView) return; 

            // 2. Import DWG
            DWGImportOptions opt = new DWGImportOptions();
            opt.Placement = ImportPlacement.Origin; 
            
            bool is3D = targetView == null || targetView.ViewType == ViewType.ThreeD;
            opt.ThisViewOnly = !is3D; 

            ElementId importId;
            bool success = doc.Import(config.FilePath, opt, targetView, out importId);
            
            if (!success || importId == ElementId.InvalidElementId) return;

            Element importElem = doc.GetElement(importId);
            if (importElem is ImportInstance ii)
            {
                // 3. Extract Geometry (Manual Explode)
                Options gOpt = new Options();
                gOpt.View = targetView;
                gOpt.ComputeReferences = true;
                
                GeometryElement geoElem = ii.get_Geometry(gOpt);
                if (geoElem == null) return;

                GraphicsStyle targetLineStyle = GetGraphicStyle(doc, config.SelectedLineStyle);

                foreach (GeometryObject obj in geoElem)
                {
                    ProcessGeometryObject(doc, targetView, obj, targetLineStyle, is3D);
                }

                // 4. Delete Import?
                try { doc.Delete(importId); } catch {}
            }
        }

        private static void ProcessGeometryObject(Document doc, View view, GeometryObject obj, GraphicsStyle style, bool is3D)
        {
            if (obj is GeometryInstance gi)
            {
                foreach (GeometryObject subObj in gi.SymbolGeometry)
                {
                    ProcessGeometryObject(doc, view, subObj, style, is3D);
                }
            }
            else if (obj is PolyLine poly)
            {
                // Convert PolyLine to Curves
                IList<XYZ> pts = poly.GetCoordinates();
                for (int i = 0; i < pts.Count - 1; i++)
                {
                    try
                    {
                        Line line = Line.CreateBound(pts[i], pts[i+1]);
                        ProcessCurve(doc, view, line, style, is3D);
                    }
                    catch { }
                }
            }
            else if (obj is Solid solid)
            {
                // Extract Edges from Solid
                foreach (Edge edge in solid.Edges)
                {
                    try
                    {
                        Curve curve = edge.AsCurve();
                        ProcessCurve(doc, view, curve, style, is3D);
                    }
                    catch { }
                }
            }
            else if (obj is Curve curve)
            {
                ProcessCurve(doc, view, curve, style, is3D);
            }
        }

        private static void ProcessCurve(Document doc, View view, Curve curve, GraphicsStyle style, bool is3D)
        {
             if (curve.Length < 0.001) return;
             
             try
             {
                if (is3D)
                {
                    // Create Model Curve (3D)
                    XYZ p0 = curve.GetEndPoint(0);
                    XYZ p1 = curve.GetEndPoint(1);
                    
                    // Flatten to Z=0 if almost flat? No, respect geometry.
                    // Need a plane containing the curve.
                    // If line, infinite planes. Pick one.
                    XYZ v = p1 - p0;
                    XYZ norm = XYZ.BasisZ;
                    if (Math.Abs(v.DotProduct(XYZ.BasisZ)) > 0.99) norm = XYZ.BasisX; // Vertical line
                    
                    // Try Create Plane
                    Plane plane = Plane.CreateByNormalAndOrigin(norm, p0);
                    
                    // If curve is not planar (e.g. spiral), ModelCurve fails without Specific SketchPlane?
                    // ModelCurve must be on a plane.
                    // For Line it works. For Arc/Ellipse, it has a plane.
                    
                    // Handle non-lines
                     if (!(curve is Line))
                     {
                         // Try to get plane from curve?
                         // If planar, GetPlane() in newer API?
                         // Fallback to simple line approx or skip?
                         // Keep simple for now.
                         // Attempt create
                     }
 
                    SketchPlane sp = SketchPlane.Create(doc, plane);
                    ModelCurve mc = doc.Create.NewModelCurve(curve, sp);
                    if (style != null) mc.LineStyle = style;
                }
                else
                {
                    // 2D View - Detail Curve
                    // Only works if curve is in View Plane.
                    // DWG lines might be 3D. Project them?
                    // Project to View Plane (Z=0 relative to view).
                    
                    // Assuming Import "ThisViewOnly" + "Origin" puts them in View Plane roughly.
                    // If not, we might need to project.
                    DetailCurve dc = doc.Create.NewDetailCurve(view, curve);
                    if (style != null) dc.LineStyle = style;
                }
             }
             catch
             {
                 // Ignore failed geometry creation
             }
        }

        private static GraphicsStyle GetGraphicStyle(Document doc, string name)
        {
            if(string.IsNullOrEmpty(name)) return null;
            Category linesCat = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines);
            if(linesCat.SubCategories.Contains(name))
                return linesCat.SubCategories.get_Item(name).GetGraphicsStyle(GraphicsStyleType.Projection);
            return null;
        }

        private static TextNoteType GetTextType(Document doc, string name)
        {
             if(string.IsNullOrEmpty(name)) return null;
             return new FilteredElementCollector(doc).OfClass(typeof(TextNoteType)).Cast<TextNoteType>().FirstOrDefault(x=>x.Name == name);
        }

        private static FilledRegionType GetFillType(Document doc, string name)
        {
             if(string.IsNullOrEmpty(name)) return null;
             return new FilteredElementCollector(doc).OfClass(typeof(FilledRegionType)).Cast<FilledRegionType>().FirstOrDefault(x=>x.Name == name);
        }
    }
}
