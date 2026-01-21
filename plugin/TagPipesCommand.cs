using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Selection;
using RevitCivilConnector.models;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class TagPipesCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Gather Data for UI
                // Available Categories for MEP
                List<string> categories = new List<string> {
                    "Tuberías", "Ductos", "Bandeja de Cables", "Tubos (Conduit)", "Tuberías Flexibles", "Ductos Flexibles" 
                };
                // Map to BuiltInCategories
                Dictionary<string, BuiltInCategory> catMap = new Dictionary<string, BuiltInCategory>
                {
                    { "Tuberías", BuiltInCategory.OST_PipeCurves },
                    { "Ductos", BuiltInCategory.OST_DuctCurves },
                    { "Bandeja de Cables", BuiltInCategory.OST_CableTray },
                    { "Tubos (Conduit)", BuiltInCategory.OST_Conduit },
                    { "Tuberías Flexibles", BuiltInCategory.OST_FlexPipeCurves },
                    { "Ductos Flexibles", BuiltInCategory.OST_FlexDuctCurves }
                };

                // Available Tags
                // We need to find Tags compatible with these categories. 
                // For simplicity, we list ALL Multicategory Tags or Specific Tags? 
                // It's hard to filter tags by "Can tag Pipe" without context. 
                // We will collect ALL Generic Tags or specific MEP Tags.
                // Better approach: Collect FamilySymbols of Category "OST_PipeTags", "OST_DuctTags", etc. 
                // But user might want to tag Pipes with a Multi-Category Tag.
                // Let's collect all symbols that are Tags.
                
                var tagCategories = new List<BuiltInCategory> { 
                    BuiltInCategory.OST_PipeTags, BuiltInCategory.OST_DuctTags, 
                    BuiltInCategory.OST_CableTrayTags, BuiltInCategory.OST_ConduitTags,
                    BuiltInCategory.OST_MultiCategoryTags 
                };
                
                ElementMulticategoryFilter tagCatFilter = new ElementMulticategoryFilter(tagCategories);
                List<FamilySymbol> tags = new FilteredElementCollector(doc)
                    .WherePasses(tagCatFilter)
                    .WhereElementIsElementType()
                    .Cast<FamilySymbol>()
                    .ToList();
                
                // 2. Show UI
                TagPipesWindow win = new TagPipesWindow(tags, categories);
                win.ShowDialog();

                if (!win.IsConfirmed) return Result.Cancelled;
                
                TagPipesConfig config = win.Config;

                // 3. Collect Elements
                List<Element> elementsToTag = new List<Element>();
                BuiltInCategory targetCat = catMap.ContainsKey(config.TargetCategory) ? catMap[config.TargetCategory] : BuiltInCategory.OST_PipeCurves;

                if (config.SelectByView)
                {
                    FilteredElementCollector col = new FilteredElementCollector(doc, doc.ActiveView.Id)
                        .OfCategory(targetCat)
                        .WhereElementIsNotElementType();
                    
                    foreach(Element e in col)
                    {
                        if (!string.IsNullOrEmpty(config.FilterParamName))
                        {
                            Parameter p = e.LookupParameter(config.FilterParamName);
                            if (p == null || !p.AsString().Equals(config.FilterParamValue, StringComparison.OrdinalIgnoreCase)) continue;
                        }
                        elementsToTag.Add(e);
                    }
                }
                else
                {
                    // Manual Selection
                    try
                    {
                        IList<Reference> refs = uidoc.Selection.PickObjects(ObjectType.Element, new MEPSelectionFilter(targetCat), "Seleccione elementos MEP");
                        foreach (Reference r in refs) elementsToTag.Add(doc.GetElement(r));
                    }
                    catch (Autodesk.Revit.Exceptions.OperationCanceledException) { return Result.Cancelled; }
                }

                if (elementsToTag.Count == 0)
                {
                    TaskDialog.Show("Info", "No se encontraron elementos.");
                    return Result.Cancelled;
                }

                // 4. Tag Transaction
                using (Transaction t = new Transaction(doc, "Tag MEP Elements"))
                {
                    t.Start();
                    
                    int count = 0;
                    foreach (Element e in elementsToTag)
                    {
                        if (!(e.Location is LocationCurve lc)) continue;
                        Curve curve = lc.Curve;

                        // Calculate Points
                        XYZ pStart = curve.GetEndPoint(0);
                        XYZ pEnd = curve.GetEndPoint(1);
                        XYZ pMid = curve.Evaluate(0.5, true);
                        
                        // Vector for Offset
                        // Assuming ReferenceLevel or current view plane
                        // MEP curves usually horizontal-ish. 
                        // Cross product with Z to get "Side" vector.
                        XYZ dir = (pEnd - pStart).Normalize();
                        XYZ up = XYZ.BasisZ;
                        XYZ side = dir.CrossProduct(up);
                        if (side.IsZeroLength()) side = new XYZ(1, 0, 0); // Vertical pipe case
                        
                        // Start
                        if (config.StartTag.Enabled) 
                            CreateTag(doc, e, pStart, side, config.StartTag);

                        // Mid
                        if (config.MidTag.Enabled) 
                            CreateTag(doc, e, pMid, side, config.MidTag);

                        // End
                        if (config.EndTag.Enabled) 
                            CreateTag(doc, e, pEnd, side, config.EndTag);
                        
                        count++;
                    }

                    t.Commit();
                    TaskDialog.Show("Info", $"Se etiquetaron {count} elementos.");
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }

        private void CreateTag(Document doc, Element target, XYZ point, XYZ sideVector, TagPositionConfig conf)
        {
            if (conf.TagSymbolId == ElementId.InvalidElementId) return;
            
            // Calc Offset Position
            // Offset defines perpendicular distance.
            // If checking "Offset", does user mean "Offset from line" or "Offset from View"? 
            // Usually "Side".
            // Convert Meters to Internal
            double offsetFt = UnitUtils.ConvertToInternalUnits(conf.Offset, UnitTypeId.Meters);
            XYZ tagPos = point + sideVector * offsetFt;

            // Create Tag
            IndependentTag tag = IndependentTag.Create(doc, conf.TagSymbolId, doc.ActiveView.Id, new Reference(target), 
                conf.HasLeader, TagOrientation.Horizontal, tagPos); // Init Horizontal

            if (tag == null) return;

            // Orientation
            tag.TagOrientation = conf.Orientation;

            // Leader
            tag.HasLeader = conf.HasLeader;
            if (conf.HasLeader)
            {
                // Optionally adjust leader elbow/end?
                // Default leader usually fine, points to element.
            }
        }

        public class MEPSelectionFilter : ISelectionFilter
        {
            private BuiltInCategory _cat;
            public MEPSelectionFilter(BuiltInCategory cat) { _cat = cat; }
            public bool AllowElement(Element elem)
            {
                return elem.Category != null && elem.Category.Id.Value == (long)_cat;
            }
            public bool AllowReference(Reference reference, XYZ position) { return true; }
        }
    }
}
