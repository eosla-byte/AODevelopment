
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Newtonsoft.Json;
using System.Net.Http;
using System.Diagnostics;
using RevitCivilConnector.Auth;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class CloudQuantifysCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            // Auth Check
            if (!AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("Cloud Quantify", "Debe iniciar sesión en AO Resources para vincular datos.");
                return Result.Cancelled;
            }

            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // 1. Collect Data Scope
                // To keep it responsive, for now we collect high-level stats.
                // In a production version, we might push this to a background thread with a progress bar.
                
                // 0. Project Selector
                var win = new RevitCivilConnector.UI.ProjectSelectorWindow();
                bool? res = win.ShowDialog();
                
                if (res != true) return Result.Cancelled;

                var payload = new Dictionary<string, object>();
                // If joining, reuse session ID. If new, gen new.
                string sessionId = win.SelectedSessionId ?? Guid.NewGuid().ToString();
                
                payload["session_id"] = sessionId;
                payload["project_name"] = win.SelectedProjectName ?? doc.Title;
                payload["user_email"] = AuthService.Instance.CurrentUserName; 
                if (!string.IsNullOrEmpty(win.SelectedFolderId))
                {
                    payload["folder_id"] = win.SelectedFolderId;
                }
                payload["timestamp"] = DateTime.Now.ToString("o");

                // -- DATA EXTRACTION (Full Model or Filtered) --
                var revitData = RevitCivilConnector.Utils.DataExtractor.Extract(doc, null); // null = all
                
                // Add Materials/Worksets separately if needed, or update DataExtractor to include them.
                // For now, let's keep DataExtractor focused on Categories/Elements.
                
                // Keep the old Materials logic if we want standalone lists, 
                // but DataExtractor already gets materials on elements if they are parameters.
                // Let's re-add the global lists just in case.
                
                // B. Materials (Names Only)
                var materials = new FilteredElementCollector(doc)
                    .OfClass(typeof(Material))
                    .Cast<Material>()
                    .Select(m => m.Name)
                    .OrderBy(n => n)
                    .ToList();
                revitData["materials"] = materials;
                
                // C. Worksets
                if (doc.IsWorkshared)
                {
                    var worksets = new FilteredWorksetCollector(doc)
                        .OfKind(WorksetKind.UserWorkset)
                        .ToWorksets()
                        .Select(w => w.Name)
                        .ToList();
                    revitData["worksets"] = worksets;
                }

                payload["data"] = revitData;

                // 2. Send to Backend
                string json = JsonConvert.SerializeObject(payload);
                string backendUrl = "https://aodevelopment-production.up.railway.app/api/plugin/cloud/sync-quantities";

                // Synchronous HTTP call to ensure data is there before opening browser
                // Using Task.Run to avoid UI blocking context issues slightly, but waiting.
                bool success = false;
                Task.Run(async () => 
                {
                   try 
                   {
                       using (HttpClient client = new HttpClient())
                       {
                           if (AuthService.Instance.IsLoggedIn)
                                client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                           var content = new StringContent(json, Encoding.UTF8, "application/json");
                           var response = await client.PostAsync(backendUrl, content);
                           success = response.IsSuccessStatusCode;
                       }
                   }
                   catch (Exception ex)
                   {
                       Debug.WriteLine("Cloud Sync Error: " + ex.Message);
                   }
                }).Wait(); 

                if (success)
                {
                     // 3. Open Browser
                     // Production URL
                     // Production URL
                     string token = Uri.EscapeDataString(AuthService.Instance.AccessToken ?? "");
                     string frontendUrl = "https://aodevelopment-production.up.railway.app/cqt-tool?session_id=" + sessionId + "&token=" + token;
                     Process.Start(new ProcessStartInfo(frontendUrl) { UseShellExecute = true });
                }
                else
                {
                    TaskDialog.Show("Cloud Quantify", "No se pudo sincronizar con el servidor. ¿Está ejecutándose AO Resources Backend?");
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }
    }
}
