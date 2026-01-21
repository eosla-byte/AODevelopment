using System;
using System.Collections.Generic;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.UI
{
    // Possible actions the AI can request
    public enum IARequestType
    {
        None,
        AuditWalls,
        AutoDimension,
        GenerateShopDrawings,
        GenerateMEPFromLines,
        CountElements,
        CreateSheet,
        CreateSheetList,
        ToggleRecording
    }

    public class IARequestHandler : IExternalEventHandler
    {
        public IARequestType Request { get; set; } = IARequestType.None;

        public void Execute(UIApplication uiapp)
        {
            try
            {
                switch (Request)
                {
                    case IARequestType.AuditWalls:
                        AuditWalls(uiapp);
                        break;
                    case IARequestType.AutoDimension:
                        AutoDimension(uiapp);
                        break;
                    case IARequestType.GenerateShopDrawings:
                        GenerateShopDrawings(uiapp);
                        break;
                    case IARequestType.GenerateMEPFromLines:
                        GenerateMEPFromLines(uiapp);
                        break;
                    case IARequestType.CountElements:
                        // CountElements(uiapp);
                        break;
                    case IARequestType.ToggleRecording:
                        ToggleRecording();
                        break;
                    case IARequestType.CreateSheetList:
                        CreateSheetList(uiapp);
                        break;
                    default:
                        break;
                }
            }
            catch (Exception ex)
            {
                TaskDialog.Show("IA Error", "Error executing IA command: " + ex.Message);
            }
        }

        public string GetName()
        {
            return "IA Action Handler";
        }

        private void GenerateMEPFromLines(UIApplication uiapp)
        {
            UIDocument uidoc = uiapp.ActiveUIDocument;
            Document doc = uidoc.Document;

            // 1. Select Lines
            ICollection<ElementId> selectionIds = uidoc.Selection.GetElementIds();
            if (selectionIds.Count == 0)
            {
                TaskDialog.Show("IA Info", "Selecciona las Líneas de Modelo que deseas convertir a tuberías/ductos.");
                return;
            }

            // 2. Collect Types for UI
            FilteredElementCollector colPipeTypes = new FilteredElementCollector(doc).OfClass(typeof(Autodesk.Revit.DB.Plumbing.PipeType));
            List<Element> pipeTypes = colPipeTypes.ToElements() as List<Element>;

            FilteredElementCollector colSysTypes = new FilteredElementCollector(doc).OfClass(typeof(Autodesk.Revit.DB.Plumbing.PipingSystemType));
            List<Element> systemTypes = colSysTypes.ToElements() as List<Element>;

            FilteredElementCollector colLevels = new FilteredElementCollector(doc).OfClass(typeof(Level));
            List<Level> levels = new List<Level>();
            foreach(Element e in colLevels) levels.Add(e as Level);

            // Default level
            Level defaultLevel = doc.ActiveView.GenLevel;
            if (defaultLevel == null &&levels.Count > 0) defaultLevel = levels[0];

            if (pipeTypes.Count == 0 || systemTypes.Count == 0)
            {
                TaskDialog.Show("IA Error", "No se encontraron tipos de tubería o sistema en el proyecto.");
                return;
            }

            // 3. Show Config Window
            MEPConfigWindow win = new MEPConfigWindow(pipeTypes, systemTypes, levels, defaultLevel);
            win.ShowDialog();

            if (!win.IsConfirmed) return; // User cancelled

            // 4. Create Pipes
            using (Transaction t = new Transaction(doc, "IA Create MEP Custom"))
            {
                t.Start();
                int created = 0;

                foreach (ElementId id in selectionIds)
                {
                    Element e = doc.GetElement(id);
                    if (e is ModelLine || e is DetailLine) 
                    {
                        Curve curve = (e.Location as LocationCurve)?.Curve;
                        if (curve != null)
                        {
                            try
                            {
                                // Create Pipe
                                Autodesk.Revit.DB.Plumbing.Pipe pipe = Autodesk.Revit.DB.Plumbing.Pipe.Create(doc, win.SelectedSystemTypeId, win.SelectedPipeTypeId, win.SelectedLevelId, curve.GetEndPoint(0), curve.GetEndPoint(1));
                                
                                // Set Diameter (RBS_PIPE_DIAMETER_PARAM)
                                // Value must be in internal units (feet). Input is mm.
                                double diameterFeet = win.SelectedDiameterMm / 304.8; 
                                
                                Parameter pDia = pipe.get_Parameter(BuiltInParameter.RBS_PIPE_DIAMETER_PARAM);
                                if (pDia != null && !pDia.IsReadOnly) 
                                {
                                    pDia.Set(diameterFeet);
                                }
                                
                                created++;
                            }
                            catch {}
                        }
                    }
                }
                t.Commit();
                TaskDialog.Show("IA Result", $"Se crearon {created} tuberías.\nSistema: {doc.GetElement(win.SelectedSystemTypeId).Name}\nDiámetro: {win.SelectedDiameterMm} mm");
            }
        }

        private void GenerateShopDrawings(UIApplication uiapp)
        {
            UIDocument uidoc = uiapp.ActiveUIDocument;
            Document doc = uidoc.Document;

            // 1. Get Selected Elements or All in Active View
            ICollection<ElementId> selectionIds = uidoc.Selection.GetElementIds();
            IList<Element> elements = new List<Element>();

            if (selectionIds.Count > 0)
            {
                foreach (ElementId id in selectionIds) elements.Add(doc.GetElement(id));
            }
            else
            {
                // Fallback: Pick all visible Generic Models, Structural Framing, or Walls
                FilteredElementCollector col = new FilteredElementCollector(doc, doc.ActiveView.Id);
                col.WherePasses(new ElementMulticategoryFilter(new List<BuiltInCategory> { BuiltInCategory.OST_GenericModel, BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_Walls }));
                elements = col.ToElements();
            }

            if (elements.Count == 0)
            {
                TaskDialog.Show("IA Info", "Selecciona elementos (Muros, Vigas, Modelos Genéricos) para generar despieces.");
                return;
            }

            using (Transaction t = new Transaction(doc, "IA Generate Shop Drawings"))
            {
                t.Start();

                // 2. Group by Geometry (Simplified: Same Type + Volume + Approx BoundingBox)
                Dictionary<string, List<Element>> groups = new Dictionary<string, List<Element>>();
                
                foreach (Element e in elements)
                {
                    // Create a "Key" based on geometry
                    string key = GetGeometryKey(e);
                    if (!groups.ContainsKey(key)) groups[key] = new List<Element>();
                    groups[key].Add(e);
                }

                int groupsCreated = 0;
                int assembliesCreated = 0;

                // 3. Process Groups
                foreach (var kvp in groups)
                {
                    List<Element> groupElements = kvp.Value;
                    string groupName = "AI-GRP-" + (groupsCreated + 1).ToString("00");
                    groupsCreated++;

                    // Write to Comments Parameter
                    foreach (Element e in groupElements)
                    {
                        Parameter p = e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                        if (p != null && !p.IsReadOnly) p.Set(groupName);
                    }

                    // 4. Create Assembly for ONE representative (Revit requirement: AssemblyInstance is per set of elements)
                    // Actually, if we want shop drawings for the "Type", we create an Assembly for one instance.
                    // If we want Asssemblies for ALL, we do loop. 
                    // Let's create Assembly for the FIRST one to generate the Shop Drawing (View)
                    
                    Element representative = groupElements[0];
                    List<ElementId> ids = new List<ElementId> { representative.Id };
                    
                    try
                    {
                        ElementId categoryId = representative.Category.Id;
                        AssemblyInstance assemblyInstance = AssemblyInstance.Create(doc, ids, categoryId);
                        
                        // Commit temporarily to generate views? No, straightforward transaction.
                        // Create Views
                        if (assemblyInstance != null)
                        {
                            assembliesCreated++;
                            
                            // Try to create views
                            try 
                            { 
                                // ViewSheet sheet = AssemblyViewUtils.CreateSheet(doc, assemblyInstance.Id, TitleBlockId...); // Needs Titleblock
                                // Fallback: Just Detail Views
                                // AssemblyViewUtils.Create3DOrthographic(doc, assemblyInstance.Id); 
                                // AssemblyViewUtils.CreateDetailSection(doc, assemblyInstance.Id, AssemblyDetailViewOrientation.DetailSectionA);
                            }
                            catch {} 
                        }
                    }
                    catch { } // Assembly creation might fail if element is already in assembly
                }

                t.Commit();
                TaskDialog.Show("IA Result", $"Agrupamiento completado.\n\nGrupos identificados: {groups.Count}\nIdentificador escrito en 'Comentarios'.\n\n(La generación de Planos de Montaje (Assemblies) requiere configuración de TitleBlocks, por ahora solo se agruparon).");
            }
        }

        private string GetGeometryKey(Element e)
        {
            // Type ID + Volume (if avail) + Bounding Box Size
            string typeId = e.GetTypeId().ToString();
            
            // Try get Volume
            double volume = 0;
            Parameter pVol = e.get_Parameter(BuiltInParameter.HOST_VOLUME_COMPUTED);
            if (pVol != null) volume = pVol.AsDouble();
            
            // Bounding Box
            BoundingBoxXYZ bb = e.get_BoundingBox(null);
            double bbVol = 0;
            if (bb != null)
            {
                bbVol = (bb.Max.X - bb.Min.X) * (bb.Max.Y - bb.Min.Y) * (bb.Max.Z - bb.Min.Z);
            }

            return $"{typeId}_{volume.ToString("F2")}_{bbVol.ToString("F2")}";
        }

        private void AutoDimension(UIApplication uiapp)
        {
            UIDocument uidoc = uiapp.ActiveUIDocument;
            Document doc = uidoc.Document;
            View view = doc.ActiveView;

            if (view is View3D)
            {
                 TaskDialog.Show("IA Info", "Acotación automática en 3D aún está en beta. Por favor intenta en Planta o Sección.");
                 return;
            }

            using (Transaction t = new Transaction(doc, "IA Auto Dimension"))
            {
                t.Start();
                
                // 1. Collect Visible Grids
                FilteredElementCollector collector = new FilteredElementCollector(doc, view.Id);
                IList<Element> grids = collector.OfClass(typeof(Grid)).ToElements();
                
                if (grids.Count < 2) 
                {
                    TaskDialog.Show("IA Info", "No hay suficientes ejes (Grids) visibles para acotar.");
                    t.RollBack();
                    return;
                }

                // 2. Separate into Vertical and Horizontal (Simplified check using Curve)
                List<Grid> verticalGrids = new List<Grid>();
                List<Grid> horizontalGrids = new List<Grid>();

                foreach (Grid g in grids)
                {
                    Line line = g.Curve as Line;
                    if (line != null)
                    {
                        XYZ dir = line.Direction;
                        if (Math.Abs(dir.X) < 0.1) verticalGrids.Add(g); // Mostly Y-oriented
                        else horizontalGrids.Add(g); // Mostly X-oriented
                    }
                }

                int dimsCreated = 0;

                // 3. Create Dimensions
                if (verticalGrids.Count > 1) dimsCreated += CreateChainDimension(doc, view, verticalGrids, true);
                if (horizontalGrids.Count > 1) dimsCreated += CreateChainDimension(doc, view, horizontalGrids, false);

                t.Commit();
                TaskDialog.Show("IA Result", $"Se han creado {dimsCreated} líneas de cotas automáticas.");
            }
        }

        private int CreateChainDimension(Document doc, View view, List<Grid> grids, bool isVerticalGroup)
        {
            // Sort grids purely by coordinate
            grids.Sort((a, b) => 
            {
                Line l1 = a.Curve as Line;
                Line l2 = b.Curve as Line;
                if (isVerticalGroup) return l1.Origin.X.CompareTo(l2.Origin.X);
                else return l1.Origin.Y.CompareTo(l2.Origin.Y);
            });

            ReferenceArray refArray = new ReferenceArray();
            foreach (Grid g in grids)
            {
                refArray.Append(new Reference(g));
            }

            // Determine placement line
            // For Verticals (X-sorted), we draw a Horizontal Line at the top/bottom
            // For Horizontals (Y-sorted), we draw a Vertical Line at left/right
            
            // Get BoundingBox of the view or grids to pick a nice spot? 
            // Simplified: Use the origin of the first grid and offset
            
            Line firstLine = (grids[0] as Grid).Curve as Line;
            Line lastLine = (grids[grids.Count - 1] as Grid).Curve as Line;
            
            XYZ pt1, pt2;

            if (isVerticalGroup) // Vertical Grids -> Horizontal Dimension Line
            {
                // Find average Y
                double midY = (firstLine.Origin.Y + firstLine.GetEndPoint(1).Y) / 2.0;
                // Create line crossing all X
                pt1 = new XYZ(firstLine.Origin.X - 5, midY, 0); 
                pt2 = new XYZ(lastLine.Origin.X + 5, midY, 0);
            }
            else // Horizontal Grids -> Vertical Dimension Line
            {
                // Find average X
                double midX = (firstLine.Origin.X + firstLine.GetEndPoint(1).X) / 2.0;
                 // Create line crossing all Y
                pt1 = new XYZ(midX, firstLine.Origin.Y - 5, 0); 
                pt2 = new XYZ(midX, lastLine.Origin.Y + 5, 0);
            }

            Line dimLine = Line.CreateBound(pt1, pt2);

            try
            {
                doc.Create.NewDimension(view, dimLine, refArray);
                return 1;
            }
            catch
            {
                return 0;
            }
        }

        private void AuditWalls(UIApplication uiapp)
        {
            UIDocument uidoc = uiapp.ActiveUIDocument;
            Document doc = uidoc.Document;

            // Simple Logic: Find overlapping walls (proxy for duplicates)
            FilteredElementCollector collector = new FilteredElementCollector(doc);
            IList<Element> walls = collector.OfClass(typeof(Wall)).ToElements();

            int duplicateCount = 0;
            List<ElementId> duplicates = new List<ElementId>();

            // Basic geometric check (BoundingBox center proximity) - Fast prototype
            // A real audit would check geometry intersection
            for (int i = 0; i < walls.Count; i++)
            {
                for (int j = i + 1; j < walls.Count; j++)
                {
                    Wall w1 = walls[i] as Wall;
                    Wall w2 = walls[j] as Wall;

                    BoundingBoxXYZ bb1 = w1.get_BoundingBox(null);
                    BoundingBoxXYZ bb2 = w2.get_BoundingBox(null);

                    if (bb1 != null && bb2 != null)
                    {
                        XYZ c1 = (bb1.Min + bb1.Max) / 2.0;
                        XYZ c2 = (bb2.Min + bb2.Max) / 2.0;

                        if (c1.IsAlmostEqualTo(c2, 0.01)) // Very close centers
                        {
                            duplicateCount++;
                            duplicates.Add(w1.Id);
                            // break; // Count pairs
                        }
                    }
                }
            }

            TaskDialog.Show("IA Audit", $"Análisis Completado.\n\nMuros analizados: {walls.Count}\nPosibles duplicados detectados: {duplicateCount}");
            
            if (duplicateCount > 0)
            {
                uidoc.Selection.SetElementIds(duplicates);
            }
        }
        private void ToggleRecording()
        {
            if (App.Recorder.IsRecording)
            {
                App.Recorder.StopRecording();
                var logs = App.Recorder.GetSessionLog();
                // In a real system, we would send this 'logs' list to the backend
                // For now, we just show it to the user.
                string summary = string.Join("\n", logs);
                if(string.IsNullOrEmpty(summary)) summary = "No actions recorded.";
                
                TaskDialog.Show("IA Learning", "Recording Stopped. Actions Learned:\n\n" + summary);
            }
            else
            {
                App.Recorder.StartRecording();
                TaskDialog.Show("IA Learning", "Recording Started... Perform your actions in Revit (Create walls, dimensions, etc). Press the button again to stop.");
            }
        }
        private void CreateSheetList(UIApplication uiapp)
        {
            UIDocument uidoc = uiapp.ActiveUIDocument;
            Document doc = uidoc.Document;

            using (Transaction t = new Transaction(doc, "IA Create Sheet List"))
            {
                t.Start();
                try
                {
                    // Create Schedule for Sheets
                    ElementId categoryId = new ElementId(BuiltInCategory.OST_Sheets);
                    ViewSchedule schedule = ViewSchedule.CreateSchedule(doc, categoryId);
                    schedule.Name = "Listado de Planos (IA Generated)";

                    // Add Fields: Sheet Number, Sheet Name
                    // We need to find the specific fields from SchedulableFields
                    foreach (SchedulableField sf in schedule.Definition.GetSchedulableFields())
                    {
                        if (sf.ParameterId == new ElementId(BuiltInParameter.SHEET_NUMBER) || 
                            sf.ParameterId == new ElementId(BuiltInParameter.SHEET_NAME))
                        {
                            schedule.Definition.AddField(sf);
                        }
                    }

                    t.Commit();
                    
                    // Activate View
                    uidoc.ActiveView = schedule;
                    
                    TaskDialog.Show("IA Result", "Listado de Planos creado con éxito.");
                }
                catch (Exception ex)
                {
                    t.RollBack();
                    TaskDialog.Show("IA Error", "No se pudo crear el listado: " + ex.Message);
                }
            }
        }
    }
}
