using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.Auth;

namespace RevitCivilConnector.Commands
{
    [Transaction(TransactionMode.Manual)]
    public class SheetManagerCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            if (!AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("AO Plugin", "Debes iniciar sesión para usar AO Labs.");
                return Result.Cancelled;
            }

            Document doc = commandData.Application.ActiveUIDocument.Document;

            try
            {
                // 1. Collect Sheets
                var sheets = new FilteredElementCollector(doc)
                    .OfClass(typeof(ViewSheet))
                    .Cast<ViewSheet>()
                    .Where(s => !s.IsTemplate)
                    .ToList();

                // 2. Extract Data
                var sheetDataList = new List<object>();
                var allParamNames = new HashSet<string>();

                // Pre-scan for common useful string parameters (Project Parameters)
                if (sheets.Count > 0)
                {
                    foreach (Parameter p in sheets[0].Parameters)
                    {
                        if (p.StorageType == StorageType.String && !p.IsReadOnly)
                        {
                            allParamNames.Add(p.Definition.Name);
                        }
                    }
                }

                // 1.1 Get Browser Organizations (Schemes)
                var browserOrgs = new FilteredElementCollector(doc)
                    .OfClass(typeof(BrowserOrganization))
                    .Cast<BrowserOrganization>()
                    .Where(bo => bo.AreFiltersSatisfied(sheets[0].Id)) // Only applicable to Sheets
                    .ToList();

                // 1.2 Get TitleBlocks (for creating new sheets)
                var titleBlocks = new FilteredElementCollector(doc)
                    .OfClass(typeof(FamilySymbol))
                    .OfCategory(BuiltInCategory.OST_TitleBlocks)
                    .Cast<FamilySymbol>()
                    .Select(tb => new { id = tb.Id.ToString(), name = tb.Name })
                    .ToList();

                foreach (var s in sheets)
                {
                    var pDict = new Dictionary<string, string>();
                    foreach(var pname in allParamNames)
                    {
                        Parameter p = s.LookupParameter(pname);
                        if (p != null) pDict[pname] = p.AsString() ?? "";
                    }

                    // Get Folder Paths for ALL Schemes
                    var folderPaths = new Dictionary<string, List<string>>();
                    foreach(var bo in browserOrgs)
                    {
                        try 
                        {
                            var items = bo.GetFolderItems(s.Id);
                            var pathList = items.Where(i => !string.IsNullOrEmpty(i.Name)).Select(i => i.Name).ToList();
                            folderPaths[bo.Name] = pathList;
                        }
                        catch { folderPaths[bo.Name] = new List<string>(); }
                    }

                    sheetDataList.Add(new 
                    {
                        id = s.UniqueId,
                        number = s.SheetNumber,
                        name = s.Name,
                        params_data = pDict,
                        browser_paths = folderPaths // New: Map of Scheme Name -> Path List
                        // folder_path removed/deprecated in favor of browser_paths defaults
                    });
                }

                // 3. Prepare Payload
                var payload = new 
                { 
                    plugin_session_id = AuthService.Instance.SessionId,
                    project = doc.Title,
                    sheets = sheetDataList,
                    param_definitions = allParamNames.ToList(),
                    browser_schemes = browserOrgs.Select(b => b.Name).ToList(),
                    title_blocks = titleBlocks
                };

                // 4. Send to Backend (Thread-Safe)
                string resultUrl = null;
                string errorMsg = null;

                // Ensure Bridge is Active (Polling) - Fix for Connectivity
                // Sheet Manager likely uses the Login Session ID if no specific session is bound
                if (string.IsNullOrEmpty(AuthService.Instance.ActiveCommandSessionId))
                {
                     // Fallback to Login Session
                     AuthService.Instance.ActiveCommandSessionId = AuthService.Instance.SessionId;
                }
                AuthService.Instance.StartCommandPolling();

                // Run on ThreadPool to avoid Deadlock, block Main Thread until done
                var task = Task.Run(async () => 
                {
                    try 
                    {
                        using (var client = new System.Net.Http.HttpClient())
                        {
                            string url = "https://aodevelopment-production.up.railway.app/api/plugin/sheets/init";
                            string json = Newtonsoft.Json.JsonConvert.SerializeObject(payload);
                            var content = new System.Net.Http.StringContent(json, System.Text.Encoding.UTF8, "application/json");

                            var res = await client.PostAsync(url, content);
                            if (res.IsSuccessStatusCode)
                            {
                                var resStr = await res.Content.ReadAsStringAsync();
                                dynamic jsonRes = Newtonsoft.Json.JsonConvert.DeserializeObject(resStr);
                                return (string)jsonRes.redirect_url;
                            }
                            else
                            {
                                errorMsg = "Error HTTP: " + res.StatusCode;
                                return null;
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                         errorMsg = ex.Message;
                         return null;
                    }
                });

                task.Wait(); // Block Revit until done
                resultUrl = task.Result;

                if (!string.IsNullOrEmpty(resultUrl))
                {
                    Process.Start(resultUrl);
                    return Result.Succeeded;
                }
                else
                {
                    TaskDialog.Show("Error", errorMsg ?? "Unknown error sending data.");
                    return Result.Failed;
                }
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
