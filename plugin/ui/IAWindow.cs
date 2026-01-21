using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;

using RevitCivilConnector.Auth;

namespace RevitCivilConnector.UI
{
    public class IAWindow : Window
    {
        private System.Windows.Controls.TextBox _txtInput;
        private StackPanel _chatHistory;
        private ScrollViewer _scrollViewer;
        
        // External Event Logic
        private IARequestHandler _requestHandler;
        private ExternalEvent _externalEvent;

        public IAWindow()
        {
            InitializeUI();
            
            // Init Event Handler
            _requestHandler = new IARequestHandler();
            _externalEvent = ExternalEvent.Create(_requestHandler);
        }

        private void InitializeUI()
        {
            this.Title = "AO AI Assistant";
            this.Width = 400;
            this.Height = 600;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(Color.FromRgb(30, 30, 30)); // Dark Theme
            this.Foreground = Brushes.White;
            this.Topmost = true; // Keep on top for assistance

            Grid mainGrid = new Grid();
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(50) }); // Header
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) }); // Chat Area
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(60) }); // Input Area

            // --- Header ---
            Border headerBorder = new Border 
            { 
                Background = new SolidColorBrush(Color.FromRgb(45, 45, 45)),
                Padding = new Thickness(10)
            };
            StackPanel headerStack = new StackPanel { Orientation = Orientation.Horizontal };
            
            // Icon (Small)
            try 
            {
                var assembly = Assembly.GetExecutingAssembly();
                // Ensure ia.png is available as EmbeddedResource or assume it is loaded
                // Using a fallback text/shape if icon logic is complex here, but trying generic load
                string resourceName = "RevitCivilConnector.Resources.ia.png";
                using (Stream stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream != null)
                    {
                        BitmapImage bmp = new BitmapImage();
                        bmp.BeginInit();
                        bmp.StreamSource = stream;
                        bmp.CacheOption = BitmapCacheOption.OnLoad;
                        bmp.EndInit();
                        bmp.Freeze();
                        Image img = new Image { Source = bmp, Width = 24, Height = 24, Margin = new Thickness(0,0,10,0) };
                        headerStack.Children.Add(img);
                    }
                }
            }
            catch {}

            TextBlock title = new TextBlock 
            { 
                Text = "Asistente IA", 
                FontWeight = FontWeights.Bold, 
                FontSize = 16,
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = Brushes.White,
                Margin = new Thickness(0,0,15,0)
            };
            headerStack.Children.Add(title);

            // Provider Selector
            System.Windows.Controls.ComboBox comboProvider = new System.Windows.Controls.ComboBox  
            { 
                Width = 100,
                Height = 25,
                Margin = new Thickness(0,0,10,0),
                VerticalContentAlignment = VerticalAlignment.Center
            };
            comboProvider.Items.Add("ChatGPT (Browser)");
            comboProvider.Items.Add("Gemini (Browser)");
            comboProvider.Items.Add("Claude (Browser)");
            comboProvider.SelectedIndex = 0;
            headerStack.Children.Add(comboProvider);

            // Status Indicator
            System.Windows.Shapes.Ellipse status = new System.Windows.Shapes.Ellipse
            {
                Width = 10, Height = 10,
                Fill = Brushes.LightGreen,
                ToolTip = "Conectado"
            };
            // Watch & Learn Button
            Button btnRecord = new Button
            {
                Content = "🔴",
                Width = 30, Height = 25,
                Margin = new Thickness(0,0,10,0),
                Background = Brushes.Transparent,
                Foreground = Brushes.Red,
                BorderThickness = new Thickness(0),
                ToolTip = "Aprender (Watch & Learn)"
            };
            btnRecord.Click += (s, e) => 
            {
                // Toggle via RequestHandler
                _requestHandler.Request = IARequestType.ToggleRecording;
                _externalEvent.Raise();
            };
            headerStack.Children.Add(btnRecord);

            headerStack.Children.Add(status);
            headerBorder.Child = headerStack;
            Grid.SetRow(headerBorder, 0);
            mainGrid.Children.Add(headerBorder);

            // --- Chat History ---
            _scrollViewer = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            _chatHistory = new StackPanel { Margin = new Thickness(10) };
            
            // Welcome Message
            AddMessage("IA", "Hola, soy tu asistente de arquitectura. Puedo ayudarte a revisar el modelo, documentar planos o analizar warnings. ¿Qué necesitas hoy?");

            _scrollViewer.Content = _chatHistory;
            Grid.SetRow(_scrollViewer, 1);
            mainGrid.Children.Add(_scrollViewer);

            // --- Input Area ---
            Grid inputGrid = new Grid();
            inputGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            inputGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(60) });
            inputGrid.Background = new SolidColorBrush(Color.FromRgb(40, 40, 40));

            _txtInput = new System.Windows.Controls.TextBox 
            { 
                Margin = new Thickness(10), 
                Padding = new Thickness(5),
                Background = new SolidColorBrush(Color.FromRgb(60, 60, 60)),
                Foreground = Brushes.White,
                BorderThickness = new Thickness(0),
                FontSize = 14,
                VerticalContentAlignment = VerticalAlignment.Center
            };
            _txtInput.KeyDown += (s, e) => { if (e.Key == System.Windows.Input.Key.Enter) SendMessage(); };
            Grid.SetColumn(_txtInput, 0);
            inputGrid.Children.Add(_txtInput);

            Button btnSend = new Button 
            { 
                Content = "Enviar", 
                Margin = new Thickness(0, 10, 10, 10),
                Background = new SolidColorBrush(Color.FromRgb(0, 120, 215)),
                Foreground = Brushes.White,
                FontWeight = FontWeights.Bold,
                BorderThickness = new Thickness(0)
            };
            btnSend.Click += (s, e) => SendMessage();
            Grid.SetColumn(btnSend, 1);
            inputGrid.Children.Add(btnSend);

            Grid.SetRow(inputGrid, 2);
            mainGrid.Children.Add(inputGrid);

            this.Content = mainGrid;
        }

        private async void SendMessage()
        {
            string msg = _txtInput.Text.Trim();
            if (string.IsNullOrEmpty(msg)) return;

            // User Message
            AddMessage("Tú", msg);
            _txtInput.Clear();

            // Simulate AI Processing
            AddMessage("IA", "Procesando solicitud...");

            try 
            {
                using (System.Net.Http.HttpClient client = new System.Net.Http.HttpClient())
                {
                    // PRODUCTION URL
                    string url = "https://www.somosao.com/api/ai/chat"; 
                    
                    var payload = new 
                    {
                        message = msg,
                        context = "Revit Plugin 2024", // Context info
                        user_email = AuthService.Instance.CurrentUserEmail ?? "unknown"
                    };

                    string json = Newtonsoft.Json.JsonConvert.SerializeObject(payload);
                    var content = new System.Net.Http.StringContent(json, System.Text.Encoding.UTF8, "application/json");

                    var response = await client.PostAsync(url, content);
                    if (response.IsSuccessStatusCode)
                    {
                        string resJson = await response.Content.ReadAsStringAsync();
                        dynamic resObj = Newtonsoft.Json.JsonConvert.DeserializeObject(resJson);
                        
                        string text = resObj.text;
                        string action = resObj.action;

                        AddMessage("IA", text);

                        if (!string.IsNullOrEmpty(action))
                        {
                            Dispatcher.Invoke(() => 
                            {
                                ExecuteAction(action);
                            });
                        }
                    }
                    else
                    {
                         AddMessage("IA", "Error conectando con el cerebro de AO. (Status: " + response.StatusCode + ")");
                    }
                }
            }
            catch (Exception ex)
            {
                AddMessage("IA", "Error crítico: " + ex.Message);
            }
        }

        private void ExecuteAction(string actionKey)
        {
            switch(actionKey.ToUpper())
            {
                case "AUDIT_WALLS":
                    _requestHandler.Request = IARequestType.AuditWalls;
                    _externalEvent.Raise();
                    break;
                case "AUTO_DIMENSION":
                    _requestHandler.Request = IARequestType.AutoDimension;
                    _externalEvent.Raise();
                    break;
                case "GENERATE_SHOP_DRAWINGS":
                    _requestHandler.Request = IARequestType.GenerateShopDrawings;
                    _externalEvent.Raise();
                    break;
                case "GENERATE_MEP":
                    _requestHandler.Request = IARequestType.GenerateMEPFromLines;
                    _externalEvent.Raise();
                    break;
                default:
                    // Just chat or unknown action
                    break;
            }
        }

        private void AddMessage(string sender, string text)
        {
            Border bubble = new Border 
            { 
                CornerRadius = new CornerRadius(5),
                Padding = new Thickness(10),
                Margin = new Thickness(0, 5, 0, 5),
                MaxWidth = 300
            };

            if (sender == "Tú")
            {
                bubble.Background = new SolidColorBrush(Color.FromRgb(0, 100, 180));
                bubble.HorizontalAlignment = HorizontalAlignment.Right;
            }
            else
            {
                bubble.Background = new SolidColorBrush(Color.FromRgb(60, 60, 60));
                bubble.HorizontalAlignment = HorizontalAlignment.Left;
            }

            TextBlock tb = new TextBlock 
            { 
                Text = text, 
                TextWrapping = TextWrapping.Wrap,
                Foreground = Brushes.White
            };
            bubble.Child = tb;

            _chatHistory.Children.Add(bubble);
            _scrollViewer.ScrollToBottom();
        }
    }
}
