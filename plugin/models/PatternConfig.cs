using System;
using System.Collections.Generic;
using System.Windows;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public class PatternLine
    {
        public System.Windows.Point Start { get; set; }
        public System.Windows.Point End { get; set; }
    }

    public class PatternConfig
    {
        public string Name { get; set; } = "New Pattern";
        public bool IsModelPattern { get; set; } = true;
        public double TileWidth { get; set; } = 1.0; // Units?
        public double TileHeight { get; set; } = 1.0;
        public List<PatternLine> Lines { get; set; } = new List<PatternLine>();
    }
}
