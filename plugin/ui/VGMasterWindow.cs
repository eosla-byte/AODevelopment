using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Shapes;
using RevitCivilConnector.models;

using Grid = System.Windows.Controls.Grid;
using Color = System.Windows.Media.Color;
using SolidColorBrush = System.Windows.Media.SolidColorBrush;
using RevitColor = Autodesk.Revit.DB.Color;

namespace RevitCivilConnector.ui
{
    public class VGMasterWindow : Window
    {
        public VGMasterConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;

        // UI Controls
        private ComboBox cmbProjColor;
        private ComboBox cmbProjWeight;
        private CheckBox chkProjOverride;

        private ComboBox cmbCutColor;
        private ComboBox cmbCutWeight;
        private CheckBox chkCutOverride;

        private ComboBox cmbSurfColor;
        private CheckBox chkSurfSolid;
        private CheckBox chkSurfOverride;
        
        private Slider sldTransparency;
        private CheckBox chkHalftone;

        private List<ColorItem> _colors;
        private List<int> _weights;

        public VGMasterWindow()
        {
            Config = new VGMasterConfig();
            InitializeData();
            InitializeUI();
        }

        private void InitializeData()
        {
            _colors = new List<ColorItem>
            {
                new ColorItem("Black", Colors.Black),
                new ColorItem("Gray", Colors.Gray),
                new ColorItem("DarkGray", Colors.DarkGray),
                new ColorItem("Silver", Colors.Silver),
                new ColorItem("White", Colors.White),
                new ColorItem("Red", Colors.Red),
                new ColorItem("DarkRed", Colors.DarkRed),
                new ColorItem("Orange", Colors.Orange),
                new ColorItem("Gold", Colors.Gold),
                new ColorItem("Yellow", Colors.Yellow),
                new ColorItem("Green", Colors.Green),
                new ColorItem("DarkGreen", Colors.DarkGreen),
                new ColorItem("Teal", Colors.Teal),
                new ColorItem("Cyan", Colors.Cyan),
                new ColorItem("DeepSkyBlue", Colors.DeepSkyBlue),
                new ColorItem("Blue", Colors.Blue),
                new ColorItem("Navy", Colors.Navy),
                new ColorItem("BlueViolet", Colors.BlueViolet),
                new ColorItem("Purple", Colors.Purple),
                new ColorItem("Magenta", Colors.Magenta),
                new ColorItem("Pink", Colors.Pink),
                new ColorItem("Chocolate", Colors.Chocolate),
                new ColorItem("Brown", Colors.Brown),
                new ColorItem("Maroon", Colors.Maroon)
            };

            _weights = Enumerable.Range(1, 16).ToList();
        }

