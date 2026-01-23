using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.UI;

namespace RevitCivilConnector.Commands
{
    [Autodesk.Revit.Attributes.Transaction(Autodesk.Revit.Attributes.TransactionMode.Manual)]
    public class CivilDataCommand : IExternalCommand
    {
        public static CivilDataWindow Window = null;

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                if (Window == null || !Window.IsLoaded)
                {
                    Window = new CivilDataWindow(commandData.Application);
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
