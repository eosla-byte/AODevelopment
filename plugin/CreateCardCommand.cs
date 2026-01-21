
using System;
using System.Collections.Generic;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.Utils;
using RevitCivilConnector.Auth;
using Newtonsoft.Json;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;

namespace RevitCivilConnector
{
    [Transaction(TransactionMode.Manual)]
    public class CreateCardCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            // Auth Check
            if (!AuthService.Instance.IsLoggedIn)
            {
                TaskDialog.Show("AO Dev", "Debe iniciar sesión.");
                return Result.Cancelled;
            }

            UIDocument uidoc = commandData.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            try
            {
                // Check Selection
                ICollection<ElementId> ids = uidoc.Selection.GetElementIds();
                if (ids.Count == 0)
                {
                    TaskDialog.Show("Crear Tarjeta", "Por favor seleccione elementos en el modelo primero.");
                    return Result.Cancelled;
                }

                // Extract Data (Selection Only)
                var revitData = DataExtractor.Extract(doc, ids);

                // Payload
                var payload = new Dictionary<string, object>();
                string sessionId = "selection_session_" + Guid.NewGuid().ToString(); // distinct session prefix?
                
                payload["session_id"] = sessionId;
                payload["project_name"] = doc.Title;
                payload["user_email"] = AuthService.Instance.CurrentUserName;
                payload["timestamp"] = DateTime.Now.ToString("o");
                payload["mode"] = "selection"; // Flag for frontend to auto-open modal
                payload["data"] = revitData;

                // Send
                string json = JsonConvert.SerializeObject(payload);
                // Send synchronously to ensure completion
                SendToBackend(json);

                // Open Browser
                string frontendUrl = "http://localhost:5173/cloud_quantify.html?session_id=" + sessionId;
                Process.Start(new ProcessStartInfo(frontendUrl) { UseShellExecute = true });

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                message = ex.Message;
                return Result.Failed;
            }
        }

        private void SendToBackend(string json)
        {
             string backendUrl = "http://localhost:8000/api/plugin/cloud/sync-quantities";
             Task.Run(async () => 
             {
                try 
                {
                    using (HttpClient client = new HttpClient())
                    {
                        var content = new StringContent(json, Encoding.UTF8, "application/json");
                        await client.PostAsync(backendUrl, content);
                    }
                }
                catch (Exception) { }
             }).Wait(); 
        }
    }
}
