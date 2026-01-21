
using System;
using System.Diagnostics;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using System.Threading.Tasks;
using System.Net.Http;
using Newtonsoft.Json;
using System.Text;

namespace RevitCivilConnector.Auth
{
    public class TrackingService
    {
        private UIControlledApplication _app;
        private Stopwatch _activeTimer;
        private DateTime _lastActivity;
        private string _currentDocPath;
        
        // Accumulators
        private double _accumulatedActiveMinutes;
        private double _accumulatedIdleMinutes;
        private DateTime _lastReportTime;

        public TrackingService(UIControlledApplication app)
        {
            _app = app;
            _activeTimer = new Stopwatch();
            _lastActivity = DateTime.Now;
            _lastReportTime = DateTime.Now;
            
            // Register Events
            _app.Idling += OnIdling;
            _app.ControlledApplication.DocumentSynchronizingWithCentral += OnSync;
            _app.ControlledApplication.DocumentOpened += OnDocOpened;
            _app.ViewActivated += OnViewActivated; // Better for detecting active doc switches
        }

        private void OnViewActivated(object sender, ViewActivatedEventArgs e)
        {
            if (e.CurrentActiveView != null && e.CurrentActiveView.Document != null)
            {
                _currentDocPath = e.CurrentActiveView.Document.PathName;
            }
        }

        private void OnDocOpened(object sender, DocumentOpenedEventArgs e)
        {
            if (e.Document != null)
            {
                _currentDocPath = e.Document.PathName;
            }
        }

        private void OnSync(object sender, DocumentSynchronizingWithCentralEventArgs e)
        {
            if (!AuthService.Instance.IsLoggedIn) return;

            // Log Sync
            Task.Run(async () => 
            {
                try
                {
                    var payload = new 
                    {
                        session_id = AuthService.Instance.SessionId,
                        file_name = System.IO.Path.GetFileName(e.Document.PathName),
                        central_path = e.Document.PathName
                    };
                    
                    var json = JsonConvert.SerializeObject(payload);
                    var content = new StringContent(json, Encoding.UTF8, "application/json");
                    var client = new HttpClient(); // Or reuse shared
                    await client.PostAsync("http://localhost:8000/api/plugin/sync", content);
                }
                catch { }
            });
        }

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        private static extern bool GetLastInputInfo(ref LASTINPUTINFO plii);

        [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        private struct LASTINPUTINFO
        {
            public uint cbSize;
            public int dwTime;
        }

        private static uint GetLastInputTime()
        {
            uint idleTime = 0;
            LASTINPUTINFO lastInputInfo = new LASTINPUTINFO();
            lastInputInfo.cbSize = (uint)System.Runtime.InteropServices.Marshal.SizeOf(lastInputInfo);
            lastInputInfo.dwTime = 0;

            if (GetLastInputInfo(ref lastInputInfo))
            {
                int envTicks = System.Environment.TickCount;
                idleTime = (uint)((envTicks - lastInputInfo.dwTime)); 
                // Handle wrap-around just in case, though TickCount wraps every 49.7 days
            }
            return idleTime; // Milliseconds
        }

        private void OnIdling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e)
        {
            // Update Doc Path periodically
            if (sender is UIApplication uiapp && uiapp.ActiveUIDocument != null && uiapp.ActiveUIDocument.Document != null)
            {
                _currentDocPath = uiapp.ActiveUIDocument.Document.PathName;
            }

            var now = DateTime.Now;
            var delta = (now - _lastActivity).TotalMinutes;
            _lastActivity = now;

            // Get System Idle Time
            double systemIdleSeconds = GetLastInputTime() / 1000.0;
            
            // Logic:
            // If delta is huge (> 10 mins), likely Sleep/Suspend -> Count as Idle (or Ignore?)
            // If System Idle > 1 min -> User is away -> Idle
            // Else -> Active
            
            if (delta > 10) 
            {
                // Likely computer sleep or long freeze
                _accumulatedIdleMinutes += delta; 
            }
            else if (systemIdleSeconds > 60) // 1 minute threshold
            {
                _accumulatedIdleMinutes += delta;
            }
            else
            {
                _accumulatedActiveMinutes += delta;
            }

            // Report every 1 minute
            if ((now - _lastReportTime).TotalMinutes >= 1)
            {
                ReportActivity(sender as UIApplication);
            }
        }

        private async void ReportActivity(UIApplication uiapp = null)
        {
            if (!AuthService.Instance.IsLoggedIn) return;
            
            var act = _accumulatedActiveMinutes;
            var idle = _accumulatedIdleMinutes;
            
            // Reset
            _accumulatedActiveMinutes = 0;
            _accumulatedIdleMinutes = 0;
            _lastReportTime = DateTime.Now;
            
            string docName = "No Document";
            string accProject = "Local";
            string revitUser = "Unknown";
            
            // Get Revit Context Info (Safety access on UI thread)
            try
            {
                if (uiapp != null && uiapp.Application != null)
                {
                    revitUser = uiapp.Application.Username;
                }
                
                if (!string.IsNullOrEmpty(_currentDocPath))
                {
                   docName = System.IO.Path.GetFileName(_currentDocPath);
                }
                
                // Try to get Active Doc for Cloud info
                if (uiapp != null && uiapp.ActiveUIDocument != null && uiapp.ActiveUIDocument.Document != null)
                {
                     Document doc = uiapp.ActiveUIDocument.Document;
                     if (doc.IsModelInCloud)
                     {
                         try
                         {
                             ModelPath mp = doc.GetCloudModelPath();
                             // Try to resolve user visible path
                             accProject = ModelPathUtils.ConvertModelPathToUserVisiblePath(mp); 
                         }
                         catch { accProject = "Cloud (Unknown)"; }
                     }
                }
            }
            catch {}

            await Task.Run(async () =>
            {
                try
                {
                    var payload = new 
                    {
                        session_id = AuthService.Instance.SessionId,
                        file_name = docName,
                        active_minutes = act,
                        idle_minutes = idle,
                        revit_user = revitUser,
                        acc_project = accProject
                    };
                    
                    var json = JsonConvert.SerializeObject(payload);
                    var content = new StringContent(json, Encoding.UTF8, "application/json");
                    var client = new HttpClient();
                    await client.PostAsync("http://localhost:8000/api/plugin/track", content);
                }
                catch { }
            });
        }
        public void Stop()
        {
            try
            {
                _app.Idling -= OnIdling;
                _app.ControlledApplication.DocumentSynchronizingWithCentral -= OnSync;
                _app.ControlledApplication.DocumentOpened -= OnDocOpened;
                _app.ViewActivated -= OnViewActivated;
                // Attempt final report
                ReportActivity(null);
            }
            catch { }
        }
    }
}
