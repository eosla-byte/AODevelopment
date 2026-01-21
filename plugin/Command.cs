using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.Models;
using RevitCivilConnector.Services;
using RevitCivilConnector.UI;

namespace RevitCivilConnector
{
    using RevitCivilConnector.Utils;

    [Transaction(TransactionMode.Manual)]
    public class Command : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Conectar con Civil 3D y obtener Corridors
                Civil3DService c3dService = new Civil3DService();
                if (!c3dService.IsCivil3DRunning())
                {
                    TaskDialog.Show("Error", "No se encontró una instancia activa de Civil 3D 2024.");
                    return Result.Failed;
                }

                List<CivilCorridor> corridors = c3dService.GetCorridors();

                if (corridors.Count == 0)
                {
                    TaskDialog.Show("Info", "No se encontraron Corridors en el dibujo activo de Civil 3D.");
                    return Result.Succeeded;
                }

                // 2. Mostrar Interfaz de Usuario (WPF)
                // Necesitamos pasar la lista de materiales de Revit a la ventana para el combobox
                List<Material> revitMaterials = new FilteredElementCollector(doc)
                    .OfClass(typeof(Material))
                    .Cast<Material>()
                    .OrderBy(m => m.Name)
                    .ToList();

                CorridorSelectorWindow window = new CorridorSelectorWindow(corridors, revitMaterials);
                bool? result = window.ShowDialog();

                if (result == true)
                {
                    Logger.Log("User accepted dialog. Starting import...");
                    
                    // 3. Procesar selección e importar geometría
                    RevitGeometryService geoService = new RevitGeometryService(doc);
                    int totalImported = 0; // Declare outside transaction scope
                    
                    using (Transaction t = new Transaction(doc, "Importar Corridors Civil3D"))
                    {
                        t.Start();
                        Logger.Log("Transaction started. Plugin Version: 4.0 (Native Solids)");

                        // TEST CUBE
                        try 
                        {
                            Logger.Log("Attempting to create Test Cube at (0,0,0)...");
                            DirectShape ds = DirectShape.CreateElement(doc, new ElementId(BuiltInCategory.OST_GenericModel));
                            ds.Name = "TEST CUBE - CHECK VISIBILITY";
                            
                            // 1m cube (3.28ft)
                            double d = 3.28084; 
                            List<XYZ> loop = new List<XYZ> { new XYZ(0,0,0), new XYZ(d,0,0), new XYZ(d,d,0), new XYZ(0,d,0) };
                            
                            // Convert vertices to curves (CurveLoop.Create requires lines, not points directly in older APIs, or strict typing)
                            List<Curve> curves = new List<Curve>();
                            for(int i=0; i<loop.Count; i++)
                            {
                                XYZ pStart = loop[i];
                                XYZ pEnd = loop[(i+1) % loop.Count];
                                curves.Add(Line.CreateBound(pStart, pEnd));
                            }
                            
                            CurveLoop cl = CurveLoop.Create(curves);
                            Solid solid = GeometryCreationUtilities.CreateExtrusionGeometry(new List<CurveLoop>{cl}, new XYZ(0,0,1), d);
                            ds.SetShape(new List<GeometryObject>{solid});
                            Logger.Log("Test Cube Created.");
                        }
                        catch(Exception ex) { Logger.Log($"Test Cube Failed: {ex.Message}"); }
                        
                        foreach (var corridor in corridors.Where(c => c.IsSelected))
                        {
                            Logger.Log($"Processing Corridor: {corridor.Name}");
                            // Para cada corridor seleccionado, importar sus códigos seleccionados
                            foreach (var code in corridor.Codes.Where(cd => cd.IsSelected))
                            {
                                Logger.Log($"  Processing Code: {code.CodeName}");
                                // Obtener los sólidos desde Civil 3D
                                var solidsData = c3dService.GetSolidsForCorridorCode(corridor.Handle, code.CodeName);
                                
                                if (solidsData != null && solidsData.Count > 0)
                                {
                                    Logger.Log($"    Found {solidsData.Count} chunks. creating DirectShapes...");
                                    geoService.CreateDirectShapes(solidsData, code.RevitCategory, code.RevitMaterial);
                                    totalImported += solidsData.Count;
                                }
                                else
                                {
                                    Logger.Log("    No geometry found.");
                                    TaskDialog.Show("Warning", $"No geometry found in Civil 3D for code: {code.CodeName}\nSee Log on Desktop.");
                                }
                            }
                        }

                        t.Commit();
                        Logger.Log("Transaction Committed.");
                    }
                    
                    TaskDialog.Show("Éxito", $"Importación completada.\nItems: {totalImported}\nRevise 'RevitCivilConnector_Log.txt' en el Escritorio.");
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message + "\n" + ex.StackTrace;
                return Result.Failed;
            }
        }
    }
}
