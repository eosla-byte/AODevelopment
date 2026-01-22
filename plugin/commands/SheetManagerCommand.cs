using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
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

                foreach (var s in sheets)
                {
                    var pDict = new Dictionary<string, string>();
                    foreach(var pname in allParamNames)
                    {
                        Parameter p = s.LookupParameter(pname);
                        if (p != null) pDict[pname] = p.AsString() ?? "";
                    }

                    sheetDataList.Add(new 
                    {
                        id = s.UniqueId,
                        number = s.SheetNumber,
                        name = s.Name,
                        params_data = pDict
                    });
                }

                // 3. Send to Backend
                var payload = new 
                { 
                    plugin_session_id = AuthService.Instance.SessionId,
                    project = doc.Title,
                    sheets = sheetDataList,
                    param_definitions = allParamNames.ToList()
                };

                SendToBackend(payload);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }

        private async void SendToBackend(object payload)
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
                        string sessionUrl = jsonRes.redirect_url;
                        Process.Start(sessionUrl);
                    }
                    else
                    {
                        TaskDialog.Show("Error", "Error conectando con AO Cloud: " + res.StatusCode);
                    }
                }
            }
            catch(Exception ex)
            {
                TaskDialog.Show("Error", "Excepción de Red: " + ex.Message);
            }
        }
    }
}
