
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Threading;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Net;
using Autodesk.Revit.UI;

namespace RevitCivilConnector.Auth
{
    public class AuthService
    {
        private static AuthService _instance;
        public static AuthService Instance => _instance ?? (_instance = new AuthService());

        // Config
        // Production URL
        private const string BASE_URL = "https://aodevelopment-production.up.railway.app/api/plugin";
        private readonly HttpClient _client;
        
        // State
        public string AccessToken { get; private set; }
        public string ActiveCommandSessionId { get; set; } // Set by CloudQuantifysCommand
        public string SessionId { get; private set; }
        public string CurrentUserEmail { get; private set; }
        public string CurrentUserName { get; private set; }
        public string CurrentUserRole { get; private set; } = "Sin Puesto";
        public bool IsLoggedIn => !string.IsNullOrEmpty(AccessToken);
        
        // New Properties
        public string LatestPluginVersion { get; private set; }
        public Dictionary<string, bool> UserPermissions { get; private set; } = new Dictionary<string, bool>();

        private CancellationTokenSource _heartbeatCts;
        public event Action<bool> OnBlockStatusChanged; // true = Blocked, false = Unblocked
        public event Action OnLogin;

        // Visualizer
        public Services.VisualizerHandler VizHandler { get; private set; }
        public ExternalEvent VizEvent { get; private set; }
        private CancellationTokenSource _pollCts;

        public void InitVisualizer(Services.VisualizerHandler handler, ExternalEvent exEvent)
        {
            VizHandler = handler;
            VizEvent = exEvent;
        }

        private AuthService()
        {
            // Enforce TLS 1.2 due to Railway/Modern HTTPS requirements
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12; 

            _client = new HttpClient();
            _client.Timeout = TimeSpan.FromSeconds(30); // Increased timeout to 30s
        }

        public async Task<bool> LoginAsync(string username, string password)
        {
            try
            {
                var machineName = Environment.MachineName;
                var revitVersion = "2024"; 
                var currentPluginVersion = "1.5.3"; // Should come from Assembly
                var ip = GetLocalIPAddress();

                var payload = new
                {
                    username = username,
                    password = password,
                    machine_name = machineName,
                    revit_version = revitVersion,
                    plugin_version = currentPluginVersion,
                    ip_address = ip
                };

                var json = JsonConvert.SerializeObject(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _client.PostAsync($"{BASE_URL}/login", content);

                if (response.IsSuccessStatusCode)
                {
                    var respString = await response.Content.ReadAsStringAsync();
                    dynamic respData = JsonConvert.DeserializeObject(respString);
                    
                    AccessToken = respData.access_token;
                    SessionId = respData.session_id;
                    CurrentUserName = respData.user_name;
                    CurrentUserEmail = username;
                    
                    // Version Check
                    try {
                         LatestPluginVersion = respData.latest_version;
                         
                         // Check for update info object
                         dynamic updateInfo = respData.update_info;
                         
                         if (LatestPluginVersion != currentPluginVersion)
                         {
                             bool isMandatory = false;
                             string url = "";
                             string changelog = "";
                             
                             if (updateInfo != null)
                             {
                                 isMandatory = (bool)updateInfo.mandatory;
                                 url = (string)updateInfo.url;
                                 changelog = (string)updateInfo.changelog;
                             }
                             
                             if (isMandatory)
                             {
                                 TaskDialog.Show("Actualización Requerida", 
                                     $"Es obligatorio actualizar a la versión {LatestPluginVersion} para continuar.\n\nNotas:\n{changelog}\n\nEl plugin se cerrará.");
                                 
                                 if (!string.IsNullOrEmpty(url)) 
                                 {
                                     try { System.Diagnostics.Process.Start(url); } catch {}
                                 }
                                 return false; // Abort Login
                             }
                             else
                             {
                                 TaskDialog.Show("Actualización Disponible", 
                                     $"Nueva versión disponible: {LatestPluginVersion}.\n\nTu versión: {currentPluginVersion}.\n\n{changelog}");
                             }
                         }
                    } catch { }

                    // Role
                    try
                    {
                        string r = (string)respData.role;
                        CurrentUserRole = string.IsNullOrEmpty(r) ? "Colaborador" : r;
                    }
                    catch { CurrentUserRole = "Colaborador"; }
                    
                    // Permissions
                    try {
                        UserPermissions.Clear();
                        var permsToken = respData.permissions; // JToken from dynamic

                        if (permsToken != null)
                        {
                            if (permsToken.Type == JTokenType.Object)
                            {
                                foreach (JProperty prop in permsToken.Properties())
                                {
                                    UserPermissions[prop.Name] = (bool)prop.Value;
                                }
                            }
                            else if (permsToken.Type == JTokenType.String)
                            {
                                string jsonStruct = (string)permsToken;
                                var dict = JsonConvert.DeserializeObject<Dictionary<string, bool>>(jsonStruct);
                                if (dict != null)
                                {
                                    foreach(var kvp in dict) UserPermissions[kvp.Key] = kvp.Value;
                                }
                            }
                        }
                    } catch (Exception ex) {
                        // Store error for Debug Info if needed
                        // Console.WriteLine(ex.ToString());
                    }

                    // Start Heartbeat
                    StartHeartbeat();
                    StartCommandPolling(); // Start polling for commands (Visualizer)
                    
                    // Unblock
                    OnBlockStatusChanged?.Invoke(false);
                    OnLogin?.Invoke();
                    return true;
                }
                return false;
            }
            catch (Exception ex)
            {
                var sb = new StringBuilder();
                sb.AppendLine($"Main: {ex.Message}");
                if (ex.InnerException != null) sb.AppendLine($"Inner: {ex.InnerException.Message}");
                // sb.AppendLine($"Stack: {ex.StackTrace}"); // Optional, maybe too long for dialog
                
                TaskDialog.Show("Login Error", $"Connection details:\n{sb.ToString()}");
                return false;
            }
        }
        
        public bool HasPermission(string permissionKey)
        {
            // Default to TRUE if key missing (Opt-out)
            if (UserPermissions == null || !UserPermissions.ContainsKey(permissionKey))
                return true;
            return UserPermissions[permissionKey];
        }

        private void StartHeartbeat()
        {
            StopHeartbeat();
            _heartbeatCts = new CancellationTokenSource();
            Task.Run(() => HeartbeatLoop(_heartbeatCts.Token));
        }

        private void StopHeartbeat()
        {
            _heartbeatCts?.Cancel();
            _heartbeatCts = null;
        }

        private async Task HeartbeatLoop(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    await Task.Delay(TimeSpan.FromMinutes(1), token); // Wait 1 min
                    
                    if (token.IsCancellationRequested) break;

                    var ip = GetLocalIPAddress();
                    var payload = new { session_id = SessionId, ip_address = ip };
                    var json = JsonConvert.SerializeObject(payload);
                    var content = new StringContent(json, Encoding.UTF8, "application/json");
                    
                    // Add Auth Header? API doesn't enforce it for Heartbeat yet but good practice if we did
                    // _client.DefaultRequestHeaders.Authorization = ...

                    var response = await _client.PostAsync($"{BASE_URL}/heartbeat", content);
                    
                    if (!response.IsSuccessStatusCode)
                    {
                        // Failed Heartbeat -> Block
                        OnBlockStatusChanged?.Invoke(true); 
                    }
                    else
                    {
                        // Success -> Parse for Permissions Update
                        try {
                            var respString = await response.Content.ReadAsStringAsync();
                            dynamic respData = JsonConvert.DeserializeObject(respString);
                            
                            // Permissions Sync
                            var permsToken = respData.permissions; // JToken
                            if (permsToken != null)
                            {
                                if (permsToken.Type == JTokenType.Object)
                                {
                                    UserPermissions.Clear();
                                    foreach (JProperty prop in permsToken.Properties())
                                    {
                                        UserPermissions[prop.Name] = (bool)prop.Value;
                                    }
                                }
                                else if (permsToken.Type == JTokenType.String)
                                {
                                    string jsonStruct = (string)permsToken;
                                    var dict = JsonConvert.DeserializeObject<Dictionary<string, bool>>(jsonStruct);
                                    if (dict != null)
                                    {
                                        UserPermissions.Clear();
                                        foreach(var kvp in dict) UserPermissions[kvp.Key] = kvp.Value;
                                    }
                                }
                            }
                        } catch { }

                        OnBlockStatusChanged?.Invoke(false);
                    }
                }
                catch
                {
                     // Connection lost -> Block
                     OnBlockStatusChanged?.Invoke(true);
                }
            }
        }

