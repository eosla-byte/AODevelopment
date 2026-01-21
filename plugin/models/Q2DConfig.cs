using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public enum Q2DMode
    {
        Count,
        Area_M2,
        Volume_M3,
        Linear_ML
    }

    public class Q2DConfig
    {
        public Q2DMode Mode { get; set; } = Q2DMode.Count;
        public ElementId SelectedCategoryId { get; set; }
        public WorksetId SelectedWorksetId { get; set; }
        
        // New: The specific Takeoff Type being used/edited
        public TakeoffType ActiveTakeoffType { get; set; }

        // Graphics (Legacy or Override)
        public byte ColorR { get; set; } = 255;
        public byte ColorG { get; set; } = 0;
        public byte ColorB { get; set; } = 0;
        public int Transparency { get; set; } = 0; // 0-100
        public int LineWeight { get; set; } = 1; // 1-16

        // Dimensions
        public double VolumeHeight { get; set; } = 3.0; // Meters, default
        
        // State
        public bool IsConfirmed { get; set; } = false;
        
        // Session Data
        public System.Data.DataTable ResultsTable { get; set; }
        public bool WantsToMeasure { get; set; } = false;

        public Q2DConfig()
        {
            ResultsTable = new System.Data.DataTable("Quantification");
            ResultsTable.Columns.Add("ID", typeof(int));
            ResultsTable.Columns.Add("Category", typeof(string));
            ResultsTable.Columns.Add("Type", typeof(string)); // Area, Vol, etc.
            ResultsTable.Columns.Add("BaseQuantity", typeof(double));
            ResultsTable.Columns.Add("Unit", typeof(string));
            // User can add more columns later
        }
    }
}
