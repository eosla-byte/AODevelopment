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
    public class VGMasterCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Get Selection (or prompt)
                ICollection<ElementId> selectedIds = uidoc.Selection.GetElementIds();
                
                if (selectedIds.Count == 0)
                {
                    // Prompt user to select
                    try
                    {
                        IList<Reference> refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecciona elementos para VGMaster");
                        selectedIds = refs.Select(r => r.ElementId).ToList();
                    }
                    catch (Autodesk.Revit.Exceptions.OperationCanceledException)
                    {
                        return Result.Cancelled;
                    }
                }

                if (selectedIds.Count == 0) return Result.Cancelled;

                // 2. Open Configuration Window
                VGMasterWindow win = new VGMasterWindow();
                win.ShowDialog();

                if (!win.IsConfirmed) return Result.Cancelled;

                VGMasterConfig config = win.Config;

                using (Transaction t = new Transaction(doc, "VGMaster Overrides"))
                {
                    t.Start();
                    
                    View view = doc.ActiveView;
                    
                    if (config.ResetOverrides)
                    {
                        foreach(ElementId id in selectedIds)
                        {
                            view.SetElementOverrides(id, new OverrideGraphicSettings());
                        }
                    }
                    else
                    {
                        // Prepare overrides
                        // NOTE: We create a NEW settings object. This replaces existing element overrides.
                        // Ideally we might want to merge, but 'easiest' is full replace for now based on UI state.
                        // Or better: Start with default (NoOverride) and apply only what user checked.
                        
                        OverrideGraphicSettings ogs = new OverrideGraphicSettings();

                        // Projection
                        if (config.OverrideProjLines)
                        {
                            ogs.SetProjectionLineColor(config.ProjLineColor);
                            if (config.ProjLineWeight != -1)
                                ogs.SetProjectionLineWeight(config.ProjLineWeight);
                        }
                        
                        // Cut
                        if (config.OverrideCutLines)
                        {
                            ogs.SetCutLineColor(config.CutLineColor);
                            if (config.CutLineWeight != -1)
                                ogs.SetCutLineWeight(config.CutLineWeight);
                        }

                        // Surface
                        if (config.OverrideSurfacePattern)
                        {
                            ogs.SetSurfaceForegroundPatternColor(config.SurfacePatternColor);
                            if (config.SolidFillSurface)
                            {
                                FillPatternElement solid = GetSolidFillPattern(doc);
                                if (solid != null)
                                    ogs.SetSurfaceForegroundPatternId(solid.Id);
                            }
                            // We can also enable visibility explicitly? 
                            ogs.SetSurfaceForegroundPatternVisible(true);
                        }

                        // Vis
                        if(config.ApplyHalftone) ogs.SetHalftone(true);
                        else ogs.SetHalftone(false); // Force off if not checked? Or default?
                        // If user meant "Don't change", we should have a tristate.
                        // But here we likely want to Apply state from UI.
                        
                        if (config.Transparency > 0)
                            ogs.SetSurfaceTransparency(config.Transparency);

                        // Apply
                        foreach(ElementId id in selectedIds)
                        {
                            // If we want to preserve existing overrides that we didn't touch:
                            // OverrideGraphicSettings existing = view.GetElementOverrides(id);
                            // But merging is complex (how to know if we should clear 'Color' if checkbox unchecked?).
                            // UI implies: Checked = Set Value. Unchecked = Do nothing (Default/NoOverride).
                            // A pure fresh 'ogs' means: Unchecked properties reset to "By Category/Filter".
                            // This effectively "Resets" uncontrolled properties. This is usually desired behavior for a "Master" tool.
                            
                            view.SetElementOverrides(id, ogs);
                        }
                    }

                    t.Commit();
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message + "\n" + ex.StackTrace;
                return Result.Failed;
            }
        }

        private FillPatternElement GetSolidFillPattern(Document doc)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(FillPatternElement))
                .Cast<FillPatternElement>()
                .FirstOrDefault(ap => ap.GetFillPattern().IsSolidFill);
        }
    }
}
