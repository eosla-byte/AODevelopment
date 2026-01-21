using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32; // For OpenFileDialog
using Autodesk.Revit.DB;
using RevitCivilConnector.models;

using Grid = System.Windows.Controls.Grid;

namespace RevitCivilConnector.ui
{
    public class CoordinatesWindow : Window
    {
        public CoordinatesConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;
        private List<FamilySymbol> _symbols;

        // UI
        private RadioButton rbMove;
        private RadioButton rbCreateSingle;
        private RadioButton rbCreateExcel;
        
        private GroupBox grpParams;
        private TextBox txtX, txtY, txtZ;
        
        private GroupBox grpFamily;
        private ComboBox cmbFamily;
        
        private GroupBox grpExcel;
        private TextBox txtExcelPath;
        private Button btnBrowse;

        public CoordinatesWindow(List<FamilySymbol> symbols)
        {
            Config = new CoordinatesConfig();
            _symbols = symbols;
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Coordenadas Compartidas - Ubicar Elementos";
            this.Width = 500;
            this.Height = 550;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(Colors.WhiteSmoke);

            StackPanel mainStack = new StackPanel { Margin = new Thickness(15) };

            // 1. Mode Selection
            GroupBox grpMode = new GroupBox { Header = "Modo de Operación", FontWeight = FontWeights.Bold, Padding = new Thickness(5) };
            StackPanel stackMode = new StackPanel();
            
            rbMove = new RadioButton { Content = "Mover Elemento Existente (Seleccionar)", IsChecked = true, Margin = new Thickness(2) };
            rbMove.Checked += ModeChanged;
            stackMode.Children.Add(rbMove);

            rbCreateSingle = new RadioButton { Content = "Crear Nuevo Elemento (Manual X,Y,Z)", Margin = new Thickness(2) };
            rbCreateSingle.Checked += ModeChanged;
            stackMode.Children.Add(rbCreateSingle);

            rbCreateExcel = new RadioButton { Content = "Crear Múltiples desde Excel (Lista X,Y,Z)", Margin = new Thickness(2) };
            rbCreateExcel.Checked += ModeChanged;
            stackMode.Children.Add(rbCreateExcel);

            grpMode.Content = stackMode;
            mainStack.Children.Add(grpMode);

            // 2. Family Selection (For Create Modes)
            grpFamily = new GroupBox { Header = "Familia a Insertar", FontWeight = FontWeights.Bold, Margin = new Thickness(0,10,0,0), Padding = new Thickness(5), IsEnabled = false };
            StackPanel stackFam = new StackPanel();
            stackFam.Children.Add(new TextBlock { Text = "Seleccione Familia:", FontWeight = FontWeights.Normal });
            cmbFamily = new ComboBox { Margin = new Thickness(0,5,0,0), DisplayMemberPath = "Name" };
            // Sort Symbols
            _symbols = _symbols.OrderBy(s => s.FamilyName).ThenBy(s => s.Name).ToList();
            foreach(var s in _symbols) cmbFamily.Items.Add(s); // Add obj directly for DisplayMemberPath
            if(cmbFamily.Items.Count > 0) cmbFamily.SelectedIndex = 0;
            stackFam.Children.Add(cmbFamily);
            grpFamily.Content = stackFam;
            mainStack.Children.Add(grpFamily);

            // 3. Manual Coords (For Move & Create Single)
            grpParams = new GroupBox { Header = "Coordenadas (Unidades del Proyecto)", FontWeight = FontWeights.Bold, Margin = new Thickness(0,10,0,0), Padding = new Thickness(5) };
            Grid gridC = new Grid();
            gridC.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(30) });
            gridC.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridC.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridC.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            gridC.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            gridC.Children.Add(CreateLabel("X:", 0, 0));
            txtX = new TextBox { Text = "0.00", Margin = new Thickness(2) };
            Grid.SetRow(txtX, 0); Grid.SetColumn(txtX, 1);
            gridC.Children.Add(txtX);

            gridC.Children.Add(CreateLabel("Y:", 1, 0));
            txtY = new TextBox { Text = "0.00", Margin = new Thickness(2) };
            Grid.SetRow(txtY, 1); Grid.SetColumn(txtY, 1);
            gridC.Children.Add(txtY);

            gridC.Children.Add(CreateLabel("Z:", 2, 0));
            txtZ = new TextBox { Text = "0.00", Margin = new Thickness(2) };
            Grid.SetRow(txtZ, 2); Grid.SetColumn(txtZ, 1);
            gridC.Children.Add(txtZ);

