using System;
using System.Collections.Generic;
using Autodesk.Revit.UI;
using RevitCivilConnector.Models;

namespace RevitCivilConnector.Services
{
    public class CivilImportHandler : IExternalEventHandler
    {
        public List<CivilElement> ElementsToImport { get; set; }
        public bool UseSharedCoordinates { get; set; }

        public void Execute(UIApplication app)
        {
            if (ElementsToImport == null || ElementsToImport.Count == 0) return;

            var svc = new RevitCivilGeometry(app);
            try
            {
                svc.CreateGeometry(ElementsToImport, UseSharedCoordinates);
                System.Windows.MessageBox.Show($"Successfully imported {ElementsToImport.Count} elements.");
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show("Error importing: " + ex.Message);
            }
        }

        public string GetName()
        {
            return "Civil Import Handler";
        }
    }
}
