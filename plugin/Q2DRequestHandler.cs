
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;
using RevitCivilConnector.ui;
using RevitCivilConnector.services;
using System.Globalization;

namespace RevitCivilConnector
{
    public class Q2DRequestHandler : IExternalEventHandler
    {
        private AOQuantifyWindow _window;
        public Q2DConfig Config { get; set; }

        public void SetWindow(AOQuantifyWindow win)
        {
            _window = win;
        }

        public void Execute(UIApplication app)
        {
            try
            {
                UIDocument uidoc = app.ActiveUIDocument;
                Document doc = uidoc.Document;

                if (Config.WantsToMeasure && Config.ActiveTakeoffType != null)
                {
                    Config.WantsToMeasure = false; // Consume flag

                    // HIDE Window for picking
                    if (_window != null) _window.Hide();
                    
                    try 
                    {
                        PerformMeasurement(uidoc, doc, Config.ActiveTakeoffType);
                    }
                    catch (Autodesk.Revit.Exceptions.OperationCanceledException)
                    {
                        // User cancelled
                    }
                    catch (Autodesk.Revit.Exceptions.InvalidOperationException iox)
                    {
                         TaskDialog.Show("Error de Plano de Trabajo", "Para medir en 3D, debe definir un Plano de Trabajo (Workplane) activo.\n\nDetalle: " + iox.Message);
                    }
                    catch (Exception ex)
                    {
                        TaskDialog.Show("Error", "Fallo en medición: " + ex.ToString());
                    }
                    finally
                    {
                        // SHOW Window again
                        if (_window != null) 
                        {
                            _window.Show();
                            _window.Activate();
                            // Force refresh to update subtotals
                            _window.RecalculateInventory(); 
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                TaskDialog.Show("External Event Error", ex.Message);
            }
        }

        public string GetName()
        {
            return "Q2D Request Handler";
        }

        // --- Measurement Logic ---
        private void PerformMeasurement(UIDocument uidoc, Document doc, TakeoffType type)
        {
            double MIPS = 3.28084; // Meters to Internal Units (Feet)

            // Convert Hex Color to RGB
            byte r=255, g=165, b=0; 
            try {
                System.Drawing.Color c = System.Drawing.ColorTranslator.FromHtml(type.FillColorHex);
                r = c.R; g = c.G; b = c.B;
            } catch {}

            // Loop until user ESC in the outer Tool loop (actually, we probably want single-action per click for tools?)
            // The previous logic looped "forever" until ESC.
            // For Area/Linear, one shape per "Session" is usually expected, then loop again? 
            // Users usually want to measure multiple areas.
            
            while(true)
            {
                if (type.Tool == TakeoffTool.Area)
                {
                    List<ElementId> tempLines = new List<ElementId>();
                    List<XYZ> points = PickPointsVisual(uidoc, doc, "Punto de Polígono (ESC para cerrar)", out tempLines);
                    
                    if (points.Count >= 3) 
                    {
                        using (Transaction t = new Transaction(doc, "Q2D Area"))
                        {
                            t.Start();
                            // Delete temp lines
                            if (tempLines.Any()) doc.Delete(tempLines);
                            
                            double heightM = type.DefaultHeight > 0 ? type.DefaultHeight : 0.01;
                            CreatePolygonShape(doc, points, type, MIPS, heightM, r, g, b); 
                            t.Commit();
                        }
                    }
                    else
                    {
                        // Clean up if not enough points (e.g. user cancelled early)
                        if (tempLines.Any()) 
                        {
                            using (Transaction t = new Transaction(doc, "Cleanup")) { t.Start(); doc.Delete(tempLines); t.Commit(); }
                        }
                        if (points.Count == 0) break; // Hard exit if no points (ESC on first)
                    }
                }
                else if (type.Tool == TakeoffTool.Linear)
                {
                    List<ElementId> tempLines = new List<ElementId>();
                    List<XYZ> points = PickPointsVisual(uidoc, doc, "Punto de Línea (ESC para finalizar tramo)", out tempLines);
                    
                    if (points.Count >= 2)
                    {
                        using (Transaction t = new Transaction(doc, "Q2D Linear"))
                        {
                            t.Start();
                             if (tempLines.Any()) doc.Delete(tempLines);
                            CreateLinearShape(doc, points, type, MIPS, r, g, b);
                            t.Commit();
                        }
                    }
                    else
                    {
                         if (tempLines.Any()) 
                        {
                            using (Transaction t = new Transaction(doc, "Cleanup")) { t.Start(); doc.Delete(tempLines); t.Commit(); }
                        }
                         if (points.Count == 0) break;
                    }
                }
                else if (type.Tool == TakeoffTool.Count)
                {
                    try {
                         XYZ pt = uidoc.Selection.PickPoint("Seleccione punto (ESC para finalizar).");
                         using (Transaction t = new Transaction(doc, "Q2D Count"))
                         {
                             t.Start();
                             CreateCountMarker(doc, pt, type, MIPS, r, g, b);
                             t.Commit();
                         }
                    } catch (Autodesk.Revit.Exceptions.OperationCanceledException) { break; }
                }
                else if (type.Tool == TakeoffTool.Model)
                {
                    // Batch Selection Mode
                    try {
                        // Use PickObjects for Batch Selection (Standard Revit behavior: Select Multiple -> Finish)
                        // This is much lighter than picking one by one with a transaction each time.
                        IList<Reference> refs = uidoc.Selection.PickObjects(Autodesk.Revit.UI.Selection.ObjectType.Element, "Seleccione Elementos para Cuantificar (Clic en 'Finalizar' en la barra superior al terminar)");
                        
                        if (refs.Count > 0)
                        {
                            using (Transaction t = new Transaction(doc, "Assign Takeoff Batch"))
                            {
                                t.Start();
                                foreach(var refObj in refs)
                                {
                                    Element el = doc.GetElement(refObj);
                                    if(el != null) MarkElement(el, type);
                                }
                                t.Commit();
                            }
                        }
                    } 
                    catch (Autodesk.Revit.Exceptions.OperationCanceledException) 
                    {
                        break; // Exit tool
                    } 
                }
                else 
                {
                    break;
                }
            }
        }

        private List<XYZ> PickPointsVisual(UIDocument uidoc, Document doc, string prompt, out List<ElementId> createdLines)
        {
            List<XYZ> pts = new List<XYZ>();
            createdLines = new List<ElementId>();
            
            try
            {
                while (true)
                {
                    // Prompt changes based on state
                    string p = pts.Count == 0 ? "Primer punto..." : prompt;
                    XYZ pt = uidoc.Selection.PickPoint(p);
                    
                    if (pts.Count > 0)
                    {
                        // Draw Temp Line
                        XYZ last = pts.Last();
                        if (!last.IsAlmostEqualTo(pt))
                        {
                            try 
                            {
                                using (Transaction t = new Transaction(doc, "Temp Visual"))
                                {
                                    t.Start();
                                    // Project to SketchPlane if possible, or just create ModelCurve
                                    // Ensure we have a sketch plane. If not, create one at Z of point?
                                    // Simplest: Create Linear Curve.
                                    Line l = Line.CreateBound(last, pt);
                                    Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, last);
                                    SketchPlane sp = SketchPlane.Create(doc, plane); // This might fail if plane is bad or exists
                                    // Actually, just try creating ModelCurve. API usually needs a SketchPlane active view.
                                    // Let's rely on ActiveView's SketchPlane if it exists.
                                    if (doc.ActiveView.SketchPlane == null)
                                    {
                                         doc.ActiveView.SketchPlane = sp;
                                    }
                                    
                                    ModelCurve mc = doc.Create.NewModelCurve(l, doc.ActiveView.SketchPlane);
                                    createdLines.Add(mc.Id);
                                    
                                    t.Commit();
                                }
                                uidoc.RefreshActiveView();
                            }
                            catch 
                            { 
                                // Ignore visual errors (e.g. sketch plane issues) 
                            }
                        }
                    }
                    pts.Add(pt);
                }
            }
            catch (Autodesk.Revit.Exceptions.OperationCanceledException)
            {
                // ESC stops the picking
            }
            return pts;
        }

        // --- Geometry Builders ---

        private void CreatePolygonShape(Document doc, List<XYZ> points, TakeoffType type, double MIPS, double heightM, byte r, byte g, byte b)
        {
            // Close loop
            if (!points[0].IsAlmostEqualTo(points[points.Count - 1])) points.Add(points[0]);
            
            double z = points[0].Z;
            CurveLoop loop = new CurveLoop();
            for (int i = 0; i < points.Count - 1; i++)
            {
                XYZ p1 = new XYZ(points[i].X, points[i].Y, z);
                XYZ p2 = new XYZ(points[i+1].X, points[i+1].Y, z);
                if (p1.IsAlmostEqualTo(p2)) continue;
                loop.Append(Line.CreateBound(p1, p2));
            }

            if (!loop.HasPlane()) return;

            try
            {
                double heightFt = heightM * MIPS;
                Solid solid = GeometryCreationUtilities.CreateExtrusionGeometry(new List<CurveLoop> { loop }, XYZ.BasisZ, heightFt);
                CreateDirectShape(doc, solid, type, r, g, b);
            }
            catch {}
        }

        private void CreateLinearShape(Document doc, List<XYZ> points, TakeoffType type, double MIPS, byte r, byte g, byte b)
        {
             // Create 'Pipe' or 'Wall' like shape along path
             // Thickness from Type or default 10cm?
             double thick = 0.1 * MIPS; 
             double heightFt = (type.DefaultHeight > 0 ? type.DefaultHeight : 0.2) * MIPS;

             // We can create a wall-like extrusion along the path?
             // Or just a sweep.
             // Simplest is DirectShape with SweptGeometry.
             
            CurveLoop path = new CurveLoop();
            for (int i = 0; i < points.Count - 1; i++)
            {
                if (points[i].IsAlmostEqualTo(points[i+1])) continue;
                path.Append(Line.CreateBound(points[i], points[i+1]));
            }

            // Create profile (Rectangle)
            CurveLoop profile = new CurveLoop();
            XYZ p1 = new XYZ(thick/2, heightFt/2, 0);
            XYZ p2 = new XYZ(-thick/2, heightFt/2, 0);
            XYZ p3 = new XYZ(-thick/2, -heightFt/2, 0);
            XYZ p4 = new XYZ(thick/2, -heightFt/2, 0);
            profile.Append(Line.CreateBound(p1, p2));
            profile.Append(Line.CreateBound(p2, p3));
            profile.Append(Line.CreateBound(p3, p4));
            profile.Append(Line.CreateBound(p4, p1));

            // Note: SweptGeometry is tricky with DirectShape sometimes if path is complex.
            // Let's stick to Extrusion if multiple segments? 
            // Actually, let's allow multi-segment sweep.
            
            // Wait, CreateSweptGeometry requires a path curve loop and profile curve loops.
            // It often fails if path has sharp corners > 90 deg or self intersects.
            // Safer: Create individual extrusions for each segment? No, that looks bad.
            // Let's try simple sweep, if fails, fallback?
            
            // Re-use logic from previous: Sweep logic along line is safer.
             List<GeometryObject> solids = new List<GeometryObject>();
             foreach (Curve curve in path)
             {
                 Line l = curve as Line;
                 XYZ dir = l.Direction;
                 XYZ up = XYZ.BasisZ;
                 if (Math.Abs(dir.DotProduct(up)) > 0.99) up = XYZ.BasisX;
                 XYZ right = dir.CrossProduct(up).Normalize();
                 
                  // Let's make a vertical wall shape
                  // Base center is curve start/end.
                  XYZ start = l.GetEndPoint(0);
                  XYZ end = l.GetEndPoint(1);
                  
                  // 4 points of base rect
                  XYZ c1 = start + right * thick/2;
                  XYZ c2 = start - right * thick/2;
                  XYZ c3 = end - right * thick/2;
                  XYZ c4 = end + right * thick/2;
                  
                  CurveLoop baseLoop = new CurveLoop();
                  baseLoop.Append(Line.CreateBound(c1, c2));
                  baseLoop.Append(Line.CreateBound(c2, c3));
                  baseLoop.Append(Line.CreateBound(c3, c4));
                  baseLoop.Append(Line.CreateBound(c4, c1));
                  
                  try {
                      Solid s = GeometryCreationUtilities.CreateExtrusionGeometry(new List<CurveLoop>{baseLoop}, XYZ.BasisZ, heightFt);
                      solids.Add(s);
                  } catch {}
             }
             
             if (solids.Count > 0)
             {
                CreateDirectShape(doc, solids, type, r, g, b);
             }
        }

        private void CreateCountMarker(Document doc, XYZ center, TakeoffType type, double MIPS, byte r, byte g, byte b)
        {
             double rad = (type.CountSize > 0 ? type.CountSize : 0.25) * MIPS;
             double h = 0.05 * MIPS; 
             
             CurveLoop loop = new CurveLoop();
             Plane plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, center);
             
             if (type.CountShape == "Square")
             {
                 // Square
                 XYZ p1 = center + new XYZ(rad, rad, 0);
                 XYZ p2 = center + new XYZ(-rad, rad, 0);
                 XYZ p3 = center + new XYZ(-rad, -rad, 0);
                 XYZ p4 = center + new XYZ(rad, -rad, 0);
                 loop.Append(Line.CreateBound(p1, p2));
                 loop.Append(Line.CreateBound(p2, p3));
                 loop.Append(Line.CreateBound(p3, p4));
                 loop.Append(Line.CreateBound(p4, p1));
             }
             else
             {
                 // Circle
                 loop.Append(Arc.Create(plane, rad, 0, Math.PI * 2));
             }
             
             Solid solid = GeometryCreationUtilities.CreateExtrusionGeometry(new List<CurveLoop>{loop}, XYZ.BasisZ, h);
             CreateDirectShape(doc, solid, type, r, g, b);
        }

        private void CreateDirectShape(Document doc, Solid solid, TakeoffType type, byte r, byte g, byte b)
        {
            CreateDirectShape(doc, new List<GeometryObject>{ solid }, type, r, g, b);
        }

        private void CreateDirectShape(Document doc, List<GeometryObject> geoms, TakeoffType type, byte r, byte g, byte b)
        {
             // Category: Generic Model? Or maybe allow user to choose? 
             // We'll stick to Generic Models for simplicity of Q2D
             ElementId catId = new ElementId(BuiltInCategory.OST_GenericModel);
             
             DirectShape ds = DirectShape.CreateElement(doc, catId);
             ds.SetShape(geoms);
             
             // Tag it
             MarkElement(ds, type);

             // Apply Visuals
             OverrideGraphicSettings ogs = new OverrideGraphicSettings();
             ogs.SetProjectionLineColor(new Color(r,g,b));
             ogs.SetSurfaceTransparency(type.Transparency);
             if (type.LineWidth > 0) ogs.SetProjectionLineWeight(type.LineWidth);
             
             FilteredElementCollector fillCollector = new FilteredElementCollector(doc);
             FillPatternElement solidFill = fillCollector.OfClass(typeof(FillPatternElement))
                .Cast<FillPatternElement>()
                .FirstOrDefault(fp => fp.GetFillPattern().IsSolidFill);
             if(solidFill != null)
             {
                 ogs.SetSurfaceForegroundPatternId(solidFill.Id);
                 ogs.SetSurfaceForegroundPatternColor(new Color(r,g,b));
             }

             doc.ActiveView.SetElementOverrides(ds.Id, ogs);
        }
        
        private void MarkElement(Element el, TakeoffType type)
        {
             // Write Type ID to Comments for robust tracking
             Parameter p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
             if(p != null && !p.IsReadOnly)
             {
                 // Format: Prefix + ID. We can also append name for human readability if we want, but logic relies on ID.
                 // Let's store: "AO_Q2D_ID:{GUID} | {Name}" to be nice to humans reading the property?
                 // But parsing is easier if strictly formatted.
                 // Let's stick to "AO_Q2D_ID:{GUID}" as primary. The Name is in the UI.
                 p.Set($"AO_Q2D_ID:{type.Id}");
             }
        }
    }
}
