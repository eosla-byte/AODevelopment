using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

using Grid = System.Windows.Controls.Grid;

namespace RevitCivilConnector.ui
{
    public class TagPipesWindow : Window
    {
        public TagPipesConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;
        private List<FamilySymbol> _tagSymbols;
        private List<string> _categories;

        // UI Controls
        private RadioButton rbSelectManual;
        private RadioButton rbSelectView;
        private ComboBox cmbCategory;
        private TextBox txtParamName;
        private TextBox txtParamValue;

        private TagSectionUi uiStart;
        private TagSectionUi uiMid;
        private TagSectionUi uiEnd;

        public TagPipesWindow(List<FamilySymbol> tags, List<string> categories)
        {
            Config = new TagPipesConfig();
            _tagSymbols = tags;
            _categories = categories;
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Etiquetado de Tuberías y Ductos (MEP)";
            this.Width = 550;
            this.Height = 700;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(Colors.WhiteSmoke);

            ScrollViewer scroll = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            StackPanel mainStack = new StackPanel { Margin = new Thickness(15) };
            
            // 1. Selection Mode
            GroupBox grpSel = new GroupBox { Header = "Selección", FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            StackPanel stackSel = new StackPanel();
            
            rbSelectManual = new RadioButton { Content = "Seleccionar Manualmente", IsChecked = true, Margin = new Thickness(2) };
            stackSel.Children.Add(rbSelectManual);
            
            rbSelectView = new RadioButton { Content = "Todos en Vista Actual", Margin = new Thickness(2) };
            stackSel.Children.Add(rbSelectView);

            StackPanel stackFilter = new StackPanel { Margin = new Thickness(20, 5, 0, 0) };
            stackFilter.Children.Add(new TextBlock { Text = "Categoría:" });
            cmbCategory = new ComboBox { ItemsSource = _categories, SelectedIndex = 0, Margin = new Thickness(0,0,0,5) };
            stackFilter.Children.Add(cmbCategory);

            stackFilter.Children.Add(new TextBlock { Text = "Filtro (Opcional) - Parametro = Valor:" });
            Grid gridParam = new Grid();
            gridParam.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridParam.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            gridParam.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            txtParamName = new TextBox { Margin = new Thickness(0,0,5,0), ToolTip = "Nombre del Parámetro" };
            gridParam.Children.Add(txtParamName);
            
            TextBlock eq = new TextBlock { Text = "=", VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(eq, 1);
            gridParam.Children.Add(eq);

            txtParamValue = new TextBox { Margin = new Thickness(5,0,0,0), ToolTip = "Valor" };
            Grid.SetColumn(txtParamValue, 2);
            gridParam.Children.Add(txtParamValue);
            
            stackFilter.Children.Add(gridParam);
            stackSel.Children.Add(stackFilter);
            
            grpSel.Content = stackSel;
            mainStack.Children.Add(grpSel);

            // 2. Tags Config
            uiStart = CreateTagSection("Etiqueta Inicio (Start)", _tagSymbols);
            mainStack.Children.Add(uiStart.Group);

            uiMid = CreateTagSection("Etiqueta Centro (Mid)", _tagSymbols);
            uiMid.CheckEnable.IsChecked = true; // Default
            mainStack.Children.Add(uiMid.Group);

            uiEnd = CreateTagSection("Etiqueta Final (End)", _tagSymbols);
            mainStack.Children.Add(uiEnd.Group);

            // Buttons
            StackPanel stackBtns = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 20, 0, 0) };
            Button btnOk = new Button { Content = "ETIQUETAR", Width = 120, Height = 35, Margin = new Thickness(5), Background = new SolidColorBrush(Colors.LightSkyBlue), FontWeight = FontWeights.Bold };
            btnOk.Click += BtnOk_Click;
            Button btnCancel = new Button { Content = "Cancelar", Width = 80, Height = 35, Margin = new Thickness(5) };
            btnCancel.Click += (s, e) => Close();

            stackBtns.Children.Add(btnOk);
            stackBtns.Children.Add(btnCancel);
            mainStack.Children.Add(stackBtns);

            scroll.Content = mainStack;
            this.Content = scroll;
        }

        private class TagSectionUi
        {
            public GroupBox Group;
            public CheckBox CheckEnable;
            public ComboBox ComboFamily;
            public TextBox TextOffset;
            public CheckBox CheckLeader;
            public ComboBox ComboOrientation;
        }

