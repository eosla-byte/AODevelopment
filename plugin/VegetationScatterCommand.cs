using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using RevitCivilConnector.models;
using RevitCivilConnector.services;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class VegetationScatterCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Select the Polygon (Chain of Lines)
                // We ask user to pick one line, then we try to find the connected loop?
                // Or "Pick Objects" logic.
                
                // Let's use PickObjects (Multiple) and assume they form a loop.
                IList<Reference> refs = null;
                try
                {
                    refs = uidoc.Selection.PickObjects(ObjectType.Element, new CurveFilter(), "Selecciona las líneas que forman el polígono cerrado (y pulsa Finalizar).");
                }
                catch (Autodesk.Revit.Exceptions.OperationCanceledException)
                {
                    return Result.Cancelled;
                }

                if (refs == null || refs.Count < 3)
                {
                    message = "Necesitas al menos 3 líneas para un polígono.";
                    return Result.Failed;
                }

                List<Curve> loop = new List<Curve>();
                foreach(var r in refs)
                {
                    Element e = doc.GetElement(r);
                    if (e is ModelLine ml) loop.Add(ml.GeometryCurve);
                    else if (e is DetailLine dl) loop.Add(dl.GeometryCurve);
                }

                // 2. Open Config Window
                VegetationScatterConfig config = null;
                try
                {
                    VegetationScatterWindow win = new VegetationScatterWindow(doc);
                    win.ShowDialog();
                    if (!win.IsConfirmed) return Result.Cancelled;
                    config = win.Config;
                }
                catch(Exception ex) 
                {
                    message = "Error en UI: " + ex.Message;
                    return Result.Failed;
                }

                using (Transaction t = new Transaction(doc, "Scatter Vegetation"))
                {
                    t.Start();
                    
                    VegetationScatterService.ScatterVegetation(doc, loop, config);
                    
                    t.Commit();
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message + "\n" + ex.StackTrace;
                return Result.Failed;
            }
        }
        
        public class CurveFilter : ISelectionFilter
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
