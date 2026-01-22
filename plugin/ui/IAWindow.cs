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
        
        // Side Panel Elements
        private bool _isPanelOpen = false;
        private Grid _mainGrid;
        private Border _sidePanel;
        private StackPanel _routinesList;
        
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
            headerBorder.Child = headerStack; // Fix: Assign child
            
            // Icon (Small) - Disabled for debug
            /*
            try 
            {
                var assembly = Assembly.GetExecutingAssembly();
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
            */

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

            // Provider Selector Removed (Always use Backend)
            /*
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
            */

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
                
                // If we are currently recording (Red UI), we are about to STOP.
                // App.Recorder.IsRecording returns the current state (True).
                // So if True, we are stopping -> Show Save Dialog.
                if (App.Recorder.IsRecording)
                {
                     // Get Log Summary for default desc
                     var logs = App.Recorder.GetSessionLog();
                     string defaultDesc = string.Join("\n", logs);
                     
                     // Show Save Window
                     RoutineSaveWindow win = new RoutineSaveWindow(defaultDesc);
                     win.Owner = this;
                     win.ShowDialog();
                     
                     if (win.IsConfirmed)
                     {
                         // Save to Backend
                         SaveRoutineToBackend(win);
                     }
                }
                
                _externalEvent.Raise();
            };
            headerStack.Children.Add(btnRecord);


            // --- LAYOUT REFACTOR ---
            // We want 2 Columns. Column 0 is Chat (header + history + input). Column 1 is Side Panel.
            // But 'header', 'history', 'input' were rows in MainGrid.
            // Let's create a 'ChatContainer' Grid that holds the 3 rows, and put THAT in Column 0.
            
            Grid chatContainer = new Grid();
            chatContainer.RowDefinitions.Add(new RowDefinition { Height = new GridLength(50) });
            chatContainer.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            chatContainer.RowDefinitions.Add(new RowDefinition { Height = new GridLength(60) });
            
            Grid.SetRow(headerBorder, 0);
            chatContainer.Children.Add(headerBorder);
            
            // Re-Initialize Chat History (Was removed in previous edit)
            _scrollViewer = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            _chatHistory = new StackPanel { Margin = new Thickness(10) };
            
            // Welcome Message
            AddMessage("IA", "Hola, soy tu asistente de arquitectura. Puedo ayudarte a revisar el modelo, documentar planos o analizar warnings. ¿Qué necesitas hoy?");

            _scrollViewer.Content = _chatHistory;

            Grid.SetRow(_scrollViewer, 1);
            chatContainer.Children.Add(_scrollViewer);
            
            // --- Input Area ---
            Grid inputGrid = new Grid();
            inputGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(30) }); // Attach Button
            inputGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            inputGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(60) });
            inputGrid.Background = new SolidColorBrush(Color.FromRgb(40, 40, 40));
            
            // Attach Button
            Button btnAttach = new Button
            {
                Content = "📎",
                Margin = new Thickness(5, 10, 0, 10),
                Background = Brushes.Transparent,
                Foreground = Brushes.White,
                BorderThickness = new Thickness(0),
                ToolTip = "Adjuntar Archivo (Excel, Img, Code)"
            };
            btnAttach.Click += BtnAttach_Click;
            Grid.SetColumn(btnAttach, 0);
            inputGrid.Children.Add(btnAttach);

            _txtInput = new System.Windows.Controls.TextBox 
            { 
                Margin = new Thickness(5, 10, 10, 10), 
                Padding = new Thickness(5),
                Background = new SolidColorBrush(Color.FromRgb(60, 60, 60)),
                Foreground = Brushes.White,
                BorderThickness = new Thickness(0),
                FontSize = 14,
                VerticalContentAlignment = VerticalAlignment.Center
            };
            _txtInput.KeyDown += (s, e) => { if (e.Key == System.Windows.Input.Key.Enter) SendMessage(); };
            Grid.SetColumn(_txtInput, 1);
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
            Grid.SetColumn(btnSend, 2);
            inputGrid.Children.Add(btnSend);

            Grid.SetRow(inputGrid, 2);
            chatContainer.Children.Add(inputGrid);

            // Re-init MainGrid with Columns
            _mainGrid = new Grid();
            _mainGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); // Chat
            _mainGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(0) }); // Side Panel (Hidden initially)

            Grid.SetColumn(chatContainer, 0);
            _mainGrid.Children.Add(chatContainer);

            // --- SIDE PANEL ---
            _sidePanel = new Border 
            { 
                Background = new SolidColorBrush(Color.FromRgb(35, 35, 35)), 
                BorderBrush = new SolidColorBrush(Color.FromRgb(50, 50, 50)),
                BorderThickness = new Thickness(1, 0, 0, 0)
            };
            
            Grid sideGrid = new Grid();
            sideGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(50) }); // Header
            sideGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) }); // List
            
            // Side Header
            TextBlock sideTitle = new TextBlock 
            { 
                Text = "🧠 Memoria AO", 
                FontWeight = FontWeights.Bold, 
                Foreground = Brushes.White,
                VerticalAlignment = VerticalAlignment.Center,
                Margin = new Thickness(10)
            };
            sideGrid.Children.Add(sideTitle);

            // Scrollable List
            ScrollViewer sideScroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            _routinesList = new StackPanel { Margin = new Thickness(5) };
            sideScroll.Content = _routinesList;
            Grid.SetRow(sideScroll, 1);
            sideGrid.Children.Add(sideScroll);

            _sidePanel.Child = sideGrid;
            Grid.SetColumn(_sidePanel, 1);
            _mainGrid.Children.Add(_sidePanel);
            
            // Add Toggle Button to Header (Small 'Book' Icon)
            Button btnToggle = new Button
            {
                Content = "📖",
                Width = 30, Height = 25,
                Margin = new Thickness(0,0,10,0),
                Background = Brushes.Transparent,
                Foreground = Brushes.White,
                BorderThickness = new Thickness(0),
                ToolTip = "Abrir Memoria (Rutinas)"
            };
            btnToggle.Click += (s, e) => ToggleSidePanel();
            // Insert before Status
            headerStack.Children.Insert(headerStack.Children.Count - 1, btnToggle);

            this.Content = _mainGrid;
            
            // Load Routines async
            LoadRoutines();
        }

        private void ToggleSidePanel()
        {
            _isPanelOpen = !_isPanelOpen;
            if (_isPanelOpen)
            {
                this.Width = 750;
                _mainGrid.ColumnDefinitions[1].Width = new GridLength(350);
                LoadRoutines();
            }
            else
            {
                this.Width = 400;
                _mainGrid.ColumnDefinitions[1].Width = new GridLength(0);
            }
        }

        private async void LoadRoutines()
        {
            try
            {
                _routinesList.Children.Clear();
                _routinesList.Children.Add(new TextBlock { Text = "Cargando...", Foreground = Brushes.Gray, Margin = new Thickness(10) });

                using (System.Net.Http.HttpClient client = new System.Net.Http.HttpClient())
                {
                    string url = $"https://aodevelopment-production.up.railway.app/api/plugin/routines?user_email={AuthService.Instance.CurrentUserEmail}";
                    var items = await client.GetStringAsync(url);
                    var routines = Newtonsoft.Json.JsonConvert.DeserializeObject<System.Collections.Generic.List<dynamic>>(items);

                    _routinesList.Children.Clear();
                    
                    if (routines == null || routines.Count == 0)
                    {
                         _routinesList.Children.Add(new TextBlock { Text = "No hay rutinas guardadas.", Foreground = Brushes.Gray, Margin = new Thickness(10) });
                         return;
                    }

                    // Group by Categoy? Simplified list for now
                    foreach(var r in routines)
                    {
                        Border card = new Border
                        {
                            Background = new SolidColorBrush(Color.FromRgb(50, 50, 50)),
                            CornerRadius = new CornerRadius(5),
                            Margin = new Thickness(5),
                            Padding = new Thickness(10)
                        };
                        
                        StackPanel st = new StackPanel();
                        st.Children.Add(new TextBlock { Text = (string)r.title, FontWeight = FontWeights.Bold, Foreground = Brushes.White });
                        st.Children.Add(new TextBlock { Text = (string)r.category, FontSize = 10, Foreground = Brushes.LightGray });
                        st.Children.Add(new TextBlock { Text = (string)r.description, FontSize = 10, Foreground = Brushes.Gray, TextTrimming = TextTrimming.CharacterEllipsis });

                        // Play Button
                        Button btnPlay = new Button 
                        { 
                             Content = "▶ Ejecutar", 
                             Height = 25, 
                             Margin = new Thickness(0, 5, 0, 0),
                             Background = new SolidColorBrush(Color.FromRgb(0, 100, 180)),
                             Foreground = Brushes.White,
                             BorderThickness = new Thickness(0)
                        };
                        string promptToRun = (string)r.description; // We run the description as a prompt
                        btnPlay.Click += (s, e) => 
                        {
                            _txtInput.Text = promptToRun;
                            SendMessage();
                        };
                        st.Children.Add(btnPlay);

                        card.Child = st;
                        _routinesList.Children.Add(card);
                    }
                }
            }
            catch (Exception ex)
            {
                 _routinesList.Children.Clear();
                 _routinesList.Children.Add(new TextBlock { Text = "Error: " + ex.Message, Foreground = Brushes.Red });
            }
        }

        // Attachments Logic
        private System.Collections.Generic.List<dynamic> _currentAttachments = new System.Collections.Generic.List<dynamic>();

        private void BtnAttach_Click(object sender, RoutedEventArgs e)
        {
            Microsoft.Win32.OpenFileDialog dlg = new Microsoft.Win32.OpenFileDialog();
            dlg.Filter = "Todos los archivos|*.*|Imagenes|*.png;*.jpg|Excel|*.xlsx;*.csv";
            if (dlg.ShowDialog() == true)
            {
                string path = dlg.FileName;
                string ext = System.IO.Path.GetExtension(path).ToLower().Replace(".", "");
                string name = System.IO.Path.GetFileName(path);
                
                try
                {
                    string content = "";
                    if (ext == "png" || ext == "jpg" || ext == "jpeg")
                    {
                         byte[] bytes = File.ReadAllBytes(path);
                         content = Convert.ToBase64String(bytes);
                    }
                    else
                    {
                         // Text based
                         // Warning: Simple read. If binary xlsx, this might fail or produce garbage if not handled.
                         // But python side expects string content for text/code.
                         // For Excel (xlsx), reading as bytes -> base64 is safer.
                         // Let's rely on backend to parse if needed or just treat everything as Base64?
                         // Python script assumed "content" is string. 
                         // Let's stick to reading as text for csv/py/txt.
                         if (ext == "xlsx" || ext == "xls")
                         {
                              // For Excel, backend can't easily parse raw bits unless we send as base64 and use pandas.read_excel(BytesIO)
                              // Let's send as Base64 for everything to be safe.
                              byte[] bytes = File.ReadAllBytes(path);
                              content = Convert.ToBase64String(bytes);
                         }
                         else
                         {
                              content = File.ReadAllText(path);
                         }
                    }

                    _currentAttachments.Add(new { name = name, content = content, type = ext });
                    AddMessage("Sistema", $"Archivo adjuntado: {name}");
                }
                catch (Exception ex)
                {
                    AddMessage("Sistema", "Error leyendo archivo: " + ex.Message);
                }
            }
        }

        private async void SendMessage()
        {
            string msg = _txtInput.Text.Trim();
            if (string.IsNullOrEmpty(msg) && _currentAttachments.Count == 0) return;

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
                    string url = "https://aodevelopment-production.up.railway.app/api/ai/chat"; 
                    
                    var payload = new 
                    {
                        message = msg,
                        context = "Revit Plugin 2024", // Context info
                        user_email = AuthService.Instance.CurrentUserEmail ?? "unknown",
                        attachments = _currentAttachments
                    };

                    string json = Newtonsoft.Json.JsonConvert.SerializeObject(payload);
                    var content = new System.Net.Http.StringContent(json, System.Text.Encoding.UTF8, "application/json");

                    var response = await client.PostAsync(url, content);
                    
                    // Clear attachments after send
                    _currentAttachments.Clear();

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
            // Log for Recorder (So it can be saved)
            if (App.Recorder != null && App.Recorder.IsRecording)
            {
                App.Recorder.LogEvent("AI Command: " + actionKey);
            }

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
                case "CREATE_SHEET_LIST":
                    _requestHandler.Request = IARequestType.CreateSheetList;
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

        private async void SaveRoutineToBackend(RoutineSaveWindow win)
        {
             try
             {
                 var actions = App.Recorder.GetSessionLog();
                 // Add the user prompt if empty?
                 if (actions.Count == 0 && !string.IsNullOrEmpty(win.RoutineDescription))
                 {
                     actions.Add("Prompt: " + win.RoutineDescription);
                 }

                 var payload = new 
                 {
                     title = win.RoutineTitle,
                     description = win.RoutineDescription,
                     category = win.RoutineCategory,
                     actions_json = actions,
                     user_email = AuthService.Instance.CurrentUserEmail ?? "unknown",
                     is_global = false
                 };
                 
                 using (System.Net.Http.HttpClient client = new System.Net.Http.HttpClient())
                 {
                     string url = "https://aodevelopment-production.up.railway.app/api/plugin/routines"; 
                     string json = Newtonsoft.Json.JsonConvert.SerializeObject(payload);
                     var content = new System.Net.Http.StringContent(json, System.Text.Encoding.UTF8, "application/json");
                     
                     var res = await client.PostAsync(url, content);
                     if (res.IsSuccessStatusCode)
                     {
                         AddMessage("Sistema", "Rutina guardada en Memoria AO.");
                         if(_isPanelOpen) LoadRoutines(); // Refresh panel
                     }
                     else
                     {
                         AddMessage("Sistema", "Error guardando rutina: " + res.StatusCode);
                     }
                 }
             }
             catch(Exception ex)
             {
                 AddMessage("Sistema", "Error de red: " + ex.Message);
             }
        }
    }
}
