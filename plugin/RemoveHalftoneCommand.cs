using System;
using System.Collections.Generic;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class RemoveHalftoneCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;
            View activeView = doc.ActiveView;

            try
            {
                ICollection<ElementId> selectedIds = uidoc.Selection.GetElementIds();

                if (selectedIds.Count == 0)
                {
                    TaskDialog.Show("Remove Halftone", "Por favor seleccione elementos para remover Halftone.");
                    return Result.Cancelled;
                }

                using (Transaction t = new Transaction(doc, "Remove Halftone"))
                {
                    t.Start();
                    
                    foreach (ElementId id in selectedIds)
                    {
                        try
                        {
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
