using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Plumbing;

namespace RevitCivilConnector.UI
{
    public class MEPConfigWindow : System.Windows.Window
    {
        private System.Windows.Controls.ComboBox _cbPipeType;
        private System.Windows.Controls.ComboBox _cbSystemType;
        private System.Windows.Controls.TextBox _txtDiameter;
        private System.Windows.Controls.ComboBox _cbLevel; // Useful to have

        public bool IsConfirmed { get; private set; } = false;
        
        public ElementId SelectedPipeTypeId { get; private set; }
        public ElementId SelectedSystemTypeId { get; private set; }
        public ElementId SelectedLevelId { get; private set; }
        public double SelectedDiameterMm { get; private set; }

        private List<Element> _pipeTypes;
        private List<Element> _systemTypes;
        private List<Level> _levels;

        public MEPConfigWindow(List<Element> pipeTypes, List<Element> systemTypes, List<Level> levels, Level defaultLevel)
        {
            _pipeTypes = pipeTypes;
            _systemTypes = systemTypes;
            _levels = levels;

            InitializeUI(defaultLevel);
        }

        private void InitializeUI(Level defaultLevel)
        {
            this.Title = "Configuración de Tuberías IA";
            this.Width = 350;
            this.Height = 350;
            this.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(45, 45, 48));
            this.Foreground = Brushes.White;
            this.ResizeMode = System.Windows.ResizeMode.NoResize;

            System.Windows.Controls.StackPanel mainStack = new System.Windows.Controls.StackPanel { Margin = new System.Windows.Thickness(20) };

            // --- Pipe Type ---
            mainStack.Children.Add(CreateLabel("Tipo de Tubería:"));
            _cbPipeType = new System.Windows.Controls.ComboBox { Height = 25, Margin = new System.Windows.Thickness(0, 0, 0, 15) };
            foreach (var t in _pipeTypes) _cbPipeType.Items.Add(t.Name);
            if (_cbPipeType.Items.Count > 0) _cbPipeType.SelectedIndex = 0;
            mainStack.Children.Add(_cbPipeType);

            // --- System Type ---
            mainStack.Children.Add(CreateLabel("Sistema:"));
            _cbSystemType = new System.Windows.Controls.ComboBox { Height = 25, Margin = new System.Windows.Thickness(0, 0, 0, 15) };
            foreach (var t in _systemTypes) _cbSystemType.Items.Add(t.Name);
            // Try to default to something common
            int sanIdx = _systemTypes.FindIndex(x => x.Name.ToLower().Contains("sani"));
            _cbSystemType.SelectedIndex = sanIdx >= 0 ? sanIdx : 0;
            mainStack.Children.Add(_cbSystemType);

            // --- Level ---
            mainStack.Children.Add(CreateLabel("Nivel de Referencia:"));
            _cbLevel = new System.Windows.Controls.ComboBox { Height = 25, Margin = new System.Windows.Thickness(0, 0, 0, 15) };
            foreach (var l in _levels) _cbLevel.Items.Add(l.Name);
            // Default level selection
            if (defaultLevel != null)
            {
                int lvlIdx = _levels.FindIndex(l => l.Id == defaultLevel.Id);
                _cbLevel.SelectedIndex = lvlIdx >= 0 ? lvlIdx : 0;
            }
            else if (_cbLevel.Items.Count > 0) _cbLevel.SelectedIndex = 0;
            mainStack.Children.Add(_cbLevel);

            // --- Diameter ---
            mainStack.Children.Add(CreateLabel("Diámetro (mm):"));
            _txtDiameter = new System.Windows.Controls.TextBox { Height = 25, Margin = new System.Windows.Thickness(0, 0, 0, 20), Text = "100" };
            mainStack.Children.Add(_txtDiameter);

            // --- Buttons ---
            System.Windows.Controls.Grid btnGrid = new System.Windows.Controls.Grid();
            btnGrid.ColumnDefinitions.Add(new System.Windows.Controls.ColumnDefinition());
            btnGrid.ColumnDefinitions.Add(new System.Windows.Controls.ColumnDefinition());
            
            System.Windows.Controls.Button btnCancel = new System.Windows.Controls.Button { Content = "Cancelar", Height = 30, Margin = new System.Windows.Thickness(0,0,5,0) };
            btnCancel.Click += (s, e) => { this.Close(); };
            
            System.Windows.Controls.Button btnOk = new System.Windows.Controls.Button { Content = "Generar", Height = 30, Margin = new System.Windows.Thickness(5,0,0,0), Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(0, 122, 204)), Foreground = Brushes.White, FontWeight = FontWeights.Bold };
            btnOk.Click += BtnOk_Click;

            System.Windows.Controls.Grid.SetColumn(btnCancel, 0);
            System.Windows.Controls.Grid.SetColumn(btnOk, 1);
            btnGrid.Children.Add(btnCancel);
            btnGrid.Children.Add(btnOk);
            mainStack.Children.Add(btnGrid);

            this.Content = mainStack;
        }

        private System.Windows.Controls.TextBlock CreateLabel(string text)
        {
            return new System.Windows.Controls.TextBlock { Text = text, Foreground = Brushes.LightGray, Margin = new System.Windows.Thickness(0, 0, 0, 5) };
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            if (_cbPipeType.SelectedIndex < 0 || _cbSystemType.SelectedIndex < 0 || _cbLevel.SelectedIndex < 0)
            {
                System.Windows.MessageBox.Show("Por favor selecciona todos los campos.");
                return;
            }

            if (!double.TryParse(_txtDiameter.Text, out double d))
            {
                System.Windows.MessageBox.Show("El diámetro debe ser un número válido.");
                return;
            }

            SelectedPipeTypeId = _pipeTypes[_cbPipeType.SelectedIndex].Id;
            SelectedSystemTypeId = _systemTypes[_cbSystemType.SelectedIndex].Id;
            SelectedLevelId = _levels[_cbLevel.SelectedIndex].Id;
            SelectedDiameterMm = d;

            IsConfirmed = true;
            this.Close();
        }
    }
}
