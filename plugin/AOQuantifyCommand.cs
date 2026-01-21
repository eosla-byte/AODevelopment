
using System;
using System.Collections.Generic;
using System.Linq;
using System.Data;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.models;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class AOQuantifyCommand : IExternalCommand
    {
        // Static reference
        public static AOQuantifyWindow CurrentWindow = null;
        public static Document ActiveDocument = null;

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            if (!RevitCivilConnector.Auth.AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("Acceso Denegado", "Debe iniciar sesión en AO Resources para usar esta herramienta.");
                return Result.Cancelled;
            }

            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;
            ActiveDocument = doc;

            // Collect Data (Cats/Worksets) for Rules UI
            List<Category> categories = new List<Category>();
            foreach(Category c in doc.Settings.Categories)
            {
                if (c.CategoryType == CategoryType.Model && c.AllowsBoundParameters && !c.IsCuttable) 
                    categories.Add(c);
                else if (c.Id.Value == (long)BuiltInCategory.OST_GenericModel || 
                         c.Id.Value == (long)BuiltInCategory.OST_Floors ||
                         c.Id.Value == (long)BuiltInCategory.OST_Walls ||
                         c.Id.Value == (long)BuiltInCategory.OST_StructuralFraming || 
                         c.Id.Value == (long)BuiltInCategory.OST_StructuralColumns)
                   if(!categories.Contains(c)) categories.Add(c);
            }
            categories = categories.OrderBy(c => c.Name).ToList();
            
            List<Workset> worksets = new List<Workset>();
            if (doc.IsWorkshared)
            {
                worksets = new FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset).ToWorksets().OrderBy(w=>w.Name).ToList();
            }

            // Create Handler & Event (Reuse Q2D Handler as logic is similar, just expanded)
            Q2DRequestHandler handler = new Q2DRequestHandler();
            ExternalEvent exEvent = ExternalEvent.Create(handler);

            // Create & Show Modeless Window
            if (CurrentWindow != null && CurrentWindow.IsLoaded)
            {
                CurrentWindow.Activate();
            }
            else
            {
                Q2DConfig config = new Q2DConfig();
                handler.Config = config; // FIX: Ensure handler acts on the shared config
                CurrentWindow = new AOQuantifyWindow(config, categories, worksets, exEvent, handler);
                
                // Load packages
                var pkgs = services.TakeoffStorageService.LoadPackages(doc);
                CurrentWindow.SetPackages(pkgs);

                CurrentWindow.Show();
            }

            return Result.Succeeded;
        }
    }
}
