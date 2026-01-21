using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Net.Http;
using System.Threading.Tasks;

namespace RevitCivilConnector.UI
{
    public class AIMonitorWindow : Window
    {
        private TextBlock _txtStats;
        private StackPanel _mainStack;

        public AIMonitorWindow()
        {
            InitializeUI();
            LoadStats();
        }

        private void InitializeUI()
        {
            this.Title = "AO AI Monitor (Admin)";
            this.Width = 500;
            this.Height = 600;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(Color.FromRgb(30, 30, 30));
            this.Foreground = Brushes.White;

            ScrollViewer scroll = new ScrollViewer();
            _mainStack = new StackPanel { Margin = new Thickness(20) };
            
            TextBlock title = new TextBlock 
            { 
                Text = "Reporte de Actividad IA", 
                FontSize = 24, 
                FontWeight = FontWeights.Bold,
                Margin = new Thickness(0,0,0,20)
            };
            _mainStack.Children.Add(title);

            _txtStats = new TextBlock 
            { 
                Text = "Cargando datos...", 
                FontSize = 14, 
                TextWrapping = TextWrapping.Wrap 
            };
            _mainStack.Children.Add(_txtStats);
            
            // Refresh Button
            Button btnRefresh = new Button
            {
                 Content = "Actualizar",
                 Width = 100, Height = 30,
                 Margin = new Thickness(0,20,0,0),
                 HorizontalAlignment = HorizontalAlignment.Left
            };
            btnRefresh.Click += (s, e) => LoadStats();
            _mainStack.Children.Add(btnRefresh);

            scroll.Content = _mainStack;
            this.Content = scroll;
        }

        private async void LoadStats()
        {
            _txtStats.Text = "Conectando al servidor...";
            try
            {
                using (HttpClient client = new HttpClient())
                {
                    string url = "https://aodevelopment-production.up.railway.app/api/ai/stats";
                    string json = await client.GetStringAsync(url);
                    
                    dynamic stats = Newtonsoft.Json.JsonConvert.DeserializeObject(json);
                    
                    string report = $"Total Requests: {stats.total_requests}\n\n";
                    report += "=== TOP USERS ===\n";
                    foreach(var u in stats.top_users)
                    {
                        report += $"{u.email}: {u.count} reqs\n";
                    }
                    
                    report += "\n=== RECENT ACTIONS ===\n";
                    foreach(var r in stats.recent_activity)
                    {
                        report += $"[{r.timestamp}] {r.user} -> {r.action} (Len: {r.message_length})\n";
                    }
                    
                    _txtStats.Text = report;
                }
            }
            catch (Exception ex)
            {
                _txtStats.Text = "Error cargando stats: " + ex.Message;
            }
        }
    }
}