        public void StartCommandPolling()
        {
            StopCommandPolling();
            _pollCts = new CancellationTokenSource();
            Task.Run(() => CommandPollingLoop(_pollCts.Token));
        }

        private void StopCommandPolling()
        {
            _pollCts?.Cancel();
            _pollCts = null;
        }

        private async Task CommandPollingLoop(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    string targetSessionId = !string.IsNullOrEmpty(ActiveCommandSessionId) ? ActiveCommandSessionId : SessionId;

                    if (string.IsNullOrEmpty(targetSessionId) || VizHandler == null || VizEvent == null)
                    {
                         await Task.Delay(1000, token);
                         continue;
                    }

                    // Poll Bridge
                    // Using separate try-catch to avoid breaking loop on single fail
                    try 
                    {
                        var response = await _client.GetAsync($"{BASE_URL}/cloud/commands/{targetSessionId}");
                        if (response.IsSuccessStatusCode)
                        {
                            var respString = await response.Content.ReadAsStringAsync();
                            dynamic respData = JsonConvert.DeserializeObject(respString);
                            var commands = respData.commands; // JArray

                            if (commands != null && commands.Count > 0)
                            {
                                foreach (var cmd in commands)
                                {
                                    VizHandler.CommandQueue.Enqueue(cmd);
                                }
                                VizEvent.Raise();
                            }
                        }
                    }
                    catch { }

                    await Task.Delay(500, token); // 0.5 sec poll for faster response
                }
                catch (TaskCanceledException) { break; }
                catch (Exception) 
                {
                     await Task.Delay(5000, token);
                }
            }
        }

        public async void Logout()
        {
            StopHeartbeat();
            AccessToken = null;
            SessionId = null;
            OnBlockStatusChanged?.Invoke(true); // Lock it
        }

        private string GetLocalIPAddress()
        {
            try
            {
                var host = Dns.GetHostEntry(Dns.GetHostName());
                foreach (var ip in host.AddressList)
                {
                    if (ip.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
                    {
                        return ip.ToString();
                    }
                }
            }
            catch { }
            return "0.0.0.0";
        }
    }
}
