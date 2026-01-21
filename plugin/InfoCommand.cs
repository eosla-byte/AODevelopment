
using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class InfoCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            var sb = new System.Text.StringBuilder();
            sb.AppendLine("AO Plugin v1.0");
            sb.AppendLine("Desarrollado para AO Development.\n");
            sb.AppendLine("Contacto Ventas: proyectos@somosao.com\n");
            
            sb.AppendLine("--- Debug Permissions ---");
            if (Autodesk.Revit.UI.TaskDialog.Show("AO Debug", "Ver detalles de permisos?", TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No) == TaskDialogResult.Yes)
            {
                var perms = RevitCivilConnector.Auth.AuthService.Instance.UserPermissions;
                if (perms != null)
                {
                    foreach (var kvp in perms)
                    {
                        sb.AppendLine($"{kvp.Key}: {kvp.Value}");
                    }
                }
                else
                {
                    sb.AppendLine("No permissions loaded.");
                }
                TaskDialog.Show("AO Info", sb.ToString());
            }
            else
            {
                TaskDialog.Show("AO Development", "AO Plugin v1.0\nDesarrollado para AO Development.\n\nSincronización Cloud y Herramientas de Productividad.\n\nContacto Ventas: proyectos@somosao.com");
            }
            return Result.Succeeded;
        }
    }
}
