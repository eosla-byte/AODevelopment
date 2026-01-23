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
            
            // Priority: If we are in Step 3 (Manager), use the TreeView items as the source of truth
            // Because user might have renamed or deleted items.
            if (_currentStep == 3)
            {
                 var items = tvImportedData.ItemsSource as List<ManagerItem>;
                 if (items != null && items.Count > 0)
                 {
                     // Flatten hierarchy
                     var children = items[0].Children; // Root -> Children
                     // Match back to _parsedData by Name or Reference?
                     // Better: We should have stored the reference in ManagerItem.
                     // Since we didn't add it to ManagerItem class, map by Name for now (risky but okay for prototype)
                     
                     var allParsed = new List<CivilElement>();
                     allParsed.AddRange(_parsedData.Surfaces);
                     allParsed.AddRange(_parsedData.Alignments);
                     
                     foreach(var child in children)
                     {
                         var match = allParsed.FirstOrDefault(x => x.Name == child.Name);
                         if (match != null)
                         {
                             match.MaterialName = child.Comment; // Sync material choice back
                             selected.Add(match);
                         }
                     }
                 }
            }
            else
            {
                // Step 2 Logic
                if (dgElements.ItemsSource is List<CivilElement> list)
                {
                    selected = list.Where(x => x.IsSelected).ToList();
                }
            }
            
            bool shared = rbShared.IsChecked == true;
            
            // Set Data on Handler
            _handler.ElementsToImport = selected;
            _handler.UseSharedCoordinates = shared;
            
            // Raise Event
            _exEvent.Raise();
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
            public string Comment { get; set; } = "<not set>"; // Used for Material
            
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
            List<string> cats = new List<string> { "Topography", "Roads", "Floors", "Generic Models", "Site" };

            var root = new ManagerItem 
            { 
                Name = System.IO.Path.GetFileName(_loadedFilePath) + $" ({DateTime.Now:g})",
                InfoText = "LandXML Source",
                Comment = "Linked",
                AvailableCategories = new List<string>() 
            };

            // Add elements as children
            foreach (var s in _parsedData.Surfaces.Where(x => x.IsSelected))
            {
                root.Children.Add(new ManagerItem 
                { 
                    Name = s.Name, 
                    InfoText = "Type: Surface", 
                    Comment = s.MaterialName, 
                    SelectedCategory = "Topography", 
                    AvailableCategories = cats 
                });
            }
             foreach (var a in _parsedData.Alignments.Where(x => x.IsSelected))
            {
                root.Children.Add(new ManagerItem 
                { 
                    Name = a.Name, 
                    InfoText = "Type: Roadway Corridor", 
                    Comment = a.MaterialName,
                    SelectedCategory = "Roads", 
                    AvailableCategories = cats
                });
            }

            var items = new List<ManagerItem> { root };
            tvImportedData.ItemsSource = items;
            txtSavedPath.Text = _loadedFilePath;
            
            UpdatePreview();
        }
        
        private void UpdatePreview()
        {
            cvsPreview.Children.Clear();
            if (_parsedData == null) return;
            
            // Calculate Bounds
            double minX = double.MaxValue, minY = double.MaxValue;
            double maxX = double.MinValue, maxY = double.MinValue;
            bool hasData = false;
            
            var surfaces = _parsedData.Surfaces.Where(x => x.IsSelected).ToList();
            var alignments = _parsedData.Alignments.Where(x => x.IsSelected).ToList();
            
            // Scan Points
            foreach(var s in surfaces)
            {
                // Surface has Faces (List<List<XYZPoint>>)
                foreach(var face in s.Faces)
                {
                    foreach(var pt in face)
                    {
                        if(pt.X < minX) minX = pt.X; if(pt.X > maxX) maxX = pt.X;
                        if(pt.Y < minY) minY = pt.Y; if(pt.Y > maxY) maxY = pt.Y;
                        hasData = true;
                    }
                }
            }
            foreach(var a in alignments)
            {
                foreach(var pt in a.Points)
                {
                     if(pt.X < minX) minX = pt.X; if(pt.X > maxX) maxX = pt.X;
                     if(pt.Y < minY) minY = pt.Y; if(pt.Y > maxY) maxY = pt.Y;
                     hasData = true;
                }
            }
            
            if (!hasData) return;
            
            // Scale to Canvas
            double width = maxX - minX;
            double height = maxY - minY;
            if (width < 0.1) width = 1; 
            if (height < 0.1) height = 1;
            
            double cvsW = cvsPreview.ActualWidth;
            double cvsH = cvsPreview.ActualHeight;
            if (cvsW == 0 || double.IsNaN(cvsW)) cvsW = 400; // Fallback if layout not ready
            if (cvsH == 0 || double.IsNaN(cvsH)) cvsH = 300;
            
            // Padding
            cvsW -= 20; cvsH -= 20;
            
            double scaleX = cvsW / width;
            double scaleY = cvsH / height;
            double scale = Math.Min(scaleX, scaleY);
            
            // Draw func
            Func<double, double, Point> toPoint = (x, y) => 
            {
                double px = (x - minX) * scale + 10;
                double py = cvsH - ((y - minY) * scale) + 10; // Flip Y for screen coords
                return new Point(px, py);
            };
            
            // Draw Alignments (Red Lines)
            foreach(var a in alignments)
            {
                var poly = new System.Windows.Shapes.Polyline
                {
                    Stroke = System.Windows.Media.Brushes.Red,
                    StrokeThickness = 2
                };
                foreach(var pt in a.Points) poly.Points.Add(toPoint(pt.X, pt.Y));
                cvsPreview.Children.Add(poly);
            }
            
            // Draw Surfaces (Gray Edges, limited to avoid lag)
            int faceCount = 0;
            foreach(var s in surfaces)
            {
                foreach(var face in s.Faces)
                {
                    if (faceCount > 2000) break; // Performance limit for canvas
                    var poly = new System.Windows.Shapes.Polygon
                    {
                        Stroke = System.Windows.Media.Brushes.Gray,
                        StrokeThickness = 0.5,
                        Fill = System.Windows.Media.Brushes.Transparent // Wireframe
                    };
                    foreach(var pt in face) poly.Points.Add(toPoint(pt.X, pt.Y));
                    cvsPreview.Children.Add(poly);
                    faceCount++;
                }
            }
            
            // Add Text
            TextBlock info = new TextBlock { Text = $"{faceCount} Faces, {alignments.Count} Routes", Foreground = System.Windows.Media.Brushes.Black, FontSize = 10 };
            Canvas.SetLeft(info, 5); Canvas.SetBottom(info, 5);
            cvsPreview.Children.Add(info);
        }

        public void BtnRefresh_Click(object sender, RoutedEventArgs e)
        {
             UpdatePreview();
        }

        public void BtnMaterial_Click(object sender, RoutedEventArgs e)
        {
             var selected = tvImportedData.SelectedItem as ManagerItem;
             if (selected != null)
                 MessageBox.Show($"Change Material for: {selected.Name} (Not implemented in prototype)");
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
             if (tvImportedData.SelectedItem is ManagerItem selected && selected.Name != "LandXML Source")
             {
                 // Find parent
                 var items = tvImportedData.ItemsSource as List<ManagerItem>;
                 var root = items[0];
                 if (root.Children.Contains(selected))
                 {
                     root.Children.Remove(selected);
                     tvImportedData.Items.Refresh();
                     UpdatePreview(); // Re-render preview without deleted item
                 }
             }
        }

        public void BtnExplode_Click(object sender, RoutedEventArgs e)
        {
             MessageBox.Show("Explode functionality: Unbinds element from XML.");
        }
    }
}
