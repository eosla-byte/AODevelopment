using System;
using System.IO;

namespace RevitCivilConnector.Utils
{
    public static class Logger
    {
        private static string LogPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "RevitCivilConnector_Log.txt");

        public static void Log(string message)
        {
            try
            {
                using (StreamWriter sw = File.AppendText(LogPath))
                {
                    sw.WriteLine($"{DateTime.Now:HH:mm:ss} - {message}");
                }
            }
            catch { }
        }

        public static void Clear()
        {
            try
            {
                File.WriteAllText(LogPath, "Start Log\n");
            }
            catch { }
        }
    }
}
