using System;
using System.Collections.Generic;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Linq;

namespace RevitCivilConnector.Services
{
    public class VisualizerHandler : IExternalEventHandler
    {
        public Queue<dynamic> CommandQueue { get; private set; } = new Queue<dynamic>();

        public void Execute(UIApplication app)
        {
            while (CommandQueue.Count > 0)
            {
                try 
                {
                    dynamic cmd = CommandQueue.Dequeue();
                    string action = cmd.action;
                    dynamic payload = cmd.payload;

                    if (action == "visualize")
                    {
                        var uids = new List<ElementId>();
                        // Parse IDs
                        foreach(var idStr in payload.elementIds)
                        {
                            if (int.TryParse((string)idStr, out int idInt))
                            {
                                // Revit 2024 uses long or ElementId constructor
                                uids.Add(new ElementId(idInt));
                            }
                        }

                        if (uids.Any())
                        {
                            // 1. Select
                            app.ActiveUIDocument.Selection.SetElementIds(uids);

                            // 2. Color Override (Optional)
                            // Requires Transaction
                            using (Transaction t = new Transaction(app.ActiveUIDocument.Document, "Visualize Cloud Elements"))
                            {
                                t.Start();
                                var colorHex = (string)payload.color; // #RRGGBB
                                var color = HexToColor(colorHex);
                                
                                var ogs = new OverrideGraphicSettings();
                                ogs.SetSurfaceForegroundPatternColor(color);
                                var solidFill = GetSolidFillKey(app.ActiveUIDocument.Document);
                                if (solidFill != null) ogs.SetSurfaceForegroundPatternId(solidFill.Id);
                                
                                // Reset first? Or just apply
                                // Iterate view?
                                // For simplicity, just selection for now as requested "select geometry"
                                // User asked for "apply color" too.
                                
                                foreach(var eid in uids)
                                {
                                    app.ActiveUIDocument.ActiveView.SetElementOverrides(eid, ogs);
                                }
                                
                                t.Commit();
                            }
                            
                            // Zoom?
                            // app.ActiveUIDocument.ShowElements(uids);
                        }
                    }
                    else if (action == "clean")
                    {
                         // Clean overrides
                         // Ideally we need to remember what we overrode. 
                         // For now, maybe just clear selection.
                         app.ActiveUIDocument.Selection.SetElementIds(new List<ElementId>());
                    }
                }
                catch (Exception ex)
                {
                    // Log error?
                    TaskDialog.Show("Visualizer Error", ex.Message);
                }
            }
        }
        
        public string GetName()
        {
            return "Cloud Visualizer Handler";
        }

        private Color HexToColor(string hex)
        {
            if (string.IsNullOrEmpty(hex)) return new Color(255, 0, 0);
            hex = hex.Replace("#", "");
            byte r = Convert.ToByte(hex.Substring(0, 2), 16);
            byte g = Convert.ToByte(hex.Substring(2, 2), 16);
            byte b = Convert.ToByte(hex.Substring(4, 2), 16);
            return new Color(r, g, b);
        }

        private FillPatternElement GetSolidFillKey(Document doc)
        {
             return new FilteredElementCollector(doc)
                .OfClass(typeof(FillPatternElement))
                .Cast<FillPatternElement>()
                .FirstOrDefault(fp => fp.GetFillPattern().IsSolidFill);
        }
    }
}