        private void InitializeUI()
        {
            this.Title = "VG Master - Element Graphics Override";
            this.Width = 400;
            this.Height = 550;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(Color.FromRgb(40, 40, 40)); 

            StackPanel mainStack = new StackPanel { Margin = new Thickness(15) };

            // Title
            TextBlock title = new TextBlock 
            { 
                Text = "VG MASTER", 
                Foreground = Brushes.White, 
                FontSize = 20, 
                FontWeight = FontWeights.Bold, 
                HorizontalAlignment = HorizontalAlignment.Center,
                Margin = new Thickness(0,0,0,15)
            };
            mainStack.Children.Add(title);

            // 1. Projection Lines
            mainStack.Children.Add(CreateHeader("Líneas de Proyección", 
                out chkProjOverride, (s,e) => ToggleSection(chkProjOverride, cmbProjColor, cmbProjWeight)));
            
            Grid gridProj = CreateColorWeightGrid(out cmbProjColor, out cmbProjWeight);
            mainStack.Children.Add(gridProj);
            ToggleSection(chkProjOverride, cmbProjColor, cmbProjWeight);

            // 2. Cut Lines
            mainStack.Children.Add(CreateHeader("Líneas de Corte",
                out chkCutOverride, (s,e) => ToggleSection(chkCutOverride, cmbCutColor, cmbCutWeight)));
            Grid gridCut = CreateColorWeightGrid(out cmbCutColor, out cmbCutWeight);
            mainStack.Children.Add(gridCut);
            ToggleSection(chkCutOverride, cmbCutColor, cmbCutWeight);

            // 3. Surface Pattern
            mainStack.Children.Add(CreateHeader("Patrón de Superficie",
                out chkSurfOverride, (s,e) => ToggleSection(chkSurfOverride, cmbSurfColor, chkSurfSolid)));
            
            Grid gridSurf = new Grid { Margin = new Thickness(0,0,0,10) };
            gridSurf.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridSurf.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            cmbSurfColor = CreateColorCombo();
            gridSurf.Children.Add(cmbSurfColor); Grid.SetColumn(cmbSurfColor, 0);

            chkSurfSolid = new CheckBox { Content = "Relleno Sólido", Foreground = Brushes.White, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(5,0,0,0) };
            gridSurf.Children.Add(chkSurfSolid); Grid.SetColumn(chkSurfSolid, 1);
            
            mainStack.Children.Add(gridSurf);
            ToggleSection(chkSurfOverride, cmbSurfColor, chkSurfSolid);

            // 4. Halftone & Transparency
            GroupBox grpVis = new GroupBox { Header = "Visibilidad", Foreground = Brushes.White, Margin = new Thickness(0,10,0,10), BorderBrush = Brushes.Gray };
            StackPanel stackVis = new StackPanel { Margin = new Thickness(5) };
            
            chkHalftone = new CheckBox { Content = "Halftone (Medio Tono)", Foreground = Brushes.White, Margin = new Thickness(0,0,0,5) };
            stackVis.Children.Add(chkHalftone);

            DockPanel dockTrans = new DockPanel();
            TextBlock lblTrans = new TextBlock { Text = "Transparencia: ", Foreground = Brushes.White, Width = 100 };
            sldTransparency = new Slider { Minimum = 0, Maximum = 100, TickFrequency = 1, IsSnapToTickEnabled = true, AutoToolTipPlacement = System.Windows.Controls.Primitives.AutoToolTipPlacement.TopLeft };
            DockPanel.SetDock(lblTrans, Dock.Left);
            dockTrans.Children.Add(lblTrans);
            dockTrans.Children.Add(sldTransparency);
            stackVis.Children.Add(dockTrans);

            grpVis.Content = stackVis;
            mainStack.Children.Add(grpVis);

            // Buttons
            Grid gridBtns = new Grid { Margin = new Thickness(0,10,0,0) };
            gridBtns.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridBtns.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridBtns.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            Button btnReset = new Button { Content = "Reset Graficos", Background = Brushes.Gray, Foreground = Brushes.White, Margin = new Thickness(2) };
            btnReset.Click += BtnReset_Click;
            
            Button btnCancel = new Button { Content = "Cancelar", Background = Brushes.DarkRed, Foreground = Brushes.White, Margin = new Thickness(2) };
            btnCancel.Click += (s, e) => Close();

            Button btnApply = new Button { Content = "APLICAR", Background = Brushes.DodgerBlue, Foreground = Brushes.White, FontWeight = FontWeights.Bold, Margin = new Thickness(2) };
            btnApply.Click += BtnApply_Click;

            gridBtns.Children.Add(btnReset); Grid.SetColumn(btnReset, 0);
            gridBtns.Children.Add(btnCancel); Grid.SetColumn(btnCancel, 1);
            gridBtns.Children.Add(btnApply); Grid.SetColumn(btnApply, 2);

            mainStack.Children.Add(gridBtns);

            this.Content = mainStack;
        }

        private UIElement CreateHeader(string text, out CheckBox chk, RoutedEventHandler toggleInfo)
        {
            StackPanel sp = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0,5,0,5) };
            chk = new CheckBox { IsChecked = false, VerticalAlignment = VerticalAlignment.Center };
            chk.Checked += toggleInfo;
            chk.Unchecked += toggleInfo;
            
            TextBlock tb = new TextBlock { Text = text, Foreground = Brushes.LightGray, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(5,0,0,0), FontWeight = FontWeights.SemiBold };
            
