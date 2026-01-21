using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class InverseHalftoneCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;
            View activeView = doc.ActiveView;

            try
            {
                // Obtenemos los IDs seleccionados actualmente
                ICollection<ElementId> selectedIds = uidoc.Selection.GetElementIds();

                if (selectedIds.Count == 0)
                {
                    TaskDialog.Show("Atención", "Por favor seleccione al menos un elemento para mantener visible.");
                    return Result.Cancelled;
                }

                // Recolectamos todos los elementos visibles en la vista actual
                // Excluimos la vista misma y otros elementos no gráficos
                FilteredElementCollector collector = new FilteredElementCollector(doc, activeView.Id)
                    .WhereElementIsNotElementType();

                List<ElementId> idsToHalftone = new List<ElementId>();
                List<ElementId> idsToReset = new List<ElementId>();

                foreach (Element e in collector)
                {
                    // Si está seleccionado, queremos que NO sea halftone
                    if (selectedIds.Contains(e.Id))
                    {
                        idsToReset.Add(e.Id);
                    }
                    else
                    {
                        // Si no está seleccionado y es modificable gráficamente, aplicar halftone
                        if (e.Category != null && e.CanBeHidden(activeView)) 
                        {
                            idsToHalftone.Add(e.Id);
                        }
                    }
                }

                using (Transaction t = new Transaction(doc, "Inverse Halftone"))
                {
                    t.Start();

                    // Aplicar Halftone
                    OverrideGraphicSettings halftoneSettings = new OverrideGraphicSettings();
                    halftoneSettings.SetHalftone(true);

                    foreach (ElementId id in idsToHalftone)
                    {
                         // Verificar si el elemento soporta overrides
                         // (La API no tiene un 'CanHaveOverrides', probamos try-catch o confiamos en Category != null)
                         try 
                         {
                             activeView.SetElementOverrides(id, halftoneSettings);
                         }
                         catch { }
                    }

                    // Quitar Halftone a los seleccionados
                    OverrideGraphicSettings resetSettings = new OverrideGraphicSettings();
                    resetSettings.SetHalftone(false);

                    foreach (ElementId id in idsToReset)
                    {
                        try
                        {
                            // Obtenemos setting actual para no borrar otros overrides (color, line pattern)
                            // La API SetElementOverrides reemplaza todo.
                            // Si queremos preservar otros overrides, primero GetElementOverrides, modificamos Halftone y volvemos a aplicar.
                            OverrideGraphicSettings current = activeView.GetElementOverrides(id);
                            current.SetHalftone(false);
                            activeView.SetElementOverrides(id, current);
                        }
                        catch { }
                    }

                    t.Commit();
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
