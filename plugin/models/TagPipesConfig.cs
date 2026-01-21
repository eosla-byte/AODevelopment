using System;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public class TagPipesConfig
    {
        public bool SelectByView { get; set; } = false; // False = Pick, True = All in View
        public string TargetCategory { get; set; } = "Tuberías"; // Pipes, Ducts...
        public string FilterParamName { get; set; } = "";
        public string FilterParamValue { get; set; } = "";

        public TagPositionConfig StartTag { get; set; } = new TagPositionConfig();
        public TagPositionConfig MidTag { get; set; } = new TagPositionConfig();
        public TagPositionConfig EndTag { get; set; } = new TagPositionConfig();

        public TagPipesConfig()
        {
            // Defaults
            MidTag.Enabled = true;
        }
    }

    public class TagPositionConfig
    {
        public bool Enabled { get; set; } = false;
        public ElementId TagSymbolId { get; set; } = ElementId.InvalidElementId;
        public double Offset { get; set; } = 0.5; // Meters (internal or project units? Let's stick to Project Units logic we fixed: Input is Meters)
        public bool HasLeader { get; set; } = false;
        public TagOrientation Orientation { get; set; } = TagOrientation.Horizontal;
    }
}
