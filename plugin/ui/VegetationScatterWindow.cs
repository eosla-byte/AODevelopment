using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

using ComboBox = System.Windows.Controls.ComboBox;
using ListBox = System.Windows.Controls.ListBox;
using CheckBox = System.Windows.Controls.CheckBox;
using TextBox = System.Windows.Controls.TextBox;
using Button = System.Windows.Controls.Button;
using Grid = System.Windows.Controls.Grid;

namespace RevitCivilConnector.ui
{
    public class VegetationScatterWindow : Window
    {
        public VegetationScatterConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;
        private Document _doc;

        private ListBox lbFamilies;
        private TextBox txtCount;
        private TextBox txtSpacing;
        private RadioButton rbCount;
        private RadioButton rbSpacing;
        
        private TextBox txtMinScale;
        private TextBox txtMaxScale;
        private CheckBox chkRotation;

        public VegetationScatterWindow(Document doc)
        {
            _doc = doc;
            Config = new VegetationScatterConfig();
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Generador de Vegetación - Scatter";
            this.Width = 400;
            this.Height = 600;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(30, 30, 30));

            StackPanel main = new StackPanel { Margin = new Thickness(15) };
            
            // Header
            main.Children.Add(new TextBlock { Text = "SCATTER VEGETATION", Foreground = Brushes.White, FontSize = 18, FontWeight = FontWeights.Bold, Margin = new Thickness(0,0,0,15) });

            // 1. Family Selector
            main.Children.Add(Label("Seleccionar Familias (Planting):"));
            lbFamilies = new ListBox { Height = 150, Margin = new Thickness(0,5,0,15), SelectionMode = SelectionMode.Multiple };
            PopulateFamilies();
            main.Children.Add(lbFamilies);

            // 2. Density / Quantity
            GroupBox grpMode = new GroupBox { Header = "Densidad / Cantidad", Foreground = Brushes.White, Margin = new Thickness(0,0,0,15) };
            StackPanel stackMode = new StackPanel { Margin = new Thickness(5) };
            
            rbSpacing = new RadioButton { Content = "Por Espaciamiento (m)", IsChecked = true, Foreground = Brushes.White, Margin = new Thickness(0,0,0,5) };
            rbSpacing.Checked += (s, e) => ToggleModes();
            stackMode.Children.Add(rbSpacing);

            txtSpacing = new TextBox { Text = "2.0", Margin = new Thickness(20,0,0,5) };
            stackMode.Children.Add(txtSpacing);

            rbCount = new RadioButton { Content = "Cantidad Fija", Foreground = Brushes.White, Margin = new Thickness(0,5,0,5) };
            rbCount.Checked += (s, e) => ToggleModes();
            stackMode.Children.Add(rbCount);

            txtCount = new TextBox { Text = "50", IsEnabled = false, Margin = new Thickness(20,0,0,5) };
            stackMode.Children.Add(txtCount);

            grpMode.Content = stackMode;
            main.Children.Add(grpMode);

            // 3. Randomization
            GroupBox grpRnd = new GroupBox { Header = "Aleatoriedad", Foreground = Brushes.White };
            StackPanel stackRnd = new StackPanel { Margin = new Thickness(5) };

            Grid gridScale = new Grid();
            gridScale.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridScale.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridScale.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridScale.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            gridScale.Children.Add(Label("Escala Min:", 0, 0));
            txtMinScale = new TextBox { Text = "0.8", Margin = new Thickness(2) };
            gridScale.Children.Add(txtMinScale); Grid.SetRow(txtMinScale, 1); Grid.SetColumn(txtMinScale, 0);

            gridScale.Children.Add(Label("Escala Max:", 0, 1));
            txtMaxScale = new TextBox { Text = "1.2", Margin = new Thickness(2), HorizontalAlignment=HorizontalAlignment.Stretch };
            gridScale.Children.Add(txtMaxScale); Grid.SetRow(txtMaxScale, 1); Grid.SetColumn(txtMaxScale, 1);
            
            stackRnd.Children.Add(gridScale);

            chkRotation = new CheckBox { Content = "Rotación Aleatoria (360°)", IsChecked = true, Foreground = Brushes.White, Margin = new Thickness(0,10,0,0) };
            stackRnd.Children.Add(chkRotation);

            grpRnd.Content = stackRnd;
            main.Children.Add(grpRnd);

            // Button
            Button btnGen = new Button { Content = "GENERAR", Height = 40, Margin = new Thickness(0,20,0,0), Background = Brushes.ForestGreen, Foreground = Brushes.White, FontWeight = FontWeights.Bold };
            btnGen.Click += BtnGen_Click;
            main.Children.Add(btnGen);

            this.Content = main;
        }

        private void PopulateFamilies()
        {
             var symbols = new FilteredElementCollector(_doc)
                 .OfClass(typeof(FamilySymbol))
                 .OfCategory(BuiltInCategory.OST_Planting)
                 .Cast<FamilySymbol>()
                 .OrderBy(x => x.Name)
                 .ToList();
            
             foreach(var sym in symbols)
             {
                 lbFamilies.Items.Add(new FamilyItem { Name = sym.FamilyName + ": " + sym.Name, Symbol = sym });
             }
        }

        private TextBlock Label(string t, int r = 0, int c = 0) 
        {
            TextBlock tb = new TextBlock { Text = t, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center };
            if(r>0 || c>0) { Grid.SetRow(tb, r); Grid.SetColumn(tb, c); }
            return tb;
        }

        private void ToggleModes()
        {
            bool isSpacing = rbSpacing.IsChecked == true;
            if(txtSpacing != null) txtSpacing.IsEnabled = isSpacing;
            if(txtCount != null) txtCount.IsEnabled = !isSpacing;
        }

        private void BtnGen_Click(object sender, RoutedEventArgs e)
        {
            if (lbFamilies.SelectedItems.Count == 0)
            {
                MessageBox.Show("Selecciona al menos una familia.");
                return;
            }

            foreach(FamilyItem item in lbFamilies.SelectedItems)
            {
                Config.SelectedFamilies.Add(item.Symbol);
            }

            Config.UseFixedCount = rbCount.IsChecked == true;
            if (int.TryParse(txtCount.Text, out int c)) Config.TotalCount = c;
            if (double.TryParse(txtSpacing.Text, out double s)) Config.Spacing = s;

            if (double.TryParse(txtMinScale.Text, out double minS)) Config.MinScale = minS;
            if (double.TryParse(txtMaxScale.Text, out double maxS)) Config.MaxScale = maxS;
            
            Config.RandomRotation = chkRotation.IsChecked == true;

            IsConfirmed = true;
            Close();
        }

        public class FamilyItem
        {
            public string Name { get; set; }
            public FamilySymbol Symbol { get; set; }
            public override string ToString() => Name;
        }
    }
}
