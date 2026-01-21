
using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Threading.Tasks;
using System.IO;
using System.Reflection;
using System.Windows.Media.Imaging;

namespace RevitCivilConnector.UI
{
    public class LoginWindow : Window
    {
        private TextBox txtUser;
        private PasswordBox txtPass;
        private TextBlock lblStatus;
        private Button btnLogin;
        private Button btnCancel;

        public LoginWindow()
        {
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "AO Development";
            this.Topmost = true;
            this.Width = 400;
            this.Height = 450;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(Color.FromRgb(30, 30, 30));
            this.Foreground = Brushes.White;


            StackPanel stack = new StackPanel { Margin = new Thickness(25) };


            

            
            // Logo or Title
            TextBlock title = new TextBlock 
            { 
                Text = "AO Development", // Updated Title
                FontSize = 24, 
                FontWeight = FontWeights.Bold, 
                Foreground = Brushes.White,
                HorizontalAlignment = HorizontalAlignment.Center,
                Margin = new Thickness(0,0,0,25)
            };
            stack.Children.Add(title);

            // User
            stack.Children.Add(new TextBlock { Text = "Email:", Foreground = Brushes.LightGray, FontSize=14 });
            txtUser = new TextBox { Margin = new Thickness(0, 5, 0, 15), Padding = new Thickness(5), FontSize=14 };
            stack.Children.Add(txtUser);

            // Pass
            stack.Children.Add(new TextBlock { Text = "Contraseña:", Foreground = Brushes.LightGray, FontSize=14 });
            txtPass = new PasswordBox { Margin = new Thickness(0, 5, 0, 25), Padding = new Thickness(5), FontSize=14 };
            stack.Children.Add(txtPass);

            // Buttons Grid
            Grid btnGrid = new Grid();
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(10) });
            btnGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            // Cancel Button
            btnCancel = new Button 
            { 
                Content = "Cancelar", 
                Height = 40, 
                Background = new SolidColorBrush(Color.FromRgb(80, 80, 80)),
                Foreground = Brushes.White,
                FontWeight = FontWeights.Bold,
                IsCancel = true // Esc Trigger
            };
            btnCancel.Click += (s,e) => { this.DialogResult = false; this.Close(); };
            Grid.SetColumn(btnCancel, 0);
            btnGrid.Children.Add(btnCancel);

            // Login Button
            btnLogin = new Button 
            { 
                Content = "Ingresar", 
                Height = 40, 
                Background = new SolidColorBrush(Color.FromRgb(0, 120, 215)),
                Foreground = Brushes.White,
                FontWeight = FontWeights.Bold,
                IsDefault = true // Enter Trigger
            };
            btnLogin.Click += BtnLogin_Click;
            Grid.SetColumn(btnLogin, 2);
            btnGrid.Children.Add(btnLogin);

            stack.Children.Add(btnGrid);

            // Status
            lblStatus = new TextBlock 
            { 
                Text = "", 
                Foreground = Brushes.Red, 
                Margin = new Thickness(0, 15, 0, 0),
                HorizontalAlignment = HorizontalAlignment.Center
            };
            stack.Children.Add(lblStatus);

            // Logo (Below Buttons/Status)
            try 
            {
                var assembly = Assembly.GetExecutingAssembly();
                string resourceName = "RevitCivilConnector.Resources.logo_ao_white_large.png";

                using (Stream stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream != null)
                    {
                        Image img = new Image();
                        BitmapImage bmp = new BitmapImage();
                        bmp.BeginInit();
                        bmp.StreamSource = stream;
                        bmp.CacheOption = BitmapCacheOption.OnLoad;
                        bmp.EndInit();
                        bmp.Freeze();
                        
                        img.Source = bmp;
                        img.Height = 88; // Increased from 50 to 88 (~75%)
                        img.Margin = new Thickness(0, 20, 0, 5);
                        stack.Children.Add(img);
                    }
                }
            }
            catch {}

            // Footer
            TextBlock footer = new TextBlock 
            { 
                Text = "AO Plugin v1.0\nDesarrollado para AO Development.\n\nSincronización Cloud y Herramientas de Productividad.\n\nContacto Ventas: proyectos@somosao.com\n\nAO Development 2026, todos los derechos reservados.\nPermitido su uso solo para colaboradores de AO", 
                Foreground = Brushes.White,
                FontSize = 14, // Increased from 10 to ~14
                FontFamily = new FontFamily("Segoe UI Light"), // Approximate Barlow Light
                TextAlignment = TextAlignment.Center,
                HorizontalAlignment = HorizontalAlignment.Center,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 5, 0, 0),
                Opacity = 0.9 // Increased opacity slightly for readability
            };
            stack.Children.Add(footer);

            // Version Label (Bottom Right)
            TextBlock versionLbl = new TextBlock
            {
                Text = "Version 1.0",
                Foreground = Brushes.Red,
                FontSize = 12,
                FontWeight = FontWeights.Bold,
                HorizontalAlignment = HorizontalAlignment.Right,
                VerticalAlignment = VerticalAlignment.Bottom,
                Margin = new Thickness(0, 0, 10, 10)
            };
            // Add to main grid instead of stack to position bottom-right
            // We need to wrap stack in a Grid or Overlay. Let's change Content to a Grid.
            Grid mainGrid = new Grid();
            mainGrid.Children.Add(stack);
            mainGrid.Children.Add(versionLbl);

            this.Content = mainGrid;
        }

        private async void BtnLogin_Click(object sender, RoutedEventArgs e)
        {
            string u = txtUser.Text;
            string p = txtPass.Password;

            if (string.IsNullOrWhiteSpace(u) || string.IsNullOrWhiteSpace(p))
            {
                lblStatus.Text = "Ingrese credenciales.";
                return;
            }

            btnLogin.Content = "Conectando...";
            btnLogin.IsEnabled = false;
            btnCancel.IsEnabled = false;

            bool success = await RevitCivilConnector.Auth.AuthService.Instance.LoginAsync(u, p);

            if (success)
            {
                this.DialogResult = true;
                this.Close();
            }
            else
            {
                lblStatus.Text = "Acceso Denegado. Verifique credenciales.";
                btnLogin.Content = "Ingresar";
                btnLogin.IsEnabled = true;
                btnCancel.IsEnabled = true;
            }
        }
    }
}