            sp.Children.Add(chk);
            sp.Children.Add(tb);
            return sp;
        }

        private Grid CreateColorWeightGrid(out ComboBox cmbColor, out ComboBox cmbWeight)
        {
            Grid g = new Grid { Margin = new Thickness(0,0,0,10) };
            g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(2, GridUnitType.Star) });
            g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            cmbColor = CreateColorCombo();
            cmbWeight = new ComboBox { ItemsSource = _weights, SelectedIndex = 0, Margin = new Thickness(5,0,0,0) };
            
            g.Children.Add(cmbColor); Grid.SetColumn(cmbColor, 0);
            g.Children.Add(cmbWeight); Grid.SetColumn(cmbWeight, 1);
            return g;
        }

        private ComboBox CreateColorCombo()
        {
            ComboBox cmb = new ComboBox();
            cmb.ItemsSource = _colors;
            cmb.SelectedIndex = 0;
            // Template
            DataTemplate dt = new DataTemplate();
            FrameworkElementFactory panel = new FrameworkElementFactory(typeof(StackPanel));
            panel.SetValue(StackPanel.OrientationProperty, Orientation.Horizontal);
            
            FrameworkElementFactory rect = new FrameworkElementFactory(typeof(Rectangle));
            rect.SetValue(Rectangle.WidthProperty, 15.0);
            rect.SetValue(Rectangle.HeightProperty, 15.0);
            rect.SetValue(Rectangle.MarginProperty, new Thickness(0,0,5,0));
            rect.SetBinding(Rectangle.FillProperty, new System.Windows.Data.Binding("Brush"));
            
            FrameworkElementFactory text = new FrameworkElementFactory(typeof(TextBlock));
            text.SetBinding(TextBlock.TextProperty, new System.Windows.Data.Binding("Name"));
            
            panel.AppendChild(rect);
            panel.AppendChild(text);
            dt.VisualTree = panel;
            
            cmb.ItemTemplate = dt;
            return cmb;
        }

        private void ToggleSection(CheckBox activator, params Control[] controls)
        {
            bool enabled = activator.IsChecked == true;
            foreach(var c in controls) c.IsEnabled = enabled;
        }

        private void BtnReset_Click(object sender, RoutedEventArgs e)
        {
            Config.ResetOverrides = true;
            IsConfirmed = true;
            Close();
        }

        private void BtnApply_Click(object sender, RoutedEventArgs e)
        {
            Config.ResetOverrides = false;
            
            Config.OverrideProjLines = chkProjOverride.IsChecked == true;
            if(Config.OverrideProjLines)
            {
                if(cmbProjColor.SelectedItem is ColorItem ci) Config.ProjLineColor = ToRevitColor(ci.Color);
                if(cmbProjWeight.SelectedItem is int w) Config.ProjLineWeight = w;
            }

            Config.OverrideCutLines = chkCutOverride.IsChecked == true;
            if (Config.OverrideCutLines)
            {
                if (cmbCutColor.SelectedItem is ColorItem ci) Config.CutLineColor = ToRevitColor(ci.Color);
                if (cmbCutWeight.SelectedItem is int w) Config.CutLineWeight = w;
            }

            Config.OverrideSurfacePattern = chkSurfOverride.IsChecked == true;
            if (Config.OverrideSurfacePattern)
            {
                if(cmbSurfColor.SelectedItem is ColorItem ci) Config.SurfacePatternColor = ToRevitColor(ci.Color);
                Config.SolidFillSurface = chkSurfSolid.IsChecked == true;
            }

            Config.ApplyHalftone = chkHalftone.IsChecked == true;
            Config.Transparency = (int)sldTransparency.Value;

            IsConfirmed = true;
            Close();
        }

        private RevitColor ToRevitColor(Color c)
        {
            return new RevitColor(c.R, c.G, c.B);
        }

        public class ColorItem
        {
            public string Name { get; set; }
            public Color Color { get; set; }
            public SolidColorBrush Brush { get; set; }
            public ColorItem(string n, Color c) 
            { 
                Name = n; 
                Color = c; 
                Brush = new SolidColorBrush(c); 
            }
        }
    }
}
