using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.ui
{
    public class SheetManagerTwoWindow : Window
    {
        public bool IsConfirmed { get; private set; } = false;
        public string CsvPath { get; private set; }
        public ElementId SelectedTitleBlockId { get; private set; }
        public bool IgnoreHeaders { get; private set; } = true;

        private List<FamilySymbol> _titleBlocks;
        private TextBox _txtPath;
        private ComboBox _cmbInfo;
        private CheckBox _chkHeader;

        public SheetManagerTwoWindow(List<FamilySymbol> titleBlocks)
        {
            _titleBlocks = titleBlocks;
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Sheet Manager 2.0 - AO Labs";
            this.Width = 450;
            this.Height = 350;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.ResizeMode = ResizeMode.NoResize;
            this.Background = new SolidColorBrush(Colors.WhiteSmoke);

            StackPanel mainStack = new StackPanel { Margin = new Thickness(15) };

            // 1. TitleBlock Selection
            Label lblTB = new Label { Content = "Seleccione Cajetín (TitleBlock) para nuevas Sheets:", FontWeight = FontWeights.Bold };
            mainStack.Children.Add(lblTB);

            _cmbInfo = new ComboBox { Margin = new Thickness(0, 0, 0, 10), DisplayMemberPath = "Name" };
            foreach (var tb in _titleBlocks.OrderBy(x => x.Name))
            {
                _cmbInfo.Items.Add(tb);
            }
            if (_cmbInfo.Items.Count > 0) _cmbInfo.SelectedIndex = 0;
            mainStack.Children.Add(_cmbInfo);

            // 2. CSV File Selection
            Label lblFile = new Label { Content = "Seleccione archivo CSV/Excel (.csv):", FontWeight = FontWeights.Bold };
            mainStack.Children.Add(lblFile);

            Grid fileGrid = new Grid();
            fileGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            fileGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            _txtPath = new TextBox { IsReadOnly = true, Margin = new Thickness(0, 0, 5, 0), VerticalContentAlignment = VerticalAlignment.Center, Height = 25 };
            Grid.SetColumn(_txtPath, 0);
            fileGrid.Children.Add(_txtPath);

            Button btnBrowse = new Button { Content = "...", Width = 30, Height = 25 };
            btnBrowse.Click += BtnBrowse_Click;
            Grid.SetColumn(btnBrowse, 1);
            fileGrid.Children.Add(btnBrowse);

            mainStack.Children.Add(fileGrid);

            // 3. Info / Instructions
            TextBlock txtInfo = new TextBlock 
            { 
                Text = "Formato CSV Requerido:\n\nColumna 1: Numero de Sheet (Obligatorio)\nColumna 2: Nombre de Sheet (Opcional)\nColumnas 3+: Nombres de Parámetros (El encabezado debe coincidir con el nombre exacto del parámetro en Revit).", 
                TextWrapping = TextWrapping.Wrap, 
                Margin = new Thickness(0, 15, 0, 0),
                Foreground = new SolidColorBrush(Colors.DimGray),
                FontSize = 11
            };
            mainStack.Children.Add(txtInfo);

            // 4. Options
            _chkHeader = new CheckBox { Content = "La primera fila son encabezados", IsChecked = true, Margin = new Thickness(0, 15, 0, 0) };
            mainStack.Children.Add(_chkHeader);

            // 5. Buttons
            StackPanel btnStack = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 20, 0, 0) };
            
            Button btnOk = new Button { Content = "PROCESAR", Width = 100, Height = 30, Margin = new Thickness(5), Background = new SolidColorBrush(Colors.LightSkyBlue), FontWeight = FontWeights.Bold };
            btnOk.Click += BtnOk_Click;
            
            Button btnCancel = new Button { Content = "Cancelar", Width = 80, Height = 30, Margin = new Thickness(5) };
            btnCancel.Click += (s, e) => Close();

            btnStack.Children.Add(btnOk);
            btnStack.Children.Add(btnCancel);
            mainStack.Children.Add(btnStack);

            this.Content = mainStack;
        }

        private void BtnBrowse_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog dlg = new OpenFileDialog();
            dlg.Filter = "Archivos CSV (*.csv)|*.csv|Archivos de Texto (*.txt)|*.txt|Todos los archivos (*.*)|*.*";
            if (dlg.ShowDialog() == true)
            {
                _txtPath.Text = dlg.FileName;
            }
        }

        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(_txtPath.Text))
            {
                MessageBox.Show("Por favor seleccione un archivo CSV.", "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (_cmbInfo.SelectedItem == null)
            {
                MessageBox.Show("Por favor seleccione un TitleBlock.", "Error", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            CsvPath = _txtPath.Text;
            SelectedTitleBlockId = (_cmbInfo.SelectedItem as FamilySymbol).Id;
            IgnoreHeaders = _chkHeader.IsChecked == true;
            IsConfirmed = true;
            Close();
        }
    }
}
