
using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.Auth;
using RevitCivilConnector.UI;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class LoginCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            if (AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("Info", $"Ya has iniciado sesión como {AuthService.Instance.CurrentUserName}.");
                return Result.Succeeded;
            }

            var loginWin = new LoginWindow();
            bool? res = loginWin.ShowDialog();

            if (res == true && AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("Exito", "Inicio de sesión correcto.");
                return Result.Succeeded;
            }

            return Result.Cancelled;
        }
    }
}
