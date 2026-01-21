using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

// Aliases
using Button = System.Windows.Controls.Button;
using ComboBox = System.Windows.Controls.ComboBox;
using TextBox = System.Windows.Controls.TextBox;
using CheckBox = System.Windows.Controls.CheckBox;
using Label = System.Windows.Controls.TextBlock;

namespace RevitCivilConnector.ui
{
    public class DWGImportWindow : Window
    {
        public DWGImportConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;
        private Document _doc;

        // UI Controls
        private TextBox txtFile;
        private ComboBox cmbTarget;
        private TextBox txtName;
        
        private ComboBox cmbLines;
        private ComboBox cmbTexts;
        private ComboBox cmbHatch;

        private CheckBox chkMask;

        public DWGImportWindow(Document doc)
        {
            _doc = doc;
            Config = new DWGImportConfig();
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Importar DWG a Nativo";
            this.Width = 500;
            this.Height = 550;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(System.Windows.Media.Color.FromRgb(40, 40, 40));

            StackPanel main = new StackPanel { Margin = new Thickness(15) };
            
            // Header
            main.Children.Add(CreateHeader("IMPORTADOR DWG"));

            // 1. Archivo
            main.Children.Add(CreateLabel("Seleccionar DWG:"));
            
            System.Windows.Controls.Grid fileGrid = new System.Windows.Controls.Grid();
            fileGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            fileGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            
            txtFile = new TextBox { IsReadOnly = true, Margin = new Thickness(0,0,5,5) };
            Button btnBrowse = new Button { Content = "...", Width = 30, Height=25, Margin = new Thickness(0,0,0,5) };
            btnBrowse.Click += BtnBrowse_Click;
            
            fileGrid.Children.Add(txtFile); UiGridSet(txtFile, 0, 0);
            fileGrid.Children.Add(btnBrowse); UiGridSet(btnBrowse, 0, 1);
            
            main.Children.Add(fileGrid);

            // 2. Target
            main.Children.Add(CreateLabel("Convertir a:"));
            cmbTarget = new ComboBox { Margin = new Thickness(0,0,0,10) };
            cmbTarget.ItemsSource = Enum.GetValues(typeof(DWGTarget));
            cmbTarget.SelectedIndex = 0;
            main.Children.Add(cmbTarget);

            main.Children.Add(CreateLabel("Nombre (Vista / Familia):"));
            txtName = new TextBox { Text = "Importacion DWG", Margin = new Thickness(0,0,0,15) };
            main.Children.Add(txtName);

            // 3. Mapping
            GroupBox grpMap = new GroupBox { Header = "Mapeo de Estilos", Foreground = Brushes.White, Margin = new Thickness(0,0,0,15) };
            
            System.Windows.Controls.Grid gridMap = new System.Windows.Controls.Grid { Margin = new Thickness(5) };
            gridMap.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridMap.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.5, GridUnitType.Star) });
            gridMap.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridMap.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridMap.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // Lines
            gridMap.Children.Add(CreateLabel("Estilo de Línea:", 0, 0));
            cmbLines = new ComboBox { Margin = new Thickness(2) };
            PopulateLineStyles();
            gridMap.Children.Add(cmbLines); UiGridSet(cmbLines, 0, 1);

            // Texts
            gridMap.Children.Add(CreateLabel("Tipo de Texto:", 1, 0));
            cmbTexts = new ComboBox { Margin = new Thickness(2) };
            PopulateTextTypes();
            gridMap.Children.Add(cmbTexts); UiGridSet(cmbTexts, 1, 1);

            // Hatch
            gridMap.Children.Add(CreateLabel("Estilo de Relleno:", 2, 0));
            cmbHatch = new ComboBox { Margin = new Thickness(2) };
            PopulateFillTypes();
            gridMap.Children.Add(cmbHatch); UiGridSet(cmbHatch, 2, 1);

            grpMap.Content = gridMap;
            main.Children.Add(grpMap);

            // 4. Options
            chkMask = new CheckBox { Content = "Crear Máscara de Fondo", Foreground = Brushes.White, Margin = new Thickness(0,0,0,10) };
            main.Children.Add(chkMask);

            // Buttons
            Button btnOk = new Button { Content = "IMPORTAR Y CONVERTIR", Height = 40, Margin = new Thickness(0,20,0,0), Background = Brushes.Orange, FontWeight = FontWeights.Bold };
            btnOk.Click += BtnOk_Click;
            main.Children.Add(btnOk);

            this.Content = main;
        }

        private TextBlock CreateHeader(string text)
        {
            return new TextBlock { Text = text, Foreground = Brushes.White, FontSize = 18, FontWeight = FontWeights.Bold, Margin = new Thickness(0,0,0,15), HorizontalAlignment = HorizontalAlignment.Center };
        }

        private TextBlock CreateLabel(string text, int r = -1, int c = -1)
        {
            TextBlock tb = new TextBlock { Text = text, Foreground = Brushes.Gray, Margin = new Thickness(0,0,0,2), VerticalAlignment = VerticalAlignment.Center };
            if (r != -1) UiGridSet(tb, r, c);
            return tb;
        }
        
        private void UiGridSet(UIElement e, int r, int c) 
        { 
            System.Windows.Controls.Grid.SetRow(e, r); 
            System.Windows.Controls.Grid.SetColumn(e, c); 
        }

        // Populators
        private void PopulateLineStyles()
        {
            Category linesCat = _doc.Settings.Categories.get_Item(BuiltInCategory.OST_Lines);
            if(linesCat != null)
            {
               foreach(Category sub in linesCat.SubCategories) cmbLines.Items.Add(sub.Name);
            }
            if(cmbLines.Items.Count > 0) cmbLines.SelectedIndex = 0;
        }

        private void PopulateTextTypes()
        {
            var types = new FilteredElementCollector(_doc).OfClass(typeof(TextNoteType)).ToElements();
            foreach(Element e in types) cmbTexts.Items.Add(e.Name);
            if(cmbTexts.Items.Count > 0) cmbTexts.SelectedIndex = 0;
        }

        private void PopulateFillTypes()
        {
            var types = new FilteredElementCollector(_doc).OfClass(typeof(FilledRegionType)).ToElements();
            foreach(Element e in types) cmbHatch.Items.Add(e.Name);
            if(cmbHatch.Items.Count > 0) cmbHatch.SelectedIndex = 0;
        }

        private void BtnBrowse_Click(object sender, RoutedEventArgs e)
        {
            Microsoft.Win32.OpenFileDialog dlg = new Microsoft.Win32.OpenFileDialog();
            dlg.Filter = "DWG Files|*.dwg";
            if (dlg.ShowDialog() == true)
            {
                txtFile.Text = dlg.FileName;
                Config.FilePath = dlg.FileName;
                if(string.IsNullOrEmpty(txtName.Text) || txtName.Text == "Importacion DWG")
                    txtName.Text = System.IO.Path.GetFileNameWithoutExtension(dlg.FileName);
            }
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(Config.FilePath)) { MessageBox.Show("Selecciona un archivo DWG."); return; }

            Config.TargetType = (DWGTarget)cmbTarget.SelectedItem;
            Config.TargetName = txtName.Text;
            Config.SelectedLineStyle = cmbLines.SelectedItem?.ToString();
            Config.SelectedTextType = cmbTexts.SelectedItem?.ToString();
            Config.SelectedFillRegionType = cmbHatch.SelectedItem?.ToString();
            Config.CreateMaskingRegion = chkMask.IsChecked == true;

            // If Family, ask save location?
            if (Config.TargetType == DWGTarget.DetailItemFamily || 
                Config.TargetType == DWGTarget.GenericAnnotationFamily || 
                Config.TargetType == DWGTarget.GenericModelFamily)
            {
                Microsoft.Win32.SaveFileDialog sfd = new Microsoft.Win32.SaveFileDialog();
                sfd.Filter = "Revit Family|*.rfa";
                sfd.FileName = Config.TargetName;
                if(sfd.ShowDialog() == true)
                {
                    Config.FamilySavePath = sfd.FileName;
                }
                else return; // Cancel
            }

            IsConfirmed = true;
            Close();
        }
    }
}
