using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using Autodesk.Revit.ApplicationServices;

namespace RevitCivilConnector.Services
{
    public class TransactionRecorder
    {
        private ControlledApplication _app;
        private bool _isRecording = false;
        private List<string> _sessionLog = new List<string>();

        public bool IsRecording => _isRecording;

        public TransactionRecorder(ControlledApplication app)
        {
            _app = app;
        }

        public void StartRecording()
        {
            if (_isRecording) return;
            _isRecording = true;
            _sessionLog.Clear();
            _app.DocumentChanged += OnDocumentChanged;
            // Note: Command events require UIControlledApplication/AdWin integration or registered events in App.cs
            // For now, we rely on DocumentChanged to see WHAT changed.
        }

        public void StopRecording()
        {
            if (!_isRecording) return;
            _isRecording = false;
            _app.DocumentChanged -= OnDocumentChanged;
        }

        public List<string> GetSessionLog()
        {
            return new List<string>(_sessionLog);
        }

        public void LogEvent(string message)
        {
            if (_isRecording) _sessionLog.Add(message);
        }

        private void OnDocumentChanged(object sender, Autodesk.Revit.DB.Events.DocumentChangedEventArgs e)
        {
            if (!_isRecording) return;

            try
            {
                Document doc = e.GetDocument();
                // Get Operation Name
                string txName = string.Join(", ", e.GetTransactionNames());
                
                // Collect generic info about what happened
                var added = e.GetAddedElementIds();
                var modified = e.GetModifiedElementIds();
                // var deleted = e.GetDeletedElementIds(); // Less relevant for creation learning

                if (added.Count > 0 || modified.Count > 0)
                {
                    string logParams = $"Transaction: '{txName}' | Added: {added.Count} | Modified: {modified.Count}";
                    
                    // Dig deeper: What CATEGORY was touched?
                    var categories = new HashSet<string>();
                    
                    foreach(var id in added)
                    {
                        Element el = doc.GetElement(id);
                        if(el != null && el.Category != null) categories.Add(el.Category.Name);
                    }
                    if (categories.Count > 0) logParams += $" | Categories: {string.Join(", ", categories)}";

                    _sessionLog.Add(logParams);
                }
            }
            catch { }
        }
    }
}
