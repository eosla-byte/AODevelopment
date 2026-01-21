using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.models;
using RevitCivilConnector.services;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class DWGToNativeCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Autodesk.Revit.ApplicationServices.Application app = commandData.Application.Application;
            Document mainDoc = uidoc.Document;

            try
            {
                // 1. Config UI
                DWGImportWindow win = new DWGImportWindow(mainDoc);
                win.ShowDialog();
                if (!win.IsConfirmed) return Result.Cancelled;
                DWGImportConfig config = win.Config;

                // 2. Determine Workflow: Project View vs Family Document
                bool isFamilyTarget = config.TargetType == DWGTarget.DetailItemFamily ||
                                      config.TargetType == DWGTarget.GenericAnnotationFamily ||
                                      config.TargetType == DWGTarget.GenericModelFamily;

                if (isFamilyTarget)
                {
                    // --- FAMILY WORKFLOW ---
                    // a) Find Template
                    string templatePath = GetTemplatePath(app, config.TargetType);
                    if (!File.Exists(templatePath))
                    {
                        message = "No se encontró la plantilla de familia adecuada en la ruta por defecto.";
                        return Result.Failed;
                    }

                    // b) Create Document
                    Document famDoc = app.NewFamilyDocument(templatePath);
                    if (famDoc == null) return Result.Failed;

                    // c) Process in Family
                    using (Transaction t = new Transaction(famDoc, "Import DWG Family"))
                    {
                        t.Start();
                        // Import into Active View of Family (usually Ref Level)
                        DWGProcessService.ProcessImport(famDoc, new DWGImportConfig 
                        { 
                            FilePath = config.FilePath,
                            TargetType = DWGTarget.ActiveView, // Always active inside family logic
                            TargetName = "Import",
                            SelectedLineStyle = config.SelectedLineStyle, // Note: Family might not have same styles. 
                                                                        // We should ideally create them or map to existing.
                                                                        // For now, names usually differ. 
                                                                        // We might ignore mapping if styles missing in template.
                            SelectedTextType = config.SelectedTextType,
                            SelectedFillRegionType = config.SelectedFillRegionType
                        });
                        t.Commit();
                    }

                    // d) Save
                    if (!string.IsNullOrEmpty(config.FamilySavePath))
                    {
                         SaveAsOptions sao = new SaveAsOptions { OverwriteExistingFile = true };
                         famDoc.SaveAs(config.FamilySavePath, sao);
                    }

                    // e) Load into Project
                    Family loadedFam = famDoc.LoadFamily(mainDoc);
                    famDoc.Close(false);

                    if (loadedFam != null)
                    {
                        TaskDialog.Show("Success", $"Familia '{loadedFam.Name}' creada e importada.");
                        if (loadedFam.GetFamilySymbolIds().Count > 0)
                        {
                            ElementId symId = loadedFam.GetFamilySymbolIds().First();
                            FamilySymbol sym = mainDoc.GetElement(symId) as FamilySymbol;
                            if (sym != null)
                            {
                                TaskDialog.Show("Success", $"Familia '{loadedFam.Name}' creada e importada. Coloca una instancia.");
                                uidoc.PostRequestForElementTypePlacement(sym);
                            }
                        }
                    }
                }
                else
                {
                    // --- PROJECT VIEW WORKFLOW ---
                    using (Transaction t = new Transaction(mainDoc, "Import DWG Native"))
                    {
                        t.Start();
                        DWGProcessService.ProcessImport(mainDoc, config);
                        t.Commit();
                    }
                    
                    // Activate view if created?
                    // If we created a Drafting View, we can open it.
                    // But we can't change view inside Transaction easily, and simple API call works outside.
                    // We need the ID of the created view. 
                    // ProcessImport void doesn't return it.
                    // Improvement: Make ProcessImport return View.
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message + "\n" + ex.StackTrace;
                return Result.Failed;
            }
        }

        private string GetTemplatePath(Autodesk.Revit.ApplicationServices.Application app, DWGTarget target)
        {
            // Try to find standard templates based on Revit installation
            // Usually C:\ProgramData\Autodesk\RVT 2024\Family Templates\English\
            // We can ask app for FamilyTemplatePath?
            // Or just allow user to pick if generic fails?
            // Let's iterate likely paths.
            
            string root = app.FamilyTemplatePath; // User setting
            if (string.IsNullOrEmpty(root) || !Directory.Exists(root))
                root = @"C:\ProgramData\Autodesk\RVT 2024\Family Templates\English\"; // Fallback

            string name = "";
            switch (target)
            {
                case DWGTarget.DetailItemFamily: name = "Metric Detail Item.rft"; break;
                case DWGTarget.GenericAnnotationFamily: name = "Metric Generic Annotation.rft"; break;
                case DWGTarget.GenericModelFamily: name = "Metric Generic Model.rft"; break;
                default: name = "Metric Generic Model.rft"; break;
            }
            
            string full = Path.Combine(root, name);
            if (!File.Exists(full))
            {
                // Try to find ANY .rft with partial match?
                // Or try spanish "Elemento de detalle metrico.rft"
                string esName = "";
                switch (target)
                {
                    case DWGTarget.DetailItemFamily: esName = "Elemento de detalle métrico.rft"; break;
                    case DWGTarget.GenericAnnotationFamily: esName = "Anotación genérica métrica.rft"; break;
                    case DWGTarget.GenericModelFamily: esName = "Modelo genérico métrico.rft"; break;
                }
                full = Path.Combine(root, esName);
            }
            
            return full;
        }
    }
}
