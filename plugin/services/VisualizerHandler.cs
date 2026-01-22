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
                            // Revit 2024 uses long IDs
                            if (long.TryParse((string)idStr, out long idLong))
                            {
                                // Using generic constructor or long depending on SDK
                                // For 2024, ElementId(long) is preferred
                                try { uids.Add(new ElementId(idLong)); } catch { uids.Add(new ElementId((int)idLong)); }
                            }
                            else if (int.TryParse((string)idStr, out int idInt))
                            {
                                uids.Add(new ElementId(idInt));
                            }
                        }

                        if (uids.Any())
                        {
                            // 1. Select
                            app.ActiveUIDocument.Selection.SetElementIds(uids);

                            // 2. Color Override
                            using (Transaction t = new Transaction(app.ActiveUIDocument.Document, "Visualize Cloud Elements"))
                            {
                                t.Start();
                                var colorHex = (string)payload.color; // #RRGGBB
                                var color = HexToColor(colorHex);
                                
                                var ogs = new OverrideGraphicSettings();
                                ogs.SetSurfaceForegroundPatternColor(color);
                                var solidFill = GetSolidFillKey(app.ActiveUIDocument.Document);
                                if (solidFill != null) ogs.SetSurfaceForegroundPatternId(solidFill.Id);
                                
                                foreach(var eid in uids)
                                {
                                    app.ActiveUIDocument.ActiveView.SetElementOverrides(eid, ogs);
                                }
                                
                                t.Commit();
                            }
                            
                            // 3. Zoom / Show
                            app.ActiveUIDocument.ShowElements(uids);

                            // Debug Confirmation
                            // TaskDialog.Show("Viz", $"Visualized {uids.Count} elements.");
                        }
                    }
                    else if (action == "clean")
                    {
                         // Clean overrides
                         app.ActiveUIDocument.Selection.SetElementIds(new List<ElementId>());
                    }
                    else if (action == "UPDATE_SHEETS")
                    {
                        // Payload: List of { id, number, name, params }
                        var updates = payload.ToList(); 
                        using (Transaction t = new Transaction(app.ActiveUIDocument.Document, "Update Sheets from Web"))
                        {
                            t.Start();
                            int count = 0;
                            var doc = app.ActiveUIDocument.Document;
                            
                            foreach (dynamic update in updates)
                            {
                                string uniqueId = update.id;
                                Element el = doc.GetElement(uniqueId);
                                if (el is ViewSheet sheet)
                                {
                                    // 1. Number (Handle conflict risk? For now just try set)
                                    string newNum = update.number;
                                    if(sheet.SheetNumber != newNum) { try { sheet.SheetNumber = newNum; } catch {} }

                                    // 2. Name
                                    string newName = update.name;
                                    if(sheet.Name != newName) { try { sheet.Name = newName; } catch {} }
                                    
                                    // 3. Params
                                    var paramsDict = update.@params; // 'params' is keyword
                                    foreach (var prop in paramsDict) // JObject or Dictionary?
                                    {
                                        string pName = prop.Name;
                                        string pVal = prop.Value.ToString();
                                        
                                        // Skip Name/Number as they are properties
                                        if(pName == "Sheet Number" || pName == "Sheet Name") continue;

                                        Parameter p = sheet.LookupParameter(pName);
                                        if (p != null && !p.IsReadOnly && p.StorageType == StorageType.String)
                                        {
                                            p.Set(pVal);
                                        }
                                    }
                                    count++;
                                }
                            }
                            t.Commit();
                            // Optional: Notify success?
                        }
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
