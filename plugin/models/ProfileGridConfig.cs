using System;

namespace RevitCivilConnector.models
{
    public class ProfileGridConfig
    {
        public double StationInterval { get; set; } = 10.0; // meters
        public double ElevationBase { get; set; } = 0.0; 
        public double ElevationTop { get; set; } = 0.0; 
        public double ElevationInterval { get; set; } = 0.50; // meters
        public bool AutoElevation { get; set; } = true;
        
        public string ViewName { get; set; } = "Perfil Longitudinal";
        
        public string SectionNamePrefix { get; set; } = "SECCION";
        public Autodesk.Revit.DB.ElementId SelectedTemplateId { get; set; } = Autodesk.Revit.DB.ElementId.InvalidElementId;

        // Extensions
        public double AxisExtensionLength { get; set; } = 2.0; // meters
        public double PlanTickSize { get; set; } = 2.0; // meters - Total length of tick in plan

        // Line Styles (Names)
        public string FrameLineStyle { get; set; } = "Wide Lines"; // Borde
        public string GridLineStyle { get; set; } = "Thin Lines"; // Interior
        public string ExtensionLineStyle { get; set; } = "Medium Lines"; // Proyecciones
    }
}
