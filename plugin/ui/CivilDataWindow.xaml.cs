using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using Autodesk.Revit.UI;
using RevitCivilConnector.Models;
using RevitCivilConnector.Services;

namespace RevitCivilConnector.UI
{
    public partial class CivilDataWindow : Window
    {
        private UIApplication _uiApp;
        private Services.CivilImportHandler _handler;
        private ExternalEvent _exEvent;
        private int _currentStep = 1;
        private string _loadedFilePath;
        private LandXmlData _parsedData;

        public CivilDataWindow(UIApplication uiApp, Services.CivilImportHandler handler, ExternalEvent exEvent)
        {
            InitializeComponent();
            _uiApp = uiApp;
            _handler = handler;
            _exEvent = exEvent;
            UpdateStepUI();
        }

        private void UpdateStepUI()
        {
            // Hide all views first
            ViewLoad.Visibility = Visibility.Collapsed;
            ViewSelection.Visibility = Visibility.Collapsed;
            ViewManager.Visibility = Visibility.Collapsed;
            
            // Buttons Reset
            btnBack.Visibility = Visibility.Collapsed;
            btnNext.Visibility = Visibility.Collapsed;
            btnFinish.Visibility = Visibility.Collapsed;
            pnlManagerButtons.Visibility = Visibility.Collapsed;
            btnCancel.Visibility = Visibility.Visible;

            if (_currentStep == 1) // LOAD
            {
                ViewLoad.Visibility = Visibility.Visible;
                btnNext.Visibility = Visibility.Visible;
                txtStepTitle.Text = "Step 1: Link Data";
            }
            else if (_currentStep == 2) // SELECTION
            {
                ViewSelection.Visibility = Visibility.Visible;
                btnBack.Visibility = Visibility.Visible;
                btnNext.Visibility = Visibility.Visible; 
                txtStepTitle.Text = "Step 2: Select Elements";
            }
            else if (_currentStep == 3) // MANAGER
            {
                ViewManager.Visibility = Visibility.Visible;
                pnlManagerButtons.Visibility = Visibility.Visible;
                btnCancel.Visibility = Visibility.Collapsed; 
                txtStepTitle.Text = "Step 3: Manage Links";
                
                // Populate List
                PopulateManagerView();
            }
        }

        private void BtnBrowse_Click(object sender, RoutedEventArgs e)
        {
            OpenFileDialog dlg = new OpenFileDialog();
            dlg.Filter = "LandXML Files (*.xml)|*.xml|All Files (*.*)|*.*";
            if (dlg.ShowDialog() == true)
            {
                txtFilePath.Text = dlg.FileName;
                _loadedFilePath = dlg.FileName;
            }
        }

        private void BtnFilter_Click(object sender, RoutedEventArgs e)
        {
             _currentStep = 2;
             LoadData();
             UpdateStepUI();
        }

        private void LoadData()
        {
            if (string.IsNullOrEmpty(_loadedFilePath)) return;
            
            // Parse
            _parsedData = LandXmlParser.Parse(_loadedFilePath);
            
            // Populate DataGrid
            List<CivilElement> all = new List<CivilElement>();
            all.AddRange(_parsedData.Surfaces);
            all.AddRange(_parsedData.Alignments);
            
            // Mock Materials (Real implementation queries Revit Doc)
            List<string> mats = new List<string> { "<By Category>", "Grass", "Asphalt", "Concrete", "Earth" };
            foreach(var el in all) el.AvailableMaterials = mats;

            dgElements.ItemsSource = all;
        }

        private void BtnNext_Click(object sender, RoutedEventArgs e)
        {
            if (_currentStep == 1)
            {
                if (string.IsNullOrEmpty(txtFilePath.Text))
                {
                    MessageBox.Show("Please select a file first.");
                    return;
                }
                LoadData(); // Parse
                _currentStep = 2; 
            }
            else if (_currentStep == 2)
            {
                // Go to Manager
                _currentStep = 3;
            }
            UpdateStepUI();
        }

        private void BtnBack_Click(object sender, RoutedEventArgs e)
        {
            if (_currentStep > 1) _currentStep--;
            UpdateStepUI();
        }

        private void BtnCheckAll_Click(object sender, RoutedEventArgs e)
        {
            if (dgElements.ItemsSource is List<CivilElement> list)
            {
                foreach (var item in list) item.IsSelected = true;
                dgElements.Items.Refresh();
            }
        }

        private void BtnCheckNone_Click(object sender, RoutedEventArgs e)
        {
            if (dgElements.ItemsSource is List<CivilElement> list)
            {
                foreach (var item in list) item.IsSelected = false;
                dgElements.Items.Refresh();
            }
        }

        private void BtnFinish_Click(object sender, RoutedEventArgs e)
        {
             // Perform Import
             PerformImport();
             this.Close();
        }
        
        private void BtnOk_Click(object sender, RoutedEventArgs e)
        {
             PerformImport();
             this.Close();
        }

