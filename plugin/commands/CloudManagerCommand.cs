using System;
using System.Diagnostics;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.Auth;

namespace RevitCivilConnector.Commands
{
    [Transaction(TransactionMode.Manual)]
    public class CloudManagerCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            if (!AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("AO Plugin", "Debes iniciar sesión para acceder a Cloud Manager.");
                return Result.Cancelled;
            }

            try
            {
                string url = "https://www.somosao.com/labs/cloud-manager";
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
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
