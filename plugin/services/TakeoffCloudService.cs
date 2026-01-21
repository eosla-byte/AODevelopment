using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using RevitCivilConnector.Auth;
using RevitCivilConnector.models;

namespace RevitCivilConnector.services
{
    public class TakeoffCloudService
    {
        // Production URL
        private const string BASE_URL = "https://aodevelopment-production.up.railway.app/api/plugin/takeoff";

        public static async Task<bool> UploadPackages(string projectId, List<TakeoffPackage> packages)
        {
            try
            {
                if (!AuthService.Instance.IsLoggedIn) return false;

                using (var client = new HttpClient())
                {
                    client.Timeout = TimeSpan.FromSeconds(30);
                    // Add Auth Header
                    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                    var cleanId = SimplifyProjectId(projectId);
                    var jsonInit = JsonConvert.SerializeObject(packages);

                    // Payload matches Python TakeoffSyncRequest
                    var payload = new
                    {
                        project_id = cleanId,
                        packages_json = jsonInit
                    };

                    var content = new StringContent(JsonConvert.SerializeObject(payload), Encoding.UTF8, "application/json");

                    var response = await client.PostAsync($"{BASE_URL}/sync?token=ignored_if_header_set", content); // Some APIs might need query param if Depends is strict, but Header is standard.

                    return response.IsSuccessStatusCode;
                }
            }
            catch (Exception ex)
            {
                // TaskDialog.Show("Cloud Error", ex.Message); // Be silent or log?
                return false;
            }
        }

        public static async Task<List<TakeoffPackage>> DownloadPackages(string projectId)
        {
            try
            {
                if (!AuthService.Instance.IsLoggedIn) return null;

                using (var client = new HttpClient())
                {
                    client.Timeout = TimeSpan.FromSeconds(30);
                    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                    var cleanId = SimplifyProjectId(projectId);
                    var response = await client.GetAsync($"{BASE_URL}/{cleanId}");

                    if (response.IsSuccessStatusCode)
                    {
                        var json = await response.Content.ReadAsStringAsync();
                        return JsonConvert.DeserializeObject<List<TakeoffPackage>>(json);
                    }
                }
            }
            catch { }
            return null;
        }

        private static string SimplifyProjectId(string original)
        {
            if (string.IsNullOrEmpty(original)) return "Default_Project";
            // Create a safe slug for filename/db
            return System.Text.RegularExpressions.Regex.Replace(original, "[^a-zA-Z0-9-_]", "");
        }
    }
}
