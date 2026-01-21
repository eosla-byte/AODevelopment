using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.models;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class CreateDetailViewsCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            // 1. Get Selection
            ICollection<ElementId> selectedIds = uidoc.Selection.GetElementIds();
            if (selectedIds.Count == 0)
            {
                TaskDialog.Show("Generar Detalles", "Seleccione elementos primero.");
                return Result.Cancelled;
            }

            // 2. Open UI
            DetailGeneratorConfig config = null;
            
            try 
            {
                // Collect View Templates
                List<View> templates = new FilteredElementCollector(doc)
                    .OfClass(typeof(View))
                    .Cast<View>()
                    .Where(v => v.IsTemplate)
                    .ToList();

                DetailGeneratorWindow win = new DetailGeneratorWindow(templates);
                win.ShowDialog();
                if (!win.IsConfirmed) return Result.Cancelled;
                config = win.Config;
            }
            catch(Exception ex)
            {
                message = "Error mostrando ventana: " + ex.Message;
                return Result.Failed;
            }

            // 3. Calculation
            BoundingBoxXYZ bbox = GetBoundingBoxForSelection(doc, selectedIds);
            if (bbox == null)
            {
                message = "No se pudo calcular el BoundingBox de la seleccion.";
                return Result.Failed;
            }

            // Expand bbox slightly
            double offset = 1.0; // 1 ft
            bbox.Min -= new XYZ(offset, offset, offset);
            bbox.Max += new XYZ(offset, offset, offset);

            using (Transaction t = new Transaction(doc, "Generar Detalles"))
            {
                t.Start();

                string nameBase = $"{config.Prefix}{config.BaseName}{config.Suffix}";

                // 3.1. 3D View
                if (config.Create3D)
                {
                    ViewFamilyType vft3D = new FilteredElementCollector(doc)
                        .OfClass(typeof(ViewFamilyType))
                        .Cast<ViewFamilyType>()
                        .FirstOrDefault(x => x.ViewFamily == ViewFamily.ThreeDimensional);

                    if (vft3D != null)
                    {
                        View3D view3d = View3D.CreateIsometric(doc, vft3D.Id);
                        view3d.Name = GetUniqueViewName(doc, nameBase + "_3D");
                        
                        if (config.Template3DId != ElementId.InvalidElementId)
                            view3d.ViewTemplateId = config.Template3DId;
                            
                        view3d.SetSectionBox(bbox);
                        ApplyVisibility(doc, view3d, selectedIds, config.Mode3DIsolate);
                    }
                }

                // 3.2. Plan View
                // Find level of centroid
                XYZ center = (bbox.Min + bbox.Max) * 0.5;
                Level level = GetClosestLevel(doc, center.Z);

                if (config.CreatePlan && level != null)
                {
                    ViewFamilyType vftPlan = new FilteredElementCollector(doc)
                         .OfClass(typeof(ViewFamilyType))
                         .Cast<ViewFamilyType>()
                         .FirstOrDefault(x => x.ViewFamily == ViewFamily.FloorPlan);

                    if (vftPlan != null)
                    {
                        ViewPlan viewPlan = ViewPlan.Create(doc, vftPlan.Id, level.Id);
                        viewPlan.Name = GetUniqueViewName(doc, nameBase + "_PLANT");
                        
                        if (config.TemplatePlanId != ElementId.InvalidElementId)
                            viewPlan.ViewTemplateId = config.TemplatePlanId;

                        viewPlan.CropBoxActive = true;
                        viewPlan.CropBoxVisible = true;
                        BoundingBoxXYZ crop = viewPlan.CropBox;
                        crop.Min = new XYZ(bbox.Min.X, bbox.Min.Y, crop.Min.Z);
                        crop.Max = new XYZ(bbox.Max.X, bbox.Max.Y, crop.Max.Z);
                        viewPlan.CropBox = crop;

                        ApplyVisibility(doc, viewPlan, selectedIds, config.ModePlanIsolate);
                    }
                }

                // 3.3. Sections
                // Determine Long/Trans
                double dx = Math.Abs(bbox.Max.X - bbox.Min.X);
                double dy = Math.Abs(bbox.Max.Y - bbox.Min.Y);
                bool xIsLong = dx >= dy;

                ViewFamilyType vftSection = new FilteredElementCollector(doc)
                    .OfClass(typeof(ViewFamilyType))
                    .Cast<ViewFamilyType>()
                    .FirstOrDefault(x => x.ViewFamily == ViewFamily.Section);

                if (vftSection != null)
                {
                    if (config.CreateSectionLong)
                    {
                        XYZ dir = xIsLong ? XYZ.BasisY : XYZ.BasisX;
                        BoundingBoxXYZ sectionBox = CreateSectionBox(bbox, dir, center);
                        ViewSection vs = ViewSection.CreateSection(doc, vftSection.Id, sectionBox);
                        vs.Name = GetUniqueViewName(doc, nameBase + "_SECLONG");
                        
                        if (config.TemplateSectionId != ElementId.InvalidElementId)
                            vs.ViewTemplateId = config.TemplateSectionId;
                            
                        ApplyVisibility(doc, vs, selectedIds, config.ModeSectionLongIsolate);
                    }

                    if (config.CreateSectionTrans)
                    {
                        XYZ dir = xIsLong ? XYZ.BasisX : XYZ.BasisY;
                        BoundingBoxXYZ sectionBox = CreateSectionBox(bbox, dir, center);
                        ViewSection vs = ViewSection.CreateSection(doc, vftSection.Id, sectionBox);
                        vs.Name = GetUniqueViewName(doc, nameBase + "_SECTRANS");
                        
                        if (config.TemplateSectionId != ElementId.InvalidElementId)
                            vs.ViewTemplateId = config.TemplateSectionId;

                        ApplyVisibility(doc, vs, selectedIds, config.ModeSectionTransIsolate);
                    }
                }

                t.Commit();
            }

            return Result.Succeeded;
        }

        private BoundingBoxXYZ GetBoundingBoxForSelection(Document doc, ICollection<ElementId> ids)
        {
            BoundingBoxXYZ total = null;
            foreach (ElementId id in ids)
            {
                Element e = doc.GetElement(id);
                BoundingBoxXYZ b = e.get_BoundingBox(null);
                if (b == null) continue;

                if (total == null)
                {
                    total = new BoundingBoxXYZ();
                    total.Min = b.Min;
                    total.Max = b.Max;
                }
                else
                {
                    XYZ newMin = new XYZ(Math.Min(total.Min.X, b.Min.X), Math.Min(total.Min.Y, b.Min.Y), Math.Min(total.Min.Z, b.Min.Z));
                    XYZ newMax = new XYZ(Math.Max(total.Max.X, b.Max.X), Math.Max(total.Max.Y, b.Max.Y), Math.Max(total.Max.Z, b.Max.Z));
                    total.Min = newMin;
                    total.Max = newMax;
                }
            }
            return total;
        }

        private Level GetClosestLevel(Document doc, double z)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .Cast<Level>()
                .OrderBy(l => Math.Abs(l.Elevation - z))
                .FirstOrDefault();
        }

        private string GetUniqueViewName(Document doc, string baseName)
        {
            string name = baseName;
            int counter = 1;
            while (new FilteredElementCollector(doc).OfClass(typeof(View)).Cast<View>().Any(v => v.Name == name))
            {
                name = $"{baseName}_{counter++}";
            }
            return name;
        }

        private BoundingBoxXYZ CreateSectionBox(BoundingBoxXYZ targetBox, XYZ normal, XYZ center)
        {
            Transform t = Transform.Identity;
            t.Origin = center;
            t.BasisZ = normal; 
            XYZ right = XYZ.BasisZ.CrossProduct(normal);
            t.BasisX = right;
            t.BasisY = XYZ.BasisZ;

            double w = Math.Abs(targetBox.Max.X - targetBox.Min.X) + Math.Abs(targetBox.Max.Y - targetBox.Min.Y);
            double h = Math.Abs(targetBox.Max.Z - targetBox.Min.Z);
            double d = w; 

            BoundingBoxXYZ box = new BoundingBoxXYZ();
            box.Transform = t;
            box.Min = new XYZ(-w/2 - 2, -h/2 - 2, -d/2 - 2); 
            box.Max = new XYZ(w/2 + 2, h/2 + 2, d/2 + 2);
            
            return box;
        }

        private void ApplyVisibility(Document doc, View view, ICollection<ElementId> keepIds, bool isolate)
        {
            // If template is applied, some overrides might be locked. 
            // Setting overrides on top of a template that controls them will fail or be ignored specifically for categories.
            // But Element Overrides usually override everything unless "Include" in template is checked?
            // Element overrides take precedence over View Filters, but View Template controls category visibility.
            // If template says "Model Categories" is controlled, we can still hide individual elements? Yes.
            // HideElements works. SetElementOverrides works.

            try { view.Scale = 50; } catch {}
            
            FilteredElementCollector coll = new FilteredElementCollector(doc, view.Id)
                .WhereElementIsNotElementType();

            List<ElementId> toHide = new List<ElementId>();
            OverrideGraphicSettings halftone = new OverrideGraphicSettings();
            halftone.SetHalftone(true);
            
            foreach (Element e in coll)
            {
                if (keepIds.Contains(e.Id)) continue;
                if (!e.CanBeHidden(view)) continue;

                if (isolate)
                {
                    toHide.Add(e.Id);
                }
                else
                {
                    try { view.SetElementOverrides(e.Id, halftone); } catch { }
                }
            }

            if (isolate && toHide.Count > 0)
            {
               if (toHide.Count < 2000) 
                   view.HideElements(toHide);
            }
        }
    }
}
