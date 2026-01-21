using System;
using System.Collections.Generic;
using System.Globalization;
using System.Windows;
using System.Windows.Controls; 
using System.Windows.Media;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

using Grid = System.Windows.Controls.Grid;

namespace RevitCivilConnector.ui
{
    public class ProfileGridWindow : Window
    {
        public ProfileGridConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;

        private TextBox txtStationInterval;
        private TextBox txtElevInterval;
        
        private RadioButton rbElevAuto;
        private RadioButton rbElevManual;
        private TextBox txtElevBase;
        private TextBox txtElevTop;
        
        private TextBox txtSectionPrefix;
        private ComboBox cmbTemplates;

        // Styling
        private ComboBox cmbFrameStyle;
        private ComboBox cmbGridStyle;
        private ComboBox cmbExtStyle;
        private TextBox txtExtLength;
        private TextBox txtPlanTick;

        private List<string> _lineStyles;
        private Dictionary<string, ElementId> _templates;

        public ProfileGridWindow(List<string> lineStyles, Dictionary<string, ElementId> templates)
        {
            Config = new ProfileGridConfig();
            _lineStyles = lineStyles;
            _templates = templates;
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Configuración de Perfil y Sección";
            this.Width = 480; 
            this.Height = 600; 
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(Colors.WhiteSmoke);

            StackPanel mainStack = new StackPanel { Margin = new Thickness(15) };

            // 1. Grid Settings
            GroupBox grpGrid = new GroupBox { Header = "Geometría del Gráfico", FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            Grid grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.6, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            grid.Children.Add(CreateLabel("Int. Estación (m):", 0, 0));
            txtStationInterval = new TextBox { Text = "10.00", Margin = new Thickness(2) };
            Grid.SetRow(txtStationInterval, 0); Grid.SetColumn(txtStationInterval, 1);
            grid.Children.Add(txtStationInterval);

            grid.Children.Add(CreateLabel("Int. Elevación (m):", 1, 0));
            txtElevInterval = new TextBox { Text = "1.00", Margin = new Thickness(2) };
            Grid.SetRow(txtElevInterval, 1); Grid.SetColumn(txtElevInterval, 1);
            grid.Children.Add(txtElevInterval);
            
            grid.Children.Add(CreateLabel("Long. Proyección (m):", 2, 0));
            txtExtLength = new TextBox { Text = "2.00", Margin = new Thickness(2) };
            Grid.SetRow(txtExtLength, 2); Grid.SetColumn(txtExtLength, 1);
            grid.Children.Add(txtExtLength);
            
            grid.Children.Add(CreateLabel("Tamaño Tick Planta (m):", 3, 0));
            txtPlanTick = new TextBox { Text = "2.00", Margin = new Thickness(2) };
            Grid.SetRow(txtPlanTick, 3); Grid.SetColumn(txtPlanTick, 1);
            grid.Children.Add(txtPlanTick);

            grpGrid.Content = grid;
            mainStack.Children.Add(grpGrid);

            // 2. Styles Settings
            GroupBox grpStyles = new GroupBox { Header = "Estilos Visuales", Margin = new Thickness(0,10,0,0), FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            Grid gridStyles = new Grid();
            gridStyles.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.6, GridUnitType.Star) });
            gridStyles.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
            
            gridStyles.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridStyles.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridStyles.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // Frame
            gridStyles.Children.Add(CreateLabel("Borde/Marco:", 0, 0));
            cmbFrameStyle = new ComboBox { ItemsSource = _lineStyles, Margin = new Thickness(2) };
            SelectOrFirst(cmbFrameStyle, "Wide Lines", "Líneas anchas");
            Grid.SetRow(cmbFrameStyle, 0); Grid.SetColumn(cmbFrameStyle, 1);
            gridStyles.Children.Add(cmbFrameStyle);

            // Grid
            gridStyles.Children.Add(CreateLabel("Cuadrícula:", 1, 0));
            cmbGridStyle = new ComboBox { ItemsSource = _lineStyles, Margin = new Thickness(2) };
            SelectOrFirst(cmbGridStyle, "Thin Lines", "Líneas finas");
            Grid.SetRow(cmbGridStyle, 1); Grid.SetColumn(cmbGridStyle, 1);
            gridStyles.Children.Add(cmbGridStyle);

            // Extensions
            gridStyles.Children.Add(CreateLabel("Proyecciones:", 2, 0));
            cmbExtStyle = new ComboBox { ItemsSource = _lineStyles, Margin = new Thickness(2) };
            SelectOrFirst(cmbExtStyle, "Medium Lines", "Líneas medias");
            Grid.SetRow(cmbExtStyle, 2); Grid.SetColumn(cmbExtStyle, 1);
            gridStyles.Children.Add(cmbExtStyle);

            grpStyles.Content = gridStyles;
            mainStack.Children.Add(grpStyles);

