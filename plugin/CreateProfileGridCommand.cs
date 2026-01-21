using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using RevitCivilConnector.models;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class CreateProfileGridCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Select curve
                Reference pickedRef = null;
                try
                {
                    pickedRef = uidoc.Selection.PickObject(ObjectType.Element, new CurveSelectionFilter(), "Seleccione una Línea de Modelo o Detalle para generar el perfil.");
                }
                catch (Autodesk.Revit.Exceptions.OperationCanceledException)
                {
                    return Result.Cancelled;
                }

                Element elem = doc.GetElement(pickedRef);
                Curve curve = null;
                if (elem is ModelLine ml) curve = ml.GeometryCurve;
                else if (elem is DetailLine dl) curve = dl.GeometryCurve;

                if (curve == null)
                {
                    message = "No se pudo obtener la geometría de la línea.";
                    return Result.Failed;
                }

                // 2. Open Config Window
                // Collect Line Styles
                List<string> lineStyles = GetAvailableLineStyles(doc);
                // Collect View Templates
                Dictionary<string, ElementId> templates = new FilteredElementCollector(doc)
                    .OfClass(typeof(View))
                    .Cast<View>()
                    .Where(v => v.IsTemplate && v.ViewType == ViewType.Section)
                    .ToDictionary(v => v.Name, v => v.Id);

                ProfileGridConfig config = null;
                try
                {
                    ProfileGridWindow win = new ProfileGridWindow(lineStyles, templates);
                    win.ShowDialog();
                    if (!win.IsConfirmed) return Result.Cancelled;
                    config = win.Config;
                }
                catch(Exception ex)
                {
                    message = "Error en interfaz: " + ex.Message;
                    return Result.Failed;
                }

                ViewSection sectionView = null;
                
                using (Transaction t = new Transaction(doc, "Create Profile Grid"))
                {
                    t.Start();
                    
                    // --- Styles ---
                    GraphicsStyle frameStyle = GetLineStyle(doc, config.FrameLineStyle);
                    GraphicsStyle gridStyle = GetLineStyle(doc, config.GridLineStyle);
                    GraphicsStyle extStyle = GetLineStyle(doc, config.ExtensionLineStyle);

                    // --- Plan Settings ---
                    double length = curve.Length;
                    double currentStation = 0;
                    
                    // Validate Intervals
                    if (config.StationInterval <= 0) config.StationInterval = 10;
                    if (config.PlanTickSize <= 0) config.PlanTickSize = 1;
                    if (config.AxisExtensionLength <= 0) config.AxisExtensionLength = 1;

                    double stationIntervalFt = UnitUtils.ConvertToInternalUnits(config.StationInterval, UnitTypeId.Meters);
                    double extensionLenFt = UnitUtils.ConvertToInternalUnits(config.AxisExtensionLength, UnitTypeId.Meters);
                    double planTickLenFt = UnitUtils.ConvertToInternalUnits(config.PlanTickSize, UnitTypeId.Meters);

                    // Safety Check for Limits (Internal Units are Feet)
                    if (stationIntervalFt < 0.1) stationIntervalFt = 1.0; 

                    TextNoteType textType = new FilteredElementCollector(doc)
                        .OfClass(typeof(TextNoteType))
                        .Cast<TextNoteType>()
                        .FirstOrDefault(x => x.Name == "Text" || x.Name == "Texto") ?? 
                        new FilteredElementCollector(doc).OfClass(typeof(TextNoteType)).Cast<TextNoteType>().FirstOrDefault();

                    // --- Annotate Plan ---
                    View activeView = doc.ActiveView;
                    bool isPlanLike = activeView.ViewType == ViewType.FloorPlan || 
                                      activeView.ViewType == ViewType.EngineeringPlan || 
                                      activeView.ViewType == ViewType.AreaPlan || 
                                      activeView.ViewType == ViewType.DraftingView;

                    if (isPlanLike)
                    {
                        double viewZ = 0;
                        if (activeView.GenLevel != null) viewZ = activeView.GenLevel.Elevation;
                        else if (activeView.SketchPlane != null && activeView.ViewType != ViewType.DraftingView) 
                            viewZ = activeView.SketchPlane.GetPlane().Origin.Z;

                        while (currentStation <= length + 0.001)
                        {
                            try
                            {
                                double normalizedParam = currentStation / length;
                                if (normalizedParam > 1.0) normalizedParam = 1.0;
                                
                                Transform curveTransform = curve.ComputeDerivatives(normalizedParam, true);
                                XYZ point = curveTransform.Origin;
                                XYZ tangent = curveTransform.BasisX.Normalize();
                                XYZ perp = new XYZ(-tangent.Y, tangent.X, 0); 
                                
                                XYZ p1 = point + perp * (planTickLenFt/2.0);
                                XYZ p2 = point - perp * (planTickLenFt/2.0);

                                if (activeView.ViewType != ViewType.DraftingView)
                                {
                                    p1 = new XYZ(p1.X, p1.Y, viewZ);
                                    p2 = new XYZ(p2.X, p2.Y, viewZ);
                                }
                                
                                DetailCurve tick = doc.Create.NewDetailCurve(activeView, Line.CreateBound(p1, p2));
                                if(extStyle != null) tick.LineStyle = extStyle; 

                                XYZ textPos = point - perp * (planTickLenFt * 1.5);
                                if (activeView.ViewType != ViewType.DraftingView)
                                    textPos = new XYZ(textPos.X, textPos.Y, viewZ);

                                textPos = new XYZ(textPos.X, textPos.Y, viewZ);

                                double stationVal = UnitUtils.ConvertFromInternalUnits(currentStation, UnitTypeId.Meters);
                                string textStr = FormatStation(stationVal);
                                
                                if (textType != null)
                                {
                                    TextNote tn = TextNote.Create(doc, activeView.Id, textPos, textStr, textType.Id);
                                    double angle = Math.Atan2(tangent.Y, tangent.X);
                                    Line axis = Line.CreateBound(textPos, textPos + XYZ.BasisZ);
                                    ElementTransformUtils.RotateElement(doc, tn.Id, axis, angle + Math.PI / 2.0);
                                }
                            }
                            catch { } 
                            currentStation += stationIntervalFt;
                        }
                    }

                    // --- Create Section View ---
                    ViewFamilyType vft = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(x => x.ViewFamily == ViewFamily.Section);

                    if (vft != null)
                    {
                        // Calculate Section Transform
                        XYZ pStart = curve.GetEndPoint(0);
                        XYZ pEnd = curve.GetEndPoint(1);
                        XYZ vX = (pEnd - pStart).Normalize();
                        XYZ vZ = XYZ.BasisZ; // Up
                        XYZ vY = vZ.CrossProduct(vX); // Normal (View Direction, away from X/Z plane? No, Revit Section: X=Right, Y=Up, Z=ViewDir)
                        // Actually, Cross(Z, X) = Y (Left Hand Rule?) -> Right Hand: Z x X = Y.
                        // Wait, Standard Basis: X=(1,0,0), Y=(0,1,0), Z=(0,0,1). Z x X = (0,1,0) = Y.
                        // So if we want BasisX=vX, BasisY=vZ (Up), then BasisZ must be Cross(vX, vZ) = -vY?
                        // Let's create BasisZ = vX.Cross(vZ). This is "Right" relative to path? No, this is -Y (Left).
                        // Let's verify.
                        
                        XYZ vNorm = vX.CrossProduct(vZ);
                        
                        Transform tf = Transform.Identity;
                        tf.Origin = pStart;
                        tf.BasisX = vX;
                        tf.BasisY = vZ;
                        tf.BasisZ = vNorm; // View Direction

                        // Calculate Vertical Limits for View (Model Geometry)
                        // Use default large box first, or calculate from min/max logic?
                        // Let's use the Profile Graph limits since we want to encompass that mostly + model.
                        // Calculate Z Range
                        double minZ = double.MaxValue;
                        double maxZ = double.MinValue;
                        int samples = 100;
                        for(int i=0; i<=samples; i++)
                        {
                             double tSample = (double)i/samples;
                             XYZ p = curve.Evaluate(tSample, true);
                             if (p.Z < minZ) minZ = p.Z;
                             if (p.Z > maxZ) maxZ = p.Z;
                        }
                        if (Math.Abs(maxZ - minZ) < 0.001) { maxZ += 5; minZ -= 5; }

                        double minZVal = UnitUtils.ConvertFromInternalUnits(minZ, UnitTypeId.Meters);
                        double maxZVal = UnitUtils.ConvertFromInternalUnits(maxZ, UnitTypeId.Meters);
                        
                        // Strict Decoupling: Range vs Interval
                        double baseElev = config.ElevationBase;
                        double topElev = config.ElevationTop;
                        
                        // Auto-Mode Override
                        if (config.AutoElevation)
                        {
                            baseElev = Math.Floor(minZVal / 5.0) * 5.0;
                            topElev = Math.Ceiling(maxZVal / 5.0) * 5.0;
                            if (topElev <= baseElev) topElev = baseElev + 10.0;
                        }
                        
                        double baseZFt = UnitUtils.ConvertToInternalUnits(baseElev, UnitTypeId.Meters);
                        double topZFt = UnitUtils.ConvertToInternalUnits(topElev, UnitTypeId.Meters);

                        // Bounding Box
                        BoundingBoxXYZ sectionBox = new BoundingBoxXYZ();
                        sectionBox.Transform = tf;
                        
                        // Local Coordinates relative to Transform
                        // X goes from 0 to Length
                        // Y goes from MinZ (relative to Origin.Z?) to MaxZ
                        // Z (Depth) +/- Offset
                        // Re-check Transform Origin: Origin is pStart (Z=pStart.Z).
                        // If pStart.Z is e.g. 100, and baseZFt is 90. Then MinY = 90-100 = -10.
                        // Correct.
                        
                        double zOffsetStart = baseZFt - pStart.Z;
                        double zOffsetEnd = topZFt - pStart.Z;
                        
                        // Add buffer for Annotations (below base)
                        // Add buffer for Annotations (below base)
                        double annotationBuffer = UnitUtils.ConvertToInternalUnits(5.0, UnitTypeId.Meters);
                        double xMargin = UnitUtils.ConvertToInternalUnits(10.0, UnitTypeId.Meters); 

                        sectionBox.Min = new XYZ(-xMargin, zOffsetStart - annotationBuffer, -10); 
                        sectionBox.Max = new XYZ(length + xMargin, zOffsetEnd + 5, 10);

                        sectionView = ViewSection.CreateSection(doc, vft.Id, sectionBox);
                        string secName = config.SectionNamePrefix + " " + DateTime.Now.ToString("HHmmss");
                        try { sectionView.Name = secName; } catch {}

                         // Apply Template
                        if (config.SelectedTemplateId != ElementId.InvalidElementId)
                        {
                            try { sectionView.ViewTemplateId = config.SelectedTemplateId; } catch {}
                        }

                        // --- Draw Graph Elements in Section ---
                        List<ElementId> graphElements = new List<ElementId>();
                        
                        // Coordinates in Section View (Detail Plane)
                        // X = Station
                        // Y = Elevation
                        // NOTE: Section View Origin might behave differently?
                        // "The origin of the section view is the origin of the section box."
                        // So (0,0) in logic matches (0,0) in view if we use same Origin. Yes.
                        // HOWEVER: Logic below uses absolute Z (baseZFt).
                        // In Section View, Y is relative to Origin.Z? 
                        // If Origin.Z = pStart.Z, then Y=0 is pStart.Z.
                        // If I draw a line at Y=100 (Abs), it will interpret it as 100ft ABOVE pStart.Z?
                        // OR does Describe give absolute coordinates?
                        // `NewDetailCurve(view, line)`: line coordinates are Projected coordinates on the plane.
                        // If I draw (0,0,0) -> It is at the Origin of the view.
                        // If Section Origin is at Z=pStart.Z.
                        // If I want to draw text at Z=100, and pStart.Z=100, I should draw at Y=0?
                        // Let's verify: In Plan/Drafting, (x,y,z) are world?
                        // In Section, `NewDetailCurve` inputs are usually in View Coordinates (X, Y in paper space)?
                        // NO. `NewDetailCurve` typically takes Model Coordinates projected onto plane.
                        // So if I pass `new XYZ(x, z, 0)` it assumes World Coordinates `(x, z, 0)`?
                        // No, DetailCurve in specific view...
                        // If it's `ViewSection`, `NewDetailCurve` lines must lie in the view plane.
                        // The inputs are Model Coordinates that lie on the plane.
                        // So I must provide (ModelX, ModelY, ModelZ) that is physically on the plane.
                        // My code calculates `(station, elevation, 0)`. This is clearly conceptual 2D.
                        // I NEED TO TRANSFORM these (Station, Elev) into Model (x,y,z).
                        // Point = Origin + Station*BasisX + Elevation*BasisY.
                        // THIS IS KEY.
                        // `drafting` view worked because drafting view space is abstract 2D.
                        // `sectionView` is 3D slice.
                        
                        // Need a transformation function: 
                        // ModelPoint = tf.Origin + u * tf.BasisX + v * tf.BasisY
                        // u = Station, v = Elevation - Origin.Z ?
                        // Wait, tf.BasisY is Z-World.
                        // So ModelPoint = (pStart.X, pStart.Y, pStart.Z) + Station*vX + (Elevation - pStart.Z)*vZ ?
                        // Simplified: ModelPoint = pStart + Station*vX + (Elevation - pStart.Z)*vZ.
                        // Actually simpler: 
                        // Project the station along the line: `pOnLine = pStart + Station * vX`.
                        // Then set Z to Elevation: `pModel = new XYZ(pOnLine.X, pOnLine.Y, Elevation)`.
                        // This assumes the line is flat/horizontal?
                        // If the line is sloped, "Station" usually means horizontal distance.
                        // My code currently assumes `dist = length * tVal` ? `length` is along curve.
                        // If curve is sloped, `ComputeDerivatives` gives point in 3D.
                        // `profilePoints` uses `dist` (along curve) for X.
                        // If I map this to Section X-axis (which is vX = Start->End normalized), 
                        // is `vX` horizontal?
                        // `XYZ vX = (pEnd - pStart).Normalize();`
                        // If pStart.Z != pEnd.Z, the section is tilted!
                        // Do users want a tilted section or a vertical section?
                        // Typically Vertical Section.
                        // So vX should be flattened? `(pEnd - pStart)` flattened.
                        // Let's assume standard Civil profiling: Vertical Section along trace.
                        // Plan = (X,Y). Section aligned with (X,Y) trace.
                        // New `vX` calculation:
                        XYZ vBase = new XYZ(pEnd.X - pStart.X, pEnd.Y - pStart.Y, 0).Normalize();
                        Transform tfReal = Transform.Identity;
                        tfReal.Origin = new XYZ(pStart.X, pStart.Y, 0); // Origin at Z=0?
                        // If I set Origin at Z=0, then Elevation Y maps directly to World Z.
                        // But Section Box must cut the geometry.
                        // Let's keep `pStart` as origin, but adjust basis.
                        tfReal.Origin = pStart;
                        tfReal.BasisX = vBase; // Horizontal vector
                        tfReal.BasisY = XYZ.BasisZ; // Vertical vector
                        tfReal.BasisZ = vBase.CrossProduct(XYZ.BasisZ); // Normal
                        
                        // Re-create section with `tfReal` (Horizontal Trace).
                        sectionBox.Transform = tfReal;
                        // Min/Max need update for relative Z.
                        // Origin Z = pStart.Z.
                        // If BaseElev = 90, Relative Y = 90 - pStart.Z.
                        zOffsetStart = baseZFt - pStart.Z;
                        zOffsetEnd = topZFt - pStart.Z;
                        sectionBox.Min = new XYZ(0, zOffsetStart - annotationBuffer, -10); 
                        sectionBox.Max = new XYZ(length, zOffsetEnd + 5, 10); 
                        
                        // Now Mapping Function:
                        // (Station, Elev) -> Model XYZ
                        // P = tfReal.Origin + Station * tfReal.BasisX + (Elev - tfReal.Origin.Z) * tfReal.BasisY
                        
                        Func<double, double, XYZ> ToModel = (s, z) => {
                            return tfReal.Origin 
                                + (s * tfReal.BasisX) 
                                + ((z - tfReal.Origin.Z) * tfReal.BasisY);
                        };
                        
                        // Now I can reuse drawing logic but transform points using `ToModel`.

                        // --- Draw Frame ---
                        // Reusing loops exactly, just wrapping p creation with ToModel.
                        
                        XYZ pBL = ToModel(0, baseZFt);
                        XYZ pBR = ToModel(length, baseZFt);
                        XYZ pTL = ToModel(0, topZFt);
                        XYZ pTR = ToModel(length, topZFt);
                        
                        List<Curve> frameCurves = new List<Curve>
                        {
                             Line.CreateBound(pBL, pBR), Line.CreateBound(pTL, pTR),
                             Line.CreateBound(pBL, pTL), Line.CreateBound(pBR, pTR)
                        };

                        foreach(Curve c in frameCurves)
                        {
                             DetailCurve dc = doc.Create.NewDetailCurve(sectionView, c);
                             if(frameStyle != null) dc.LineStyle = frameStyle;
                             graphElements.Add(dc.Id);
                        }

                        // --- Vertical (Stations) ---
                        currentStation = 0;
                        while(currentStation <= length + 0.001)
                        {
                             try {
                                 XYZ p1 = ToModel(currentStation, baseZFt);
                                 XYZ p2 = ToModel(currentStation, topZFt);
                                 DetailCurve gridV = doc.Create.NewDetailCurve(sectionView, Line.CreateBound(p1, p2));
                                 if(gridStyle != null) gridV.LineStyle = gridStyle;
                                 graphElements.Add(gridV.Id);

                                 XYZ pExtStart = ToModel(currentStation, baseZFt);
                                 XYZ pExtEnd = ToModel(currentStation, baseZFt - extensionLenFt);
                                 DetailCurve extV = doc.Create.NewDetailCurve(sectionView, Line.CreateBound(pExtStart, pExtEnd));
                                 if(extStyle != null) extV.LineStyle = extStyle;
                                 graphElements.Add(extV.Id);

                                 graphElements.Add(extV.Id);

                                 string label = FormatStation(UnitUtils.ConvertFromInternalUnits(currentStation, UnitTypeId.Meters));
                                 // Text Note placement needs "Model" point? Yes.
                                 XYZ pText = ToModel(currentStation, baseZFt - extensionLenFt - planTickLenFt/2.0); // Offset slightly
                                 if(textType != null)
                                 {
                                     TextNote tn = TextNote.Create(doc, sectionView.Id, pText, label, textType.Id);
                                     tn.HorizontalAlignment = HorizontalTextAlignment.Center;
                                     tn.VerticalAlignment = VerticalTextAlignment.Top;
                                     graphElements.Add(tn.Id);
                                 }
                             } catch {}
                             currentStation += stationIntervalFt;
                        }

                        // --- Horizontal (Elevations) ---
                         double elevStep = config.ElevationInterval; 
                        if (elevStep <= 0.01) elevStep = 1.0; 
                        
                        // Start at valid multiple of interval? Or just start at Base?
                        // Usually Grid Lines are at round numbers (e.g. 100, 105, 110) even if Base is 102.
                        // So we identify the first Interval Multiple >= Base.
                        double startGridElev = Math.Ceiling(baseElev / elevStep) * elevStep;
                        double gridElev = startGridElev;

                        while (gridElev <= topElev + 0.001)
                        {
                             try {
                                 double z = UnitUtils.ConvertToInternalUnits(gridElev, UnitTypeId.Meters);
                                 
                                 // Check containment (redundant given loop but safe)
                                 if (z >= baseZFt - 0.001 && z <= topZFt + 0.001)
                                 {
                                     XYZ p1 = ToModel(0, z);
                                     XYZ p2 = ToModel(length, z);
                                     
                                     // Draw Main Grid Line
                                     DetailCurve gridH = doc.Create.NewDetailCurve(sectionView, Line.CreateBound(p1, p2));
                                     if(gridStyle != null) gridH.LineStyle = gridStyle;
                                     graphElements.Add(gridH.Id);
                                     
                                     XYZ pExtStart = ToModel(0, z);
                                     XYZ pExtEnd = ToModel(-extensionLenFt, z); 
                                     DetailCurve extH = doc.Create.NewDetailCurve(sectionView, Line.CreateBound(pExtStart, pExtEnd));
                                     if(extStyle != null) extH.LineStyle = extStyle;
                                     graphElements.Add(extH.Id);

                                     // Label just value
                                     string label = gridElev.ToString("F2");
                                     XYZ pText = ToModel(-extensionLenFt - planTickLenFt/2.0, z);
                                     if(textType != null)
                                     {
                                        TextNote tn = TextNote.Create(doc, sectionView.Id, pText, label, textType.Id);
                                        tn.HorizontalAlignment = HorizontalTextAlignment.Right;
                                        tn.VerticalAlignment = VerticalTextAlignment.Middle;
                                        graphElements.Add(tn.Id);
                                     }
                                 }
                             } catch {}
                             gridElev += elevStep;
                        }

                        // --- Profile Line ---
                        GraphicsStyle medStyle = GetLineStyle(doc, "Medium Lines") ?? GetLineStyle(doc, "Líneas medias");
                        
                        List<XYZ> profilePoints = new List<XYZ>();
                        int resolution = 200;
                        for(int i=0; i<=resolution; i++)
                        {
                            double tVal = (double)i/resolution;
                            XYZ pt3d = curve.Evaluate(tVal, true);
                            
                            // Map Profile Point to Graph Coordinates?
                            // Graph X = Distance along curve?
                            // Graph Y = Z.
                            // The "Profile Graph" shows "Distance vs Elevation".
                            // If we draw this in Model Space (Section), it aligns with the terrain IF the terrain is under the line.
                            // But we are drawing a Chart.
                            // Dist = i/res * length.
                            // Z = pt3d.Z.
                            // Point = ToModel(dist, z).
                            
                            double dist = length * tVal;
                            profilePoints.Add(ToModel(dist, pt3d.Z));
                        }
                        
                         for(int i=0; i<profilePoints.Count-1; i++)
                        {
                            try{
                                if (profilePoints[i].IsAlmostEqualTo(profilePoints[i+1])) continue;
                                Line seg = Line.CreateBound(profilePoints[i], profilePoints[i+1]);
                                DetailCurve dcProfile = doc.Create.NewDetailCurve(sectionView, seg);
                                if(medStyle != null) dcProfile.LineStyle = medStyle;
                                
                                OverrideGraphicSettings redOgs = new OverrideGraphicSettings();
                                redOgs.SetProjectionLineColor(new Autodesk.Revit.DB.Color(255, 0, 0));
                                redOgs.SetProjectionLineWeight(4);
                                sectionView.SetElementOverrides(dcProfile.Id, redOgs);
                                graphElements.Add(dcProfile.Id);
                            } catch {}
                        }

                        // --- Group ---
                        if (graphElements.Count > 0)
                        {
                            doc.Create.NewGroup(graphElements);
                        }
                    }

                    t.Commit();
                }

                if (sectionView != null)
                {
                    uidoc.ActiveView = sectionView;
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message + "\n" + ex.StackTrace;
                return Result.Failed;
            }
        }

        private string FormatStation(double meters)
        {
            int km = (int)(meters / 1000);
            double m = meters % 1000;
            return $"{km}+{m:000}";
        }

        private List<string> GetAvailableLineStyles(Document doc)
        {
            List<string> styles = new List<string>();
            Category linesCat = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines);
            if (linesCat != null)
            {
                foreach (Category sub in linesCat.SubCategories)
                {
                    styles.Add(sub.Name);
                }
            }
            styles.Sort();
            return styles;
        }

        private GraphicsStyle GetLineStyle(Document doc, string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            Category linesCat = doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines);
            if(linesCat == null) return null;
            
            CategoryNameMap subCats = linesCat.SubCategories;
            if(subCats.Contains(name))
            {
                Category sub = subCats.get_Item(name);
                return sub.GetGraphicsStyle(GraphicsStyleType.Projection);
            }
            return null;
        }

        public class CurveSelectionFilter : ISelectionFilter
        {
            public bool AllowElement(Element elem)
            {
                return elem is ModelLine || elem is DetailLine;
            }

            public bool AllowReference(Reference reference, XYZ position)
            {
                return true;
            }
        }
    }
}
