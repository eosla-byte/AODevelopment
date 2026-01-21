using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public enum DWGTarget
    {
        DraftingView,
        LegendView,
        ActiveView,
        DetailItemFamily,
        GenericAnnotationFamily,
        GenericModelFamily
    }

    public class DWGImportConfig
    {
        public string FilePath { get; set; }
        public string TargetName { get; set; }
        public DWGTarget TargetType { get; set; } = DWGTarget.DraftingView;
        
        // Mappings
        public string SelectedLineStyle { get; set; } // Global override or default
        public string SelectedTextType { get; set; }
        public string SelectedFillRegionType { get; set; } // For hatches

        // Options
        public bool CreateMaskingRegion { get; set; } = false;
        public bool SaveFamilyToDisk { get; set; } = true;
        public string FamilySavePath { get; set; }
    }
}
