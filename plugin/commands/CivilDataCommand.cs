using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.UI;
using RevitCivilConnector.Services;

namespace RevitCivilConnector.Commands
{
    [Autodesk.Revit.Attributes.Transaction(Autodesk.Revit.Attributes.TransactionMode.Manual)]
    public class CivilDataCommand : IExternalCommand
    {
        public static CivilDataWindow Window = null;
        public static CivilImportHandler ImportHandler = null;
        public static ExternalEvent ImportEvent = null;

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                if (Window == null || !Window.IsLoaded)
                {
                    ImportHandler = new Services.CivilImportHandler();
                    ImportEvent = ExternalEvent.Create(ImportHandler);
                    Window = new CivilDataWindow(commandData.Application, ImportHandler, ImportEvent);
                    Window.Show();
                }
                else
                {
                    Window.Activate();
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
