using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;

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

        private void SendMessage()
        {
            string msg = _txtInput.Text.Trim();
            if (string.IsNullOrEmpty(msg)) return;

            // User Message
            AddMessage("Tú", msg);
            _txtInput.Clear();

            // Simulate AI Processing
            AddMessage("IA", "Procesando solicitud...");

            // --- Simple NLP Simulation ---
            // In a real scenario, this 'msg' goes to OpenAI/Gemini API, and returns a JSON intent.
            // Here we look for keywords.

            if (msg.ToLower().Contains("audit") || msg.ToLower().Contains("auditar") || msg.ToLower().Contains("duplicado"))
            {
                System.Threading.Tasks.Task.Delay(1500).ContinueWith(t => 
                {
                    Dispatcher.Invoke(() => 
                    {
                        AddMessage("IA", "Detecté que quieres auditar duplicados en el modelo. Ejecutando análisis ahora...");
                        
                        // Trigger Revit Action
                        _requestHandler.Request = IARequestType.AuditWalls;
                        _externalEvent.Raise();
                    });
                });
            }
            else if (msg.ToLower().Contains("acotar") || msg.ToLower().Contains("dimensionar") || msg.ToLower().Contains("cotas"))
            {
               System.Threading.Tasks.Task.Delay(1500).ContinueWith(t => 
                {
                    Dispatcher.Invoke(() => 
                    {
                        AddMessage("IA", "Entendido. Generando cotas automáticas para los ejes visibles en esta vista...");
                        
                        // Trigger Revit Action
                        _requestHandler.Request = IARequestType.AutoDimension;
                        _externalEvent.Raise();
                    });
                });
            }
            else if (msg.ToLower().Contains("despiece") || msg.ToLower().Contains("agrupar") || msg.ToLower().Contains("assembly"))
            {
               System.Threading.Tasks.Task.Delay(1500).ContinueWith(t => 
                {
                    Dispatcher.Invoke(() => 
                    {
                        AddMessage("IA", "Entendido. Analizando geometría para agrupar elementos idénticos y generar montajes (assemblies)...");
                        
                        // Trigger Revit Action
                        _requestHandler.Request = IARequestType.GenerateShopDrawings;
                        _externalEvent.Raise();
                    });
                });
            }
            else if (msg.ToLower().Contains("tubería") || msg.ToLower().Contains("ducto") || msg.ToLower().Contains("mep") || msg.ToLower().Contains("sanitaria"))
            {
               System.Threading.Tasks.Task.Delay(1500).ContinueWith(t => 
                {
                    Dispatcher.Invoke(() => 
                    {
                        AddMessage("IA", "Entendido. Convirtiendo líneas seleccionadas en elementos MEP (Tuberías/Ductos)...");
                        
                        // Trigger Revit Action
                        _requestHandler.Request = IARequestType.GenerateMEPFromLines;
                        _externalEvent.Raise();
                    });
                });
            }
            else
            {
                 System.Threading.Tasks.Task.Delay(1000).ContinueWith(t => 
                {
                    Dispatcher.Invoke(() => 
                    {
                        AddMessage("IA", "Entendido. Por favor prueba con comandos como 'auditar muros' para ver una demostración de mis capacidades.");
                    });
                });
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
