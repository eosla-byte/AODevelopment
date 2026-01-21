using System;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public class VGMasterConfig
    {
        // Projection Lines
        public bool OverrideProjLines { get; set; } = false;
        public Color ProjLineColor { get; set; } = new Color(0,0,0);
        public int ProjLineWeight { get; set; } = -1; // -1 = No override

        // Cut Lines
        public bool OverrideCutLines { get; set; } = false;
        public Color CutLineColor { get; set; } = new Color(0, 0, 0);
        public int CutLineWeight { get; set; } = -1;

        // Surface Patterns (Foreground)
        public bool OverrideSurfacePattern { get; set; } = false;
        public Color SurfacePatternColor { get; set; } = new Color(128, 128, 128);
        public bool SolidFillSurface { get; set; } = false;

        // General
        public bool ApplyHalftone { get; set; } = false;
        public int Transparency { get; set; } = 0; // 0-100

        public bool ResetOverrides { get; set; } = false;
    }
}
