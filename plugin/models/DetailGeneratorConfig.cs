using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.models
{
    public class DetailGeneratorConfig
    {
        public bool Create3D { get; set; } = true;
        public bool CreatePlan { get; set; } = true;
        public bool CreateSectionLong { get; set; } = true;
        public bool CreateSectionTrans { get; set; } = true;

        // True = Isolate, False = Halftone Context
        public bool Mode3DIsolate { get; set; } = false;
        public bool ModePlanIsolate { get; set; } = false;
        public bool ModeSectionLongIsolate { get; set; } = false;
        public bool ModeSectionTransIsolate { get; set; } = false;

        // View Template IDs
        public ElementId Template3DId { get; set; } = ElementId.InvalidElementId;
        public ElementId TemplatePlanId { get; set; } = ElementId.InvalidElementId;
        public ElementId TemplateSectionId { get; set; } = ElementId.InvalidElementId;

        public string Prefix { get; set; } = "";
        public string BaseName { get; set; } = "Detail";
        public string Suffix { get; set; } = "";
    }
}
