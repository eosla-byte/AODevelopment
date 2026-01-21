using System;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public enum CoordinateMode
    {
        MoveExisting,
        CreateNewSingle,
        CreateNewMultiFromExcel
    }

    public class CoordinatesConfig
    {
        public CoordinateMode Mode { get; set; } = CoordinateMode.MoveExisting;
        
        // Single Move/Create Params
        public double X { get; set; } = 0;
        public double Y { get; set; } = 0;
        public double Z { get; set; } = 0;
        
        // Family Symbol for Creation (Single or Multi)
        public ElementId SelectedFamilySymbolId { get; set; } = ElementId.InvalidElementId;
        
        // Excel Path
        public string ExcelPath { get; set; } = "";
    }
}