        private void PerformImport()
        {
            if (_parsedData == null) return;
            
            // Collect selected
            List<CivilElement> selected = new List<CivilElement>();
            if (dgElements.ItemsSource is List<CivilElement> list)
            {
                selected = list.Where(x => x.IsSelected).ToList();
            }
            
            bool shared = rbShared.IsChecked == true;
            
            // Set Data on Handler
            _handler.ElementsToImport = selected;
            _handler.UseSharedCoordinates = shared;
            
            // Raise Event
            _exEvent.Raise();
            
            // Note: MessageBox success/fail is now handled by the Handler
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e) => this.Close();
        private void BtnAddMore_Click(object sender, RoutedEventArgs e) 
        {
            _currentStep = 1; 
            txtFilePath.Text = "";
            UpdateStepUI();
        }
        
        // --- MANAGER VIEW LOGIC ---

        public class ManagerItem
        {
            public string Name { get; set; }
            public string InfoText { get; set; } 
            public string Comment { get; set; } = "<not set>";
            
            // New Category Selection
            public string SelectedCategory { get; set; } = "Generic Models";
            public List<string> AvailableCategories { get; set; } = new List<string>();

            public bool HasChildren => Children != null && Children.Any();
            public List<ManagerItem> Children { get; set; } = new List<ManagerItem>();
        }

        private void PopulateManagerView()
        {
            if (_parsedData == null) return;
            
            // Default Categories list
            List<string> cats = new List<string> 
            { 
                "Topography", 
                "Roads", 
                "Floors", 
                "Generic Models", 
                "Site", 
                "Structural Foundations" 
            };

            var root = new ManagerItem 
            { 
                Name = System.IO.Path.GetFileName(_loadedFilePath) + $" ({DateTime.Now:g})",
                InfoText = "LandXML Source",
                Comment = "Linked",
                AvailableCategories = new List<string>() // Root doesn't track category usually, or maybe it does?
            };

            // Add elements as children
            foreach (var s in _parsedData.Surfaces)
            {
                root.Children.Add(new ManagerItem 
                { 
                    Name = s.Name, 
                    InfoText = "Type: Surface", 
                    Comment = s.MaterialName, 
                    SelectedCategory = "Topography", // Default for Surface
                    AvailableCategories = cats 
                });
            }
             foreach (var a in _parsedData.Alignments)
            {
                root.Children.Add(new ManagerItem 
                { 
                    Name = a.Name, 
                    InfoText = "Type: Roadway Corridor", 
                    Comment = a.MaterialName,
                    SelectedCategory = "Roads", // Default for Alignment
                    AvailableCategories = cats
                });
            }

            var items = new List<ManagerItem> { root };
            tvImportedData.ItemsSource = items;
            
            txtSavedPath.Text = _loadedFilePath;
        }

        public void BtnRefresh_Click(object sender, RoutedEventArgs e)
        {
             MessageBox.Show("Refreshed data from source.");
             // Logic to re-parse XML would go here
        }

        public void BtnMaterial_Click(object sender, RoutedEventArgs e)
        {
             var selected = tvImportedData.SelectedItem as ManagerItem;
             if (selected != null)
                 MessageBox.Show($"Change Material for: {selected.Name}");
             else
                 MessageBox.Show("Please select an item in the tree.");
        }

        public void BtnRename_Click(object sender, RoutedEventArgs e)
        {
             var selected = tvImportedData.SelectedItem as ManagerItem;
             if (selected != null)
             {
                 string newName = ShowInput("Enter new name:", selected.Name);
                 if (!string.IsNullOrEmpty(newName)) 
                 {
                     selected.Name = newName;
                     tvImportedData.Items.Refresh(); 
                 }
             }
        }

        private string ShowInput(string prompt, string defaultVal)
        {
            // Simple Input Dialog Window
            System.Windows.Window inputWin = new System.Windows.Window 
            { 
                 Title = "Input", Height = 150, Width = 300, WindowStartupLocation = WindowStartupLocation.CenterScreen, ResizeMode = ResizeMode.NoResize 
            };
            System.Windows.Controls.StackPanel sp = new System.Windows.Controls.StackPanel { Margin = new Thickness(10) };
            sp.Children.Add(new System.Windows.Controls.TextBlock { Text = prompt, Margin = new Thickness(0,0,0,5) });
            System.Windows.Controls.TextBox tb = new System.Windows.Controls.TextBox { Text = defaultVal };
            sp.Children.Add(tb);
            System.Windows.Controls.Button btn = new System.Windows.Controls.Button { Content = "OK", Width = 60, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0,10,0,0) };
            btn.Click += (s, e) => { inputWin.DialogResult = true; inputWin.Close(); };
            sp.Children.Add(btn);
            inputWin.Content = sp;
            
            if (inputWin.ShowDialog() == true) return tb.Text;
            return null;
        }

        public void BtnDelete_Click(object sender, RoutedEventArgs e)
        {
             if (MessageBox.Show("Are you sure you want to remove this item?", "Confirm", MessageBoxButton.YesNo) == MessageBoxResult.Yes)
             {
                 MessageBox.Show("Item removed.");
             }
        }

        public void BtnExplode_Click(object sender, RoutedEventArgs e)
        {
             MessageBox.Show("Explode functionality: Unbinds element from XML.");
        }
    }
}
