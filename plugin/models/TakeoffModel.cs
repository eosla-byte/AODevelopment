using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace RevitCivilConnector.models
{
    public enum TakeoffTool
    {
        Area,
        Linear,
        Count,
        Model
    }

    [Serializable]
    public class TakeoffPackage
    {
        public string Id { get; set; }
        public string Name { get; set; } = "General";
        public string Version { get; set; } = "V1";
        public List<TakeoffType> Types { get; set; } = new List<TakeoffType>();
        
        public TakeoffPackage()
        {
            Id = Guid.NewGuid().ToString();
        }
    }

    [Serializable]
    public class TakeoffType
    {
        public string Id { get; set; }
        public string Name { get; set; } = "New Takeoff Type";
        public TakeoffTool Tool { get; set; } = TakeoffTool.Area;
        
        // Appearance
        public string FillColorHex { get; set; } = "#FFA500"; // Orange
        public string BorderColorHex { get; set; } = "#FFA500";
        public int Transparency { get; set; } = 50; // 0-100
        public int LineWidth { get; set; } = 2; // Revit 1-16
        
        // Count specific
        public string CountShape { get; set; } = "Circle"; // Circle, Square
        public double CountSize { get; set; } = 0.5; // Meters

        // Data
        public string Description { get; set; } = "";
        public string PrimaryClassification { get; set; } = "Unassigned";
        public string Unit { get; set; } = "M2"; // M2, M3, ML, EA
        public double Cost { get; set; } = 0.0; // Unit Cost
        
        public double DefaultHeight { get; set; } = 1.0;
        
        // 3D Rules / Filters
        public List<TakeoffRule> Rules { get; set; } = new List<TakeoffRule>();

        public TakeoffType()
        {
            Id = Guid.NewGuid().ToString();
        }
    }

    [Serializable]
    public class TakeoffRule
    {
        public string CategoryName { get; set; } // e.g. "Walls"
        public string ParameterName { get; set; } // e.g. "Type Name", "Mark", "Comments"
        public string Evaluator { get; set; } // "Equals", "Contains", "StartsWith"
        public string Value { get; set; }
    }
}
