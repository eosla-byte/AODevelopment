using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace RevitCivilConnector.UI
{
    public class RoutineSaveWindow : Window
    {
        public string RoutineTitle { get; private set; }
        public string RoutineCategory { get; private set; }
        public string RoutineDescription { get; private set; }
        public bool IsConfirmed { get; private set; } = false;

        private TextBox _txtTitle;
        private ComboBox _cmbCategory;
        private TextBox _txtDesc;

        public RoutineSaveWindow(string defaultDescription = "")
        {
            InitializeUI(defaultDescription);
        }

        private void InitializeUI(string defaultDesc)
        {
            this.Title = "Guardar Rutina (Memoria AO)";
            this.Width = 400;
            this.Height = 350;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(Color.FromRgb(30, 30, 30));
            this.Foreground = Brushes.White;
            this.ResizeMode = ResizeMode.NoResize;

            StackPanel root = new StackPanel { Margin = new Thickness(20) };

            // Title Input
            root.Children.Add(new TextBlock { Text = "Título de la Rutina:", Foreground = Brushes.Gray, Margin = new Thickness(0, 0, 0, 5) });
            _txtTitle = new TextBox { Height = 30, Padding = new Thickness(5), FontSize = 14 };
            root.Children.Add(_txtTitle);

            // Category Input
            root.Children.Add(new TextBlock { Text = "Categoría:", Foreground = Brushes.Gray, Margin = new Thickness(0, 15, 0, 5) });
            _cmbCategory = new ComboBox { Height = 30, FontSize = 14 };
            _cmbCategory.Items.Add("General");
            _cmbCategory.Items.Add("Documentacion");
            _cmbCategory.Items.Add("Modelado");
            _cmbCategory.Items.Add("Calculo");
            _cmbCategory.SelectedIndex = 0;
            root.Children.Add(_cmbCategory);

            // Description (Prompt)
            root.Children.Add(new TextBlock { Text = "Descripción / Prompt:", Foreground = Brushes.Gray, Margin = new Thickness(0, 15, 0, 5) });
            _txtDesc = new TextBox { Height = 80, Padding = new Thickness(5), TextWrapping = TextWrapping.Wrap, AcceptsReturn = true };
            _txtDesc.Text = defaultDesc;
            root.Children.Add(_txtDesc);

            // Buttons
            StackPanel btnPanel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 20, 0, 0) };
            
            Button btnCancel = new Button { Content = "Cancelar", Width = 80, Height = 30, Margin = new Thickness(0, 0, 10, 0) };
            btnCancel.Click += (s, e) => { this.Close(); };
            
            Button btnSave = new Button { Content = "Guardar", Width = 80, Height = 30, Background = new SolidColorBrush(Color.FromRgb(0, 120, 215)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
            btnSave.Click += (s, e) => 
            {
                if (string.IsNullOrWhiteSpace(_txtTitle.Text)) { MessageBox.Show("Ingresa un Título."); return; }
                
                RoutineTitle = _txtTitle.Text;
                RoutineCategory = _cmbCategory.SelectedItem.ToString();
                RoutineDescription = _txtDesc.Text;
                IsConfirmed = true;
                this.Close();
            };

            btnPanel.Children.Add(btnCancel);
            btnPanel.Children.Add(btnSave);
            root.Children.Add(btnPanel);

            this.Content = root;
        }
    }
}
