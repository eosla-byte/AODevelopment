using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.UI;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class AIMonitorCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                // Only allow if role suggests Admin/Dev - Safety check (redundant if UI hidden but good practice)
                // Actually User might see button if they are "Arquitecto" in Labs.
                // We should let them see it if the button is there.
                
                AIMonitorWindow win = new AIMonitorWindow();
                win.Show(); // Non-blocking
                
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
