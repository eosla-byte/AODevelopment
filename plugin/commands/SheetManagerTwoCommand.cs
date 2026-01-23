using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.ui;

namespace RevitCivilConnector.Commands
{
    [Transaction(TransactionMode.Manual)]
    public class SheetManagerTwoCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;

            try
            {
                // 1. Obtener TitleBlocks disponibles
                var titleBlocks = new FilteredElementCollector(doc)
                    .OfClass(typeof(FamilySymbol))
                    .OfCategory(BuiltInCategory.OST_TitleBlocks)
                    .Cast<FamilySymbol>()
                    .ToList();

                if (titleBlocks.Count == 0)
                {
                    TaskDialog.Show("Error", "No se encontraron familias de TitleBlock cargadas en el proyecto.");
                    return Result.Failed;
                }

                // 2. Mostrar Ventana
                SheetManagerTwoWindow win = new SheetManagerTwoWindow(titleBlocks);
                win.ShowDialog();

                if (!win.IsConfirmed) return Result.Cancelled;

                // 3. Procesar Archivo
                string csvPath = win.CsvPath;
                bool hasHeader = win.IgnoreHeaders;
                ElementId tbId = win.SelectedTitleBlockId;

                List<string[]> rows = new List<string[]>();
                using (var reader = new StreamReader(csvPath))
                {
                    while (!reader.EndOfStream)
                    {
                        var line = reader.ReadLine();
                        if (string.IsNullOrWhiteSpace(line)) continue;
                        rows.Add(line.Split(',')); // Asumimos coma simple por ahora
                    }
                }

                if (rows.Count == 0) return Result.Cancelled;

                // 4. Identificar Columnas Opciónales (Parámetros)
                string[] headers = null;
                int startRow = 0;

                if (hasHeader)
                {
                    headers = rows[0];
                    startRow = 1;
                }

                // 5. Ejecutar Transacción
                using (Transaction t = new Transaction(doc, "Sheet Manager 2.0 import"))
                {
                    t.Start();
                    
                    int created = 0;
                    int updated = 0;
                    string report = "";

                    // Cache de Sheets existentes
                    var existingSheets = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewSheet))
                        .Cast<ViewSheet>()
                        .ToList();

                    for (int i = startRow; i < rows.Count; i++)
                    {
                        var cols = rows[i];
                        if (cols.Length < 1) continue;

                        string num = cols[0].Trim();
                        string name = cols.Length > 1 ? cols[1].Trim() : "";
                        
                        // Buscar si existe
                        ViewSheet sheet = existingSheets.FirstOrDefault(s => s.SheetNumber.Equals(num, StringComparison.InvariantCultureIgnoreCase));
                        
                        if (sheet == null)
                        {
                            try
                            {
                                sheet = ViewSheet.Create(doc, tbId);
                                sheet.SheetNumber = num;
                                sheet.Name = !string.IsNullOrEmpty(name) ? name : "Unnamed";
                                created++;
                            }
                            catch (Exception ex)
                            {
                                report += $"Error creando {num}: {ex.Message}\n";
                                continue;
                            }
                        }
                        else
                        {
                            // Actualizar Nombre si viene definido
                            if (!string.IsNullOrEmpty(name)) sheet.Name = name;
                            updated++;
                        }

                        // Actualizar Parámetros Dinámicos (Columnas 2+)
                        if (headers != null && cols.Length > 2)
                        {
                            for (int c = 2; c < cols.Length; c++)
                            {
                                if (c >= headers.Length) break;
                                string paramName = headers[c].Trim();
                                string val = cols[c].Trim();

                                Parameter p = sheet.LookupParameter(paramName);
                                if (p != null && !p.IsReadOnly)
                                {
                                    if (p.StorageType == StorageType.String) p.Set(val);
                                    else if (p.StorageType == StorageType.Double)
                                    {
                                        if (double.TryParse(val, out double d)) p.Set(d);
                                    }
                                    else if (p.StorageType == StorageType.Integer)
                                    {
                                        if (int.TryParse(val, out int n)) p.Set(n);
                                    }
                                }
                            }
                        }
                    }

                    t.Commit();
                    TaskDialog.Show("Sheet Manager 2.0", $"Proceso Completado.\nCreados: {created}\nActualizados: {updated}\n\n{report}");
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
