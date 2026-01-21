using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public class VegetationScatterConfig
    {
        public List<FamilySymbol> SelectedFamilies { get; set; } = new List<FamilySymbol>();
        
        // Density / Count
        public bool UseFixedCount { get; set; } = false;
        public int TotalCount { get; set; } = 50;
        public double Spacing { get; set; } = 2.0; // Meters, average spacing logic

        // Randomization
        public double MinScale { get; set; } = 0.8;
        public double MaxScale { get; set; } = 1.2;
        public bool RandomRotation { get; set; } = true;
        
        public double BaseOffset { get; set; } = 0.0;
    }
}