            // 3. Range Settings
            GroupBox grpRange = new GroupBox { Header = "Rango Vertical", Margin = new Thickness(0,10,0,0), FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            StackPanel stackRange = new StackPanel();
            
            rbElevAuto = new RadioButton { Content = "Automático (Detectar Z)", IsChecked = true, Margin = new Thickness(2) };
            rbElevAuto.Checked += (s,e) => ToggleManualInputs(false);
            stackRange.Children.Add(rbElevAuto);

            rbElevManual = new RadioButton { Content = "Manual", Margin = new Thickness(2) };
            rbElevManual.Checked += (s,e) => ToggleManualInputs(true);
            stackRange.Children.Add(rbElevManual);

            Grid gridMan = new Grid { Margin = new Thickness(10,5,0,0) };
            gridMan.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            gridMan.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridMan.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridMan.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            gridMan.Children.Add(CreateLabel("Base (m):", 0, 0));
            txtElevBase = new TextBox { Text = "100.00", IsEnabled = false, Margin = new Thickness(2) };
            Grid.SetRow(txtElevBase, 0); Grid.SetColumn(txtElevBase, 1);
            gridMan.Children.Add(txtElevBase);

            gridMan.Children.Add(CreateLabel("Tope (m):", 1, 0));
            txtElevTop = new TextBox { Text = "110.00", IsEnabled = false, Margin = new Thickness(2) };
            Grid.SetRow(txtElevTop, 1); Grid.SetColumn(txtElevTop, 1);
            gridMan.Children.Add(txtElevTop);

            stackRange.Children.Add(gridMan);
            grpRange.Content = stackRange;
            mainStack.Children.Add(grpRange);
            
            // 4. Section Configuration
            GroupBox grpSec = new GroupBox { Header = "Configuración de Sección", Margin = new Thickness(0,10,0,0), FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            Grid gridSec = new Grid();
            gridSec.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.6, GridUnitType.Star) });
            gridSec.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
            gridSec.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridSec.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            gridSec.Children.Add(CreateLabel("Prefijo Nombre:", 0, 0));
            txtSectionPrefix = new TextBox { Text = "SECCION", Margin = new Thickness(2) };
            Grid.SetRow(txtSectionPrefix, 0); Grid.SetColumn(txtSectionPrefix, 1);
            gridSec.Children.Add(txtSectionPrefix);

            gridSec.Children.Add(CreateLabel("View Template:", 1, 0));
            cmbTemplates = new ComboBox { Margin = new Thickness(2) };
            // Populate
            cmbTemplates.Items.Add("<Ninguno>");
            foreach(var kvp in _templates)
                cmbTemplates.Items.Add(kvp.Key);
            cmbTemplates.SelectedIndex = 0;
            
            Grid.SetRow(cmbTemplates, 1); Grid.SetColumn(cmbTemplates, 1);
            gridSec.Children.Add(cmbTemplates);

            grpSec.Content = gridSec;
            mainStack.Children.Add(grpSec);

            // Buttons
            StackPanel stackBtns = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0,20,0,0) };
            Button btnOk = new Button { Content = "GENERAR", Width = 100, Height = 30, Margin = new Thickness(5), Background = new SolidColorBrush(Colors.LightSkyBlue), FontWeight = FontWeights.Bold };
            btnOk.Click += BtnOk_Click;
            Button btnCancel = new Button { Content = "Cancelar", Width = 80, Height = 30, Margin = new Thickness(5) };
            btnCancel.Click += (s, e) => Close();
            
            stackBtns.Children.Add(btnOk);
            stackBtns.Children.Add(btnCancel);
            mainStack.Children.Add(stackBtns);

            this.Content = mainStack;
        }

        private void SelectOrFirst(ComboBox cmb, string preferred1, string preferred2)
        {
            if (cmb.Items.Count == 0) return;
            foreach(var item in cmb.Items)
            {
                string s = item.ToString();
                if (s.Equals(preferred1, StringComparison.OrdinalIgnoreCase) || s.Equals(preferred2, StringComparison.OrdinalIgnoreCase))
                {
                    cmb.SelectedItem = item;
                    return;
                }
            }
            cmb.SelectedIndex = 0;
        }

        private TextBlock CreateLabel(string text, int row, int col)
        {
            TextBlock tb = new TextBlock { Text = text, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(2) };
            Grid.SetRow(tb, row);
            Grid.SetColumn(tb, col);
            return tb;
        }

        private void ToggleManualInputs(bool enable)
        {
            if(txtElevBase != null) txtElevBase.IsEnabled = enable;
            if(txtElevTop != null) txtElevTop.IsEnabled = enable;
        }

        private double ParseToDouble(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return 0;
            string normalized = text.Replace(',', '.');
            if (double.TryParse(normalized, NumberStyles.Any, CultureInfo.InvariantCulture, out double val))
                return val;
            return 0;
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            Config.StationInterval = ParseToDouble(txtStationInterval.Text);
            Config.ElevationInterval = ParseToDouble(txtElevInterval.Text);
            Config.AxisExtensionLength = ParseToDouble(txtExtLength.Text);
            Config.PlanTickSize = ParseToDouble(txtPlanTick.Text);
            
            Config.AutoElevation = rbElevAuto.IsChecked == true;
            if (!Config.AutoElevation)
            {
                Config.ElevationBase = ParseToDouble(txtElevBase.Text);
                Config.ElevationTop = ParseToDouble(txtElevTop.Text);
            }
            
            Config.SectionNamePrefix = txtSectionPrefix.Text;

            // Template
            if (cmbTemplates.SelectedItem != null)
            {
                string sel = cmbTemplates.SelectedItem.ToString();
                if (_templates.ContainsKey(sel))
                    Config.SelectedTemplateId = _templates[sel];
            }

            if (cmbFrameStyle.SelectedItem != null) Config.FrameLineStyle = cmbFrameStyle.SelectedItem.ToString();
            if (cmbGridStyle.SelectedItem != null) Config.GridLineStyle = cmbGridStyle.SelectedItem.ToString();
            if (cmbExtStyle.SelectedItem != null) Config.ExtensionLineStyle = cmbExtStyle.SelectedItem.ToString();

            IsConfirmed = true;
            Close();
        }
    }
}