            grpParams.Content = gridC;
            mainStack.Children.Add(grpParams);

            // 4. Excel Selection (For Multi)
            grpExcel = new GroupBox { Header = "Importar Excel", FontWeight = FontWeights.Bold, Margin = new Thickness(0,10,0,0), Padding = new Thickness(5), IsEnabled = false };
            StackPanel stackExcel = new StackPanel();
            stackExcel.Children.Add(new TextBlock { Text = "Formato Requerido: Col A=X, Col B=Y, Col C=Z. (Sin encabezados o primera fila ignorada si es texto).", TextWrapping = TextWrapping.Wrap, Foreground = new SolidColorBrush(Colors.Gray), FontWeight = FontWeights.Normal, FontSize = 10 });
            
            Grid gridEx = new Grid { Margin = new Thickness(0,5,0,0) };
            gridEx.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            gridEx.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            
            txtExcelPath = new TextBox { IsReadOnly = true, Margin = new Thickness(0,0,5,0) };
            gridEx.Children.Add(txtExcelPath);
            
            btnBrowse = new Button { Content = "Buscar...", Width = 70 };
            btnBrowse.Click += BtnBrowse_Click;
            Grid.SetColumn(btnBrowse, 1);
            gridEx.Children.Add(btnBrowse);

            stackExcel.Children.Add(gridEx);
            grpExcel.Content = stackExcel;
            mainStack.Children.Add(grpExcel);


            // Buttons
            StackPanel stackBtns = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 20, 0, 0) };
            Button btnOk = new Button { Content = "EJECUTAR", Width = 120, Height = 35, Margin = new Thickness(5), Background = new SolidColorBrush(Colors.LightSkyBlue), FontWeight = FontWeights.Bold };
            btnOk.Click += BtnOk_Click;
            Button btnCancel = new Button { Content = "Cancelar", Width = 80, Height = 35, Margin = new Thickness(5) };
            btnCancel.Click += (s, e) => Close();

            stackBtns.Children.Add(btnOk);
            stackBtns.Children.Add(btnCancel);
            mainStack.Children.Add(stackBtns);

            this.Content = mainStack;
            
            ModeChanged(null, null); // Init State
        }

        private TextBlock CreateLabel(string text, int row, int col)
        {
            TextBlock tb = new TextBlock { Text = text, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(2), FontWeight = FontWeights.Bold };
            Grid.SetRow(tb, row);
            Grid.SetColumn(tb, col);
            return tb;
        }

        private void ModeChanged(object sender, RoutedEventArgs e)
        {
            if (grpParams == null) return;

            bool isMove = rbMove.IsChecked == true;
            bool isSingle = rbCreateSingle.IsChecked == true;
            bool isExcel = rbCreateExcel.IsChecked == true;

            grpParams.IsEnabled = isMove || isSingle;
            grpFamily.IsEnabled = isSingle || isExcel;
            grpExcel.IsEnabled = isExcel;
        }

        private void BtnBrowse_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog dlg = new OpenFileDialog();
            dlg.Filter = "Excel Files|*.xlsx;*.xls|CSV Files|*.csv";
            if (dlg.ShowDialog() == true)
            {
                txtExcelPath.Text = dlg.FileName;
            }
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
            if (rbMove.IsChecked == true) Config.Mode = CoordinateMode.MoveExisting;
            else if (rbCreateSingle.IsChecked == true) Config.Mode = CoordinateMode.CreateNewSingle;
            else Config.Mode = CoordinateMode.CreateNewMultiFromExcel;

            if (Config.Mode != CoordinateMode.CreateNewMultiFromExcel)
            {
                Config.X = ParseDouble(txtX.Text);
                Config.Y = ParseDouble(txtY.Text);
                Config.Z = ParseDouble(txtZ.Text);
            }
            else
            {
                Config.ExcelPath = txtExcelPath.Text;
                if(string.IsNullOrEmpty(Config.ExcelPath))
                {
                    MessageBox.Show("Debe seleccionar un archivo Excel.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
            }

            if (Config.Mode != CoordinateMode.MoveExisting)
            {
                if (cmbFamily.SelectedItem != null && cmbFamily.SelectedItem is FamilySymbol fs)
                    Config.SelectedFamilySymbolId = fs.Id;
                else
                {
                    MessageBox.Show("Debe seleccionar una familia.", "Error", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
            }

            IsConfirmed = true;
            Close();
        }
    }
}
