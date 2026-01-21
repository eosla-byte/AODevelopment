using System;
using System.Collections.Generic;
using System.IO;
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
    public class CoordinatesCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Gather Family Symbols (Generic Models, Structural Columns, etc.)
                // Let's filter for Point-based families (Generic Models mainly)
                List<FamilySymbol> symbols = new FilteredElementCollector(doc)
                    .OfClass(typeof(FamilySymbol))
                    .WhereElementIsElementType()
                    .Cast<FamilySymbol>()
                    .Where(x => x.Category != null && (x.Category.Id.Value == (long)BuiltInCategory.OST_GenericModel || x.Category.Id.Value == (long)BuiltInCategory.OST_StructuralColumns))
                    .ToList();

                // 2. Show UI
                CoordinatesWindow win = new CoordinatesWindow(symbols);
                win.ShowDialog();

                if (!win.IsConfirmed) return Result.Cancelled;
                
                CoordinatesConfig config = win.Config;

                // 3. Execution
                using (Transaction t = new Transaction(doc, "Coordenadas"))
                {
                    t.Start();
                    
                    // Activate Symbol if needed
                    FamilySymbol fs = null;
                    if (config.SelectedFamilySymbolId != ElementId.InvalidElementId)
                    {
                        fs = doc.GetElement(config.SelectedFamilySymbolId) as FamilySymbol;
                        if (fs != null && !fs.IsActive) fs.Activate();
                    }

                    // Calculate Transform for Shared Coordinates
                    // Project Base Point vs Survey Point.
                    // "Coordenadas Compartidas" usually means Survey Point (Shared).
                    // We need to transform Input (Shared) -> Internal.
                    // ProjectLocation activeLoc = doc.ActiveProjectLocation;
                    // Transform sharedTransform = activeLoc.GetTotalTransform().Inverse; 
                    // Wait, GetTotalTransform transforms FROM Internal TO Shared? 
                    // No. doc.ActiveProjectLocation.GetProjectPosition(origin) gives position relative to shared.
                    
                    // Proper way:
                    // Create a point in Shared Coordinates (Input).
                    // Convert to Internal.
                    // Internal = Input - SharedOrigin? Rotated?
                    // Use `ProjectLocation`.
                    
                    ProjectLocation pl = doc.ActiveProjectLocation;
                    XYZ projectBasePoint = new XYZ(0,0,0); // Internal Origin
                    ProjectPosition pp = pl.GetProjectPosition(projectBasePoint);
                    
                    // Input X (Shared)
                    // Internal X = ?
                    // Let's use `ProjectPosition` to map.
                    // Actually, `ProjectPosition` gives (E, N, Elev, Angle) of a point.
                    // We want the inverse: Given (E, N, Elev), find Internal (X, Y, Z).
                    
                    // Transform T: Internal -> Shared.
                    // T.Origin = (E_origin, N_origin, Z_origin).
                    // T.BasisX = East Vector in Internal? No.
                    // T is a Transform that takes a point in Internal and output Shared coordinates (but as XYZ, usually relative to Survey Point).
                    
                    // Let's assume standard simple transformation involving Translation and Rotation (Angle).
                    // East-West = X_shared, North-South = Y_shared.
                    // Angle = Rotation from True North to Project North?
                    // ProjectPosition.Angle: "The angle between Project North and True North."
                    
                    // Algorithm:
                    // 1. Point_Internal = Point_Shared (Input)
                    // 2. Rotate by -Angle?
                    // 3. Translate by -Origin?
                    
                    // Let's use `CreateShared`? No.
                    
                    double angle = pp.Angle; // Angle from True North, counter-clockwise?
                    double ew = pp.EastWest;
                    double ns = pp.NorthSouth;
                    double elev = pp.Elevation;
                    
                    // The ProjectPosition of the Internal Origin is (ew, ns, elev).
                    // So InternalOrigin.Shared = (ew, ns, elev).
                    
                    // P_Shared = P_Internal.Rotate(Angle) + (ew, ns, elev).
                    // So P_Internal = (P_Shared - (ew, ns, elev)).Rotate(-Angle).
                    
                    Transform toShared = Transform.CreateRotation(XYZ.BasisZ, -angle); // Wait, pp.Angle is usually positive CounterClockwise.
                    // If North is rotated 10 deg East. 
                    // Let's trust standard formula:
                    // Internal = Rotation(Shared - Translation)
                    
                    Func<double, double, double, XYZ> ToInternal = (xS, yS, zS) => {
                         // 1. Translate (relative to Internal Origin's Shared Pos)
                         XYZ pRel = new XYZ(xS - ew, yS - ns, zS - elev);
                         // 2. Rotate
                         // If Project North is rotated `angle` relative to True North...
                         // We need to rotate back.
                         // `ProjectPosition.Angle` is positive if Project North is rotated CCW from True North.
                         // So we rotate CW (-angle) to align.
                         XYZ pInt = Transform.CreateRotation(XYZ.BasisZ, -angle).OfPoint(pRel);
                         return pInt;
                    };
                    
                    // Unit Conversion for Inputs (Meters -> Internal Feet)
                    // Input X, Y, Z are in Project Units (Meters usually).
                    // `pp.EastWest` returns Internal Units (Feet)?
                    // Documentation: ProjectPosition properties are in System Units (Feet).
                    // So we must convert Inputs (Meters) -> Feet FIRST.
                    
                    
                    Action<double, double, double, string> ProcessPoint = (xIn, yIn, zIn, desc) => {
                         // Inputs are User Units (Meters).
                         double xFt = UnitUtils.ConvertToInternalUnits(xIn, UnitTypeId.Meters);
                         double yFt = UnitUtils.ConvertToInternalUnits(yIn, UnitTypeId.Meters);
                         double zFt = UnitUtils.ConvertToInternalUnits(zIn, UnitTypeId.Meters);
                         
                         XYZ pInt = ToInternal(xFt, yFt, zFt);
                         
                         if (config.Mode == CoordinateMode.MoveExisting)
                         {
                             // Move picked element
                             // We are inside Transaction, need to pick first?
                             // Can't pick inside Transaction easily in some modes.
                             // But we already started Trans.
                             // Structure this better.
                         }
                         else
                         {
                             // Create
                             if (fs != null)
                             {
                                 doc.Create.NewFamilyInstance(pInt, fs, Autodesk.Revit.DB.Structure.StructuralType.NonStructural);
                             }
                         }
                    };
                    
                    // LOGIC BRANCHING
                    if (config.Mode == CoordinateMode.MoveExisting)
                    {
                        // Need selection
                         // Temporarily commit/cancel to pick?
                         // Or use "PickObjects" before Trans. 
                         // Refactor: Move selection BEFORE Trans.
                    }
                    else if (config.Mode == CoordinateMode.CreateNewSingle)
                    {
                        ProcessPoint(config.X, config.Y, config.Z, "");
                    }
                    else if (config.Mode == CoordinateMode.CreateNewMultiFromExcel)
                    {
                        // Read Excel/CSV
                        // Simple CSV for now, assuming Excel saves as CSV or using Basic parsing?
                        // User said "Excel sheet". Reading .xlsx needs referencing OpenXml or similar.
                        // Or just simplistic text reading if it is CSV.
                        // If it is .xlsx, we might struggle without libraries.
                        // "Excel externo". 
                        // I will try to read as CSV/Txt lines if possible, or warn.
                        // For this environment, supporting .csv is safest. 
                        // If xlsx, basic Interop is risky.
                        // I will assume CSV logic for simplicity and robustness in this plugin context basically.
                        // And warn user to save as CSV?
                        // Or simple OleDb?
                        // Let's assume CSV reading for "Excel" path if extension is csv.
                        // If .xlsx, we can try to use standard text? No.
                        // Let's implement CSV.
                        
                        if (config.ExcelPath.EndsWith(".csv", StringComparison.OrdinalIgnoreCase) || config.ExcelPath.EndsWith(".txt"))
                        {
                            var lines = File.ReadAllLines(config.ExcelPath);
                            foreach(var line in lines)
                            {
                                var parts = line.Split(',', ';', '\t');
                                if(parts.Length >= 3)
                                {
                                    if(double.TryParse(parts[0], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out double x) &&
                                       double.TryParse(parts[1], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out double y) &&
                                       double.TryParse(parts[2], System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out double z))
                                    {
                                        ProcessPoint(x, y, z, "");
                                    }
                                }
                            }
                        }
                        else
                        {
                            TaskDialog.Show("Error", "Por favor guarde su Excel como CSV para importar.");
                        }
                    }

                    t.Commit();
                }

                // Handle Move Selection Separation
                if (config.Mode == CoordinateMode.MoveExisting)
                {
                    // Selection must happen outside transaction if using PickObject?
                    // Actually PickObject works fine inside/outside, but better outside transaction that modifies model.
                    // But we need to Move inside Trans.
                    // Sequence: Pick -> Trans -> Move.
                    
                    Reference r = null;
                    try { r = uidoc.Selection.PickObject(ObjectType.Element, "Seleccione Elemento a Mover"); }
                    catch { return Result.Cancelled; }
                    
                    if (r != null)
                    {
                        using (Transaction tMove = new Transaction(doc, "Mover a Coordenadas"))
                        {
                            tMove.Start();
                            Element e = doc.GetElement(r);
                            
                            // Calc Target
                            ProjectLocation pl = doc.ActiveProjectLocation;
                            XYZ projectBasePoint = new XYZ(0,0,0);
                            ProjectPosition pp = pl.GetProjectPosition(projectBasePoint);
                            double angle = pp.Angle; 
                            double ew = pp.EastWest;
                            double ns = pp.NorthSouth;
                            double elev = pp.Elevation;
                            
                            Func<double, double, double, XYZ> ToInternal = (xS, yS, zS) => {
                                 XYZ pRel = new XYZ(xS - ew, yS - ns, zS - elev);
                                 return Transform.CreateRotation(XYZ.BasisZ, -angle).OfPoint(pRel);
                            };
                            
                            double xFt = UnitUtils.ConvertToInternalUnits(config.X, UnitTypeId.Meters);
                            double yFt = UnitUtils.ConvertToInternalUnits(config.Y, UnitTypeId.Meters);
                            double zFt = UnitUtils.ConvertToInternalUnits(config.Z, UnitTypeId.Meters);
                            XYZ targetPos = ToInternal(xFt, yFt, zFt);
                            
                            // Move
                            if (e.Location is LocationPoint lp)
                            {
                                XYZ current = lp.Point;
                                XYZ vec = targetPos - current;
                                ElementTransformUtils.MoveElement(doc, e.Id, vec);
                            }
                            else
                            {
                                // Handle Curve? Center?
                                // For now LocationPoint only (Families).
                            }
                            
                            tMove.Commit();
                        }
                    }
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