        private TagSectionUi CreateTagSection(string title, List<FamilySymbol> symbols)
        {
            TagSectionUi ui = new TagSectionUi();
            ui.Group = new GroupBox { Header = title, Margin = new Thickness(0, 10, 0, 0), FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            
            Grid grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(120) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // Enable
            ui.CheckEnable = new CheckBox { Content = "Habilitar esta etiqueta", FontWeight = FontWeights.Normal, Margin = new Thickness(2) };
            Grid.SetColumnSpan(ui.CheckEnable, 2);
            grid.Children.Add(ui.CheckEnable);

            // Family
            TextBlock lblFam = new TextBlock { Text = "Tipo de Etiqueta:", VerticalAlignment = VerticalAlignment.Center, FontWeight = FontWeights.Normal };
            Grid.SetRow(lblFam, 1);
            grid.Children.Add(lblFam);

            ui.ComboFamily = new ComboBox { Margin = new Thickness(2), FontWeight = FontWeights.Normal, DisplayMemberPath = "Name" };
            foreach (var s in symbols) ui.ComboFamily.Items.Add(s);
            if(ui.ComboFamily.Items.Count > 0) ui.ComboFamily.SelectedIndex = 0;
            Grid.SetRow(ui.ComboFamily, 1); Grid.SetColumn(ui.ComboFamily, 1);
            grid.Children.Add(ui.ComboFamily);

            // Offset
            TextBlock lblOff = new TextBlock { Text = "Separación (m):", VerticalAlignment = VerticalAlignment.Center, FontWeight = FontWeights.Normal };
            Grid.SetRow(lblOff, 2);
            grid.Children.Add(lblOff);
            
            ui.TextOffset = new TextBox { Text = "0.20", Margin = new Thickness(2), FontWeight = FontWeights.Normal };
            Grid.SetRow(ui.TextOffset, 2); Grid.SetColumn(ui.TextOffset, 1);
            grid.Children.Add(ui.TextOffset);

            // Leader
            ui.CheckLeader = new CheckBox { Content = "Directriz (Leader)", Margin = new Thickness(2), FontWeight = FontWeights.Normal };
            Grid.SetRow(ui.CheckLeader, 3); Grid.SetColumn(ui.CheckLeader, 1);
            grid.Children.Add(ui.CheckLeader);

            // Orientation
            TextBlock lblOri = new TextBlock { Text = "Orientación:", VerticalAlignment = VerticalAlignment.Center, FontWeight = FontWeights.Normal };
            Grid.SetRow(lblOri, 4);
            grid.Children.Add(lblOri);

            ui.ComboOrientation = new ComboBox { Margin = new Thickness(2), FontWeight = FontWeights.Normal };
            ui.ComboOrientation.Items.Add(TagOrientation.Horizontal);
            ui.ComboOrientation.Items.Add(TagOrientation.Vertical);
            ui.ComboOrientation.SelectedIndex = 0;
            Grid.SetRow(ui.ComboOrientation, 4); Grid.SetColumn(ui.ComboOrientation, 1);
            grid.Children.Add(ui.ComboOrientation);
            
            ui.Group.Content = grid;
            
            // Toggle Logic
            ui.CheckEnable.Checked += (s, e) => ToggleSection(ui, true);
            ui.CheckEnable.Unchecked += (s, e) => ToggleSection(ui, false);
            ToggleSection(ui, false);

            return ui;
        }

        private void ToggleSection(TagSectionUi ui, bool enable)
        {
            ui.ComboFamily.IsEnabled = enable;
            ui.TextOffset.IsEnabled = enable;
            ui.CheckLeader.IsEnabled = enable;
            ui.ComboOrientation.IsEnabled = enable;
        }

        private double ParseDouble(string s)
        {
            if (string.IsNullOrWhiteSpace(s)) return 0;
            s = s.Replace(',', '.');
            if (double.TryParse(s, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out double v)) return v;
            return 0;
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            Config.SelectByView = rbSelectView.IsChecked == true;
            if (cmbCategory.SelectedItem != null) Config.TargetCategory = cmbCategory.SelectedItem.ToString();
            Config.FilterParamName = txtParamName.Text;
            Config.FilterParamValue = txtParamValue.Text;

            SaveSection(uiStart, Config.StartTag);
            SaveSection(uiMid, Config.MidTag);
            SaveSection(uiEnd, Config.EndTag);

            IsConfirmed = true;
            Close();
        }

        private void SaveSection(TagSectionUi ui, TagPositionConfig conf)
        {
            conf.Enabled = ui.CheckEnable.IsChecked == true;
            if (ui.ComboFamily.SelectedItem is FamilySymbol fs) conf.TagSymbolId = fs.Id;
            conf.Offset = ParseDouble(ui.TextOffset.Text);
            conf.HasLeader = ui.CheckLeader.IsChecked == true;
            if(ui.ComboOrientation.SelectedItem is TagOrientation to) conf.Orientation = to;
        }
    }
}
