using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.models;
using RevitCivilConnector.services;
using RevitCivilConnector.ui;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class PatternMakerCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                // Open Window
                PatternMakerWindow win = new PatternMakerWindow();
                win.ShowDialog();

                if (!win.IsConfirmed) return Result.Cancelled;

                PatternConfig config = win.Config;
                if (config.Lines.Count == 0)
                {
                    message = "No lines drawn.";
                    return Result.Failed;
                }

                Document doc = commandData.Application.ActiveUIDocument.Document;

                using (Transaction t = new Transaction(doc, "Create Pattern"))
                {
                    t.Start();

                    // Generate FillPattern
                    FillPattern fp = PatternGenService.CreateFillPattern(config);
                    
                    // Create Element
                    FillPatternElement fpe = FillPatternElement.Create(doc, fp);

                    // Inform user
                    TaskDialog.Show("Success", $"Pattern '{fpe.Name}' created successfully as a {(config.IsModelPattern ? "Model" : "Drafting")} Pattern.");

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
    }
}
