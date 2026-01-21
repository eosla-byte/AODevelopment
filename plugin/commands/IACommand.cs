using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.UI;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class IACommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                // Ensure we are on UI thread (Revit logic handles this, but good to know)
                IAWindow window = new IAWindow();
                window.Show(); // Non-blocking (modeless-like behavior on top)
                
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
