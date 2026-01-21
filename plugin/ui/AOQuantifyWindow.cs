
using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Media;
using System.Windows.Controls;
using System.Windows.Data;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitCivilConnector.models;
using RevitCivilConnector.services;
using System.Collections.ObjectModel;

// UI Imports
using TextBox = System.Windows.Controls.TextBox;
using Button = System.Windows.Controls.Button;
using ComboBox = System.Windows.Controls.ComboBox;
using CheckBox = System.Windows.Controls.CheckBox;
using DataGrid = System.Windows.Controls.DataGrid;
using Grid = System.Windows.Controls.Grid;
using Canvas = System.Windows.Controls.Canvas;
using StackPanel = System.Windows.Controls.StackPanel;
using ScrollViewer = System.Windows.Controls.ScrollViewer;
using TextBlock = System.Windows.Controls.TextBlock;
using TreeView = System.Windows.Controls.TreeView;
using TreeViewItem = System.Windows.Controls.TreeViewItem;
using Brushes = System.Windows.Media.Brushes;
using Color = System.Windows.Media.Color;
using ColorConverter = System.Windows.Media.ColorConverter;
using Orientation = System.Windows.Controls.Orientation;
using Border = System.Windows.Controls.Border;

namespace RevitCivilConnector.ui
{
    public class AOQuantifyWindow : Window
    {
        public Q2DConfig Config { get; private set; }
        private List<Category> _categories;
        private List<Workset> _worksets;
        
        private List<TakeoffPackage> _packages;
        private TakeoffPackage _activePackage;
        private TakeoffType _activeType;
        
        private ExternalEvent _exEvent;
        private Q2DRequestHandler _handler;
        
        // UI Controls
        private ComboBox _cmbPackage;
        private TextBox _txtVersion;
        private TreeView _typesTree; // Changed to TreeView for grouping
        private DataGrid _inventoryGrid;
        private DataGrid _instanceGrid; // Added
        private TextBlock _lblTotalCost;
        
        // Type Editor Controls
        private Grid _editorPanel;
        private ComboBox _typeName; // Changed to ComboBox
        private TextBox _typeCost;
        private ComboBox _typeUnit;
        private ComboBox _typeClass; // Changed to ComboBox
        private Canvas _colorPreview;
        private StackPanel _colorPalette;
        
        // Stats
        private TextBlock _lblTotalLeft;

        // Local Fields
        private DataGrid _rulesGrid;

        public AOQuantifyWindow(Q2DConfig config, List<Category> cats, List<Workset> worksets, ExternalEvent exEvent, Q2DRequestHandler handler)
        {
            Config = config;
            _categories = cats;
            _worksets = worksets;
            _exEvent = exEvent;
            _handler = handler;
            _handler.SetWindow(this);
            
            InitializeUI();
        }

        public void SetPackages(List<TakeoffPackage> pkgs)
        {
            _packages = pkgs;
            if (!_packages.Any()) _packages.Add(new TakeoffPackage { Name = "Default Package" });
            SetActivePackage(_packages.First());
            // RefreshUI(); // Called by SetActive
            RecalculateInventory(); 
        }

        private void InitializeUI()
        {
            this.Title = "AO Quantify | Hybrid BIM Takeoff";
            this.Width = 1400;
            this.Height = 850;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(Color.FromRgb(245, 247, 250));

            Grid mainGrid = new Grid();
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto, MinHeight = 70 }); // Auto height to avoid clipping
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            
            // --- Toolbar ---
            Grid toolbar = new Grid { Background = Brushes.White, Effect = new System.Windows.Media.Effects.DropShadowEffect { BlurRadius=5, Opacity=0.2 } };
            // Add padding (Top/Bottom) to toolbar itself
            toolbar.Margin = new Thickness(0,0,0,0); 
            toolbar.ShowGridLines = false;
            
            // Configure columns to ensure visibility. 
            // 0: Logo (Auto)
            // 1: Package Selector (Auto)
            // 2: Spacer (*)
            // 3: Buttons (Auto)
            
            toolbar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            toolbar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            toolbar.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            toolbar.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            TextBlock logo = new TextBlock { Text = "AO Quantify", FontSize = 20, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(20,0,20,0), Foreground = new SolidColorBrush(Color.FromRgb(0, 50, 100)) };
            toolbar.Children.Add(logo);

            StackPanel pkgPanel = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(pkgPanel, 1);
            pkgPanel.Children.Add(new TextBlock { Text = "Package: ", VerticalAlignment = VerticalAlignment.Center, Foreground=Brushes.Gray });
            _cmbPackage = new ComboBox { Width = 200, Margin=new Thickness(5,0,10,0) };
            _cmbPackage.DisplayMemberPath = "Name";
            _cmbPackage.SelectionChanged += (s,e) => { if(_cmbPackage.SelectedItem is TakeoffPackage p && p != _activePackage) SetActivePackage(p); };
            pkgPanel.Children.Add(_cmbPackage);
            
            pkgPanel.Children.Add(new TextBlock { Text = "Ver: ", VerticalAlignment = VerticalAlignment.Center, Foreground=Brushes.Gray });
            _txtVersion = new TextBox { Width = 50, Margin=new Thickness(5,0,0,0) };
            pkgPanel.Children.Add(_txtVersion);
            toolbar.Children.Add(pkgPanel);

            StackPanel utils = new StackPanel { Orientation = Orientation.Horizontal, VerticalAlignment = VerticalAlignment.Center, Margin=new Thickness(0,0,20,0) };
            Grid.SetColumn(utils, 3);
            
            Button btnSync = new Button { Content = "☁ Cloud Sync", Padding = new Thickness(15,8,15,8), Background = new SolidColorBrush(Color.FromRgb(0, 120, 215)), Foreground = Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.SemiBold };
            btnSync.Click += SyncCloud_Click;
            utils.Children.Add(btnSync);

            Button btnExport = new Button { Content = "Export CSV", Padding = new Thickness(15,8,15,8), Margin=new Thickness(10,0,0,0), Background = Brushes.White, BorderBrush = Brushes.Gray, BorderThickness = new Thickness(1) };
            btnExport.Click += Export_Click;
            utils.Children.Add(btnExport);

            toolbar.Children.Add(utils);
            mainGrid.Children.Add(toolbar);

            // --- Main Content ---
            Grid contentInfo = new Grid();
            Grid.SetRow(contentInfo, 1);
            contentInfo.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(350) });
            contentInfo.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(5) });
            contentInfo.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

            // -- Left Panel (Hierarchical Types) -- 
            Border leftPanel = new Border { Background = Brushes.White, BorderBrush = Brushes.LightGray, BorderThickness = new Thickness(0,0,1,0) };
            Grid leftLayout = new Grid();
            leftLayout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            leftLayout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            leftLayout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // Header
            StackPanel lHead = new StackPanel { Margin = new Thickness(10) };
            lHead.Children.Add(new TextBlock { Text = "Takeoff Types", FontWeight = FontWeights.Bold, FontSize = 14 });
            TextBox txtSearch = new TextBox { Margin = new Thickness(0,10,0,0), Padding = new Thickness(5), Text = "Search types..." };
            lHead.Children.Add(txtSearch);
            leftLayout.Children.Add(lHead);

            // List (TreeView)
            _typesTree = new TreeView { BorderThickness = new Thickness(0), Background = Brushes.Transparent };
            _typesTree.SelectedItemChanged += TypesTree_SelectedItemChanged;
            Grid.SetRow(_typesTree, 1);
            leftLayout.Children.Add(_typesTree);

            // Add Btn
            Button btnAdd = new Button { Content = "+ Create Type", Height = 40, Margin = new Thickness(10,5,10,0), Background = Brushes.WhiteSmoke, BorderBrush = Brushes.Gray, BorderThickness = new Thickness(1,1,1,1) };
            btnAdd.Click += (s,e) => CreateNewType();
            
            _lblTotalLeft = new TextBlock { Text = "TOTAL PROJECT: $0.00", FontWeight = FontWeights.Bold, Foreground = Brushes.DarkGreen, HorizontalAlignment=HorizontalAlignment.Center, Margin=new Thickness(0,5,0,10) };

            StackPanel bottomP = new StackPanel();
            bottomP.Children.Add(btnAdd);
            bottomP.Children.Add(_lblTotalLeft);

            Grid.SetRow(bottomP, 2);
            leftLayout.Children.Add(bottomP);
            
            leftPanel.Child = leftLayout;
            mainGrid.Children.Add(leftPanel);

            // -- Right Panel --
            Grid rightLayout = new Grid { Margin = new Thickness(10) };
            rightLayout.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            rightLayout.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // Tabs
            TabControl mainTabs = new TabControl();
            
            // Tab 1: Inventory (Global)
            TabItem tabInv = new TabItem { Header = "INVENTORY SUMMARY" };
            Grid invGrid = new Grid();
            invGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            invGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            
            StackPanel invHead = new StackPanel { Orientation = Orientation.Horizontal, Margin=new Thickness(0,0,0,10) };
            Button btnRef = new Button { Content = "🔄 Refresh Inventory", Width = 150, Height = 30 };
            btnRef.Click += (s,e) => RecalculateInventory();
            invHead.Children.Add(btnRef);
            invGrid.Children.Add(invHead);
            
            _inventoryGrid = new DataGrid { AutoGenerateColumns = true, IsReadOnly = true, HeadersVisibility = DataGridHeadersVisibility.Column };
            Grid.SetRow(_inventoryGrid, 1);
            invGrid.Children.Add(_inventoryGrid);
            
            tabInv.Content = invGrid;
            mainTabs.Items.Add(tabInv);

            // Tab 2: Type Details (Active Context)
            TabItem tabDet = new TabItem { Header = "SELECTED TYPE Details" };
            tabDet.Content = CreateEditorPanel();
            mainTabs.Items.Add(tabDet);
            
            rightLayout.Children.Add(mainTabs);

            // Bottom Stats
            _lblTotalCost = new TextBlock { Text = "Total Project Cost: $0.00", FontSize = 18, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(10), Foreground=Brushes.DarkGreen };
            Grid.SetRow(_lblTotalCost, 1);
            rightLayout.Children.Add(_lblTotalCost);

            Grid.SetColumn(rightLayout, 2);
            contentInfo.Children.Add(rightLayout);
            
            mainGrid.Children.Add(contentInfo);
            this.Content = mainGrid;
        }

        private Grid CreateEditorPanel()
        {
            _editorPanel = new Grid { Margin = new Thickness(20), Background = Brushes.White };
            _editorPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(450) }); // Props
            _editorPanel.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); // Instances

            // Props (Left Side of Tab)
            ScrollViewer sv = new ScrollViewer { VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
            StackPanel sp = new StackPanel { Margin = new Thickness(0,0,20,0) };
            sv.Content = sp;
            
            sp.Children.Add(new TextBlock { Text = "Properties", FontWeight=FontWeights.Bold, FontSize=16, Margin=new Thickness(0,0,0,10)});
            
            sp.Children.Add(MakeLabel("Type Name"));
            _typeName = new ComboBox { IsEditable = true, Height = 25 };
            _typeName.AddHandler(System.Windows.Controls.Primitives.TextBoxBase.TextChangedEvent, 
                new System.Windows.Controls.TextChangedEventHandler((s,e) => { 
                    if(_activeType!=null) { _activeType.Name = _typeName.Text; } 
                }));
            _typeName.LostFocus += (s,e) => RefreshUI();
            sp.Children.Add(_typeName);
            
            sp.Children.Add(MakeLabel("Classification (Group)"));
            _typeClass = new ComboBox { IsEditable = true, Height = 25 };
            _typeClass.AddHandler(System.Windows.Controls.Primitives.TextBoxBase.TextChangedEvent, 
                new System.Windows.Controls.TextChangedEventHandler((s,e) => { 
                    if(_activeType!=null) { _activeType.PrimaryClassification = _typeClass.Text; } 
                }));
            _typeClass.LostFocus += (s,e) => RefreshUI(); 
            sp.Children.Add(_typeClass);

            sp.Children.Add(MakeLabel("Unit & Cost"));
            StackPanel uc = new StackPanel { Orientation = Orientation.Horizontal };
            _typeUnit = new ComboBox { Width = 80, Margin=new Thickness(0,0,10,0) };
            _typeUnit.Items.Add("M2"); _typeUnit.Items.Add("M3"); _typeUnit.Items.Add("ML"); _typeUnit.Items.Add("EA");
            _typeUnit.SelectionChanged += (s,e) => { 
                if(_activeType!=null && _typeUnit.SelectedItem!=null) _activeType.Unit = _typeUnit.SelectedItem.ToString(); 
            };
            uc.Children.Add(_typeUnit);
            
            _typeCost = new TextBox { Width = 100 };
            _typeCost.TextChanged += (s,e) => { 
                if(_activeType!=null && double.TryParse(_typeCost.Text, out double c)) _activeType.Cost = c; 
            };
            uc.Children.Add(_typeCost);
            sp.Children.Add(uc);

            sp.Children.Add(MakeLabel("Appearance"));
            StackPanel app = new StackPanel { Orientation = Orientation.Horizontal, Margin=new Thickness(0,0,0,10) };
            _colorPreview = new Canvas { Width = 30, Height = 30, Background = Brushes.Orange, Margin=new Thickness(0,0,10,0) };
            app.Children.Add(_colorPreview);
            
            _colorPalette = new StackPanel { Orientation = Orientation.Horizontal };
            // Populate colors
            string[] colors = new string[] { "#FF0000", "#FFA500", "#FFFF00", "#008000", "#0000FF", "#4B0082", "#EE82EE", "#A52A2A", "#808080", "#000000", "#00FFFF", "#FF00FF", "#F5F5DC", "#008080", "#800000" };
            foreach(var c in colors)
            {
                Button b = new Button { Width=20, Height=20, Margin=new Thickness(2), Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(c)), Tag=c, BorderThickness=new Thickness(0) };
                b.Click += (s,e) => {
                     string hex = (s as Button).Tag.ToString();
                     _colorPreview.Background = (s as Button).Background;
                     if(_activeType!=null) { _activeType.FillColorHex = hex; RefreshListVisuals(); }
                };
                _colorPalette.Children.Add(b);
            }
            app.Children.Add(_colorPalette);
            sp.Children.Add(app);
            
            sp.Children.Add(new TextBlock { Text = "Measurement Tools", FontWeight=FontWeights.Bold, Margin=new Thickness(0,20,0,5) });
            StackPanel tools = new StackPanel { Orientation = Orientation.Horizontal };
            tools.Children.Add(MakeToolBtn("□ Area", TakeoffTool.Area));
            tools.Children.Add(MakeToolBtn("📏 Linear", TakeoffTool.Linear));
            tools.Children.Add(MakeToolBtn("• Count", TakeoffTool.Count));
            tools.Children.Add(MakeToolBtn("📦 3D Select", TakeoffTool.Model)); 
            sp.Children.Add(tools);
            
            Button btnMeasure = new Button { Content = "▶ START MEASURING", Height = 40, Margin = new Thickness(0,20,0,0), Background = new SolidColorBrush(Color.FromRgb(0,120,215)), Foreground=Brushes.White, FontWeight=FontWeights.Bold };
            btnMeasure.Click += BtnMeasure_Click;
            sp.Children.Add(btnMeasure);
            
            _editorPanel.Children.Add(sv);

            // Item Instances List (Right Side of Tab)
            Grid grInst = new Grid { Margin = new Thickness(20,0,0,0) };
            Grid.SetColumn(grInst, 1);
            grInst.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grInst.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            
            grInst.Children.Add(new TextBlock { Text = "Measured Items (Instances)", FontWeight=FontWeights.Bold, Margin=new Thickness(0,0,0,10) });
            
            _instanceGrid = new DataGrid { AutoGenerateColumns = true, IsReadOnly = true };
            Grid.SetRow(_instanceGrid, 1);
            grInst.Children.Add(_instanceGrid);
            
            _editorPanel.Children.Add(grInst);

            return _editorPanel;
        }
        
        // --- Logic ---
        
        private void SetActivePackage(TakeoffPackage pkg)
        {
            _activePackage = pkg;
            _cmbPackage.SelectedItem = pkg;
            RefreshUI();
        }
        
        private void RefreshUI()
        {
            if (_activePackage == null) return;
            
            _typesTree.Items.Clear();
            
            // Group By Classification
            var groups = _activePackage.Types.GroupBy(t => string.IsNullOrEmpty(t.PrimaryClassification) ? "Unassigned" : t.PrimaryClassification);
            
            foreach(var g in groups.OrderBy(x => x.Key))
            {
                TreeViewItem groupItem = new TreeViewItem { Header = g.Key, IsExpanded = true, FontWeight = FontWeights.Bold, Foreground = Brushes.DimGray };
                
                foreach(var t in g)
                {
                    StackPanel sp = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(2) };
                    Canvas c = new Canvas { Width = 12, Height = 12, Margin = new Thickness(0,0,8,0) };
                    try { c.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(t.FillColorHex)); } catch { c.Background = Brushes.Gray; }
                    sp.Children.Add(c);
                    sp.Children.Add(new TextBlock { Text = t.Name, FontWeight = FontWeights.Normal });
                    
                    TreeViewItem typeItem = new TreeViewItem { Header = sp, Tag = t };
                    groupItem.Items.Add(typeItem);
                    
                    // Auto-select if matches active
                    if (t == _activeType) typeItem.IsSelected = true;
                }
                _typesTree.Items.Add(groupItem);
            }
        }
        
        private void UpdateAutoCompleteSources()
        {
            if (_activePackage == null) return;
            var names = _activePackage.Types.Select(t => t.Name).Distinct().OrderBy(n=>n).ToList();
            var classes = _activePackage.Types.Select(t => t.PrimaryClassification).Distinct().OrderBy(c=>c).ToList();
            
            if (_typeName != null) _typeName.ItemsSource = names;
            if (_typeClass != null) _typeClass.ItemsSource = classes;
        }

        private void SelectType(TakeoffType t)
        {
            _activeType = t;
            _typeName.Text = t.Name;
            _typeClass.Text = t.PrimaryClassification;
            _typeCost.Text = t.Cost.ToString();
            _typeUnit.SelectedItem = t.Unit;
            try { 
                var c = (Color)ColorConverter.ConvertFromString(t.FillColorHex);
                _colorPreview.Background = new SolidColorBrush(c);
            } catch {}
            
            UpdateTreeVisuals(); // Just redraw tree
            UpdateInstanceList(t);
            UpdateToolButtons(t.Tool);
        }

        private void TypesTree_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
        {
            if (e.NewValue is TreeViewItem item && item.Tag is TakeoffType t)
            {
                SelectType(t);
            }
        }
        
        private void CreateNewType()
        {
            if (_activePackage == null) return;
            TakeoffType t = new TakeoffType { Name = "New Type", PrimaryClassification="Unassigned" };
            _activePackage.Types.Add(t);
            
            // Add to stats so UpdateTreeVisuals finds it
            _currentStats[t.Id] = new InventoryItem { TypeName = t.Name, Unit = t.Unit, Classification = t.PrimaryClassification, UnitCost = t.Cost, RefType = t, Quantity=0 };
            
            SelectType(t);
        }

        private void BtnMeasure_Click(object sender, RoutedEventArgs e)
        {
            if (_activeType == null) return;
            Config.ActiveTakeoffType = _activeType;
            Config.WantsToMeasure = true; 
            _exEvent.Raise();
        }
        
        private async void SyncCloud_Click(object sender, RoutedEventArgs e)
        {
            var btn = sender as Button;
            btn.Content = "Syncing..."; btn.IsEnabled = false;
            string docTitle = AOQuantifyCommand.ActiveDocument?.Title ?? "Unknown";
            bool res = await services.TakeoffCloudService.UploadPackages(docTitle, _packages);
            MessageBox.Show(res ? "Synced!" : "Failed.");
            btn.Content = "☁ Cloud Sync"; btn.IsEnabled = true;
        }

        private void Export_Click(object sender, RoutedEventArgs e)
        {
            if (_inventoryGrid.Items.Count == 0) RecalculateInventory();
            Microsoft.Win32.SaveFileDialog sfd = new Microsoft.Win32.SaveFileDialog { Filter="CSV|*.csv" };
            if (sfd.ShowDialog() == true)
            {
                MessageBox.Show("Export function to be fully wired to DataGrid items.");
            }
        }
        
        private Dictionary<string, InventoryItem> _currentStats = new Dictionary<string, InventoryItem>();

        public void RecalculateInventory()
        {
             Document doc = AOQuantifyCommand.ActiveDocument;
             if (doc == null || _activePackage == null) return;
             
             // 1. Scan Revit for Tags (This is expensive, only do when needed)
             FilteredElementCollector collector = new FilteredElementCollector(doc);
             IEnumerable<Element> elements = collector.WhereElementIsNotElementType().Where(e => e.Category != null && e.Category.CategoryType == CategoryType.Model);
             
             string TAG_PREFIX = "AO_Q2D_ID:";
             string TAG_PREFIX_OLD = "AO_Q2D:";
             
             // Pre-fetch tagged elements for performance
             var taggedElements = elements.Where(e => {
                 Parameter p = e.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                 string val = p?.AsString();
                 return val != null && (val.StartsWith(TAG_PREFIX) || val.StartsWith(TAG_PREFIX_OLD));
             }).ToList();

             // 2. Initialize Stats Map
             Dictionary<string, InventoryItem> stats = new Dictionary<string, InventoryItem>();
             foreach(var t in _activePackage.Types)
             {
                 stats[t.Id] = new InventoryItem { TypeName = t.Name, Unit = t.Unit, Classification = string.IsNullOrEmpty(t.PrimaryClassification) ? "Unassigned" : t.PrimaryClassification, UnitCost = t.Cost, RefType = t };
             }
             
             // 3. Aggregate Data
             foreach(var el in taggedElements)
             {
                 Parameter p = el.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS);
                 string val = p.AsString();
                 InventoryItem item = null;
                 
                 if (val.StartsWith(TAG_PREFIX))
                 {
                     string id = val.Replace(TAG_PREFIX, "").Trim();
                     if (stats.ContainsKey(id)) item = stats[id];
                 }
                 else if (val.StartsWith(TAG_PREFIX_OLD))
                 {
                     string name = val.Replace(TAG_PREFIX_OLD, "").Trim();
                     var match = stats.Values.FirstOrDefault(i => i.TypeName == name); 
                     if (match != null) item = match;
                 }
                 
                 if (item != null)
                 {
                     double qty = GetQuant(el, item.Unit);
                     item.Quantity += qty;
                     item.InstanceIds.Add(el.Id);
                     item.InstanceDetails.Add(new InstanceDetail { 
                        Id = el.Id.Value.ToString(), 
                        Category = el.Category.Name, 
                        Name = el.Name, 
                        Quantity = qty 
                     });
                 }
             }
             
             _currentStats = stats; // Cache

             // 4. Update Inventory Grid (Center Tab)
             System.Data.DataTable dt = new System.Data.DataTable();
             dt.Columns.Add("Classification");
             dt.Columns.Add("Type");
             dt.Columns.Add("Quantity", typeof(double));
             dt.Columns.Add("Unit");
             dt.Columns.Add("Cost/Unit", typeof(double));
             dt.Columns.Add("Total Cost", typeof(double));
             
             double totalProj = 0;
             foreach(var kvp in stats)
             {
                 var i = kvp.Value;
                 double tc = i.Quantity * i.UnitCost;
                 totalProj += tc;
                 dt.Rows.Add(i.Classification, i.TypeName, Math.Round(i.Quantity, 2), i.Unit, i.UnitCost, Math.Round(tc, 2));
             }
             _inventoryGrid.ItemsSource = dt.DefaultView;
             
             // 5. Update Left Panel Tree (with Subtotals)
             UpdateTreeVisuals();

             // 6. Update Stats Labels
             _lblTotalCost.Text = $"${totalProj:N2}";
             _lblTotalLeft.Text = $"TOTAL PROJECT: ${totalProj:N2}";

             // 7. Update Instance Grid if type selected
             if (_activeType != null) UpdateInstanceList(_activeType);
             
             // 8. Update ComboBox Sources for Auto-complete
             UpdateAutoCompleteSources();
        }

        private void UpdateTreeVisuals()
        {
            Dictionary<string, InventoryItem> stats = _currentStats;
            _typesTree.Items.Clear();
            var groups = _activePackage.Types.GroupBy(t => string.IsNullOrEmpty(t.PrimaryClassification) ? "Unassigned" : t.PrimaryClassification);
            
            foreach(var g in groups.OrderBy(x => x.Key))
            {
                double subtotal = 0;
                foreach(var t in g) { if(stats.ContainsKey(t.Id)) subtotal += (stats[t.Id].Quantity * stats[t.Id].UnitCost); }
                
                DockPanel grpHeader = new DockPanel { Width = 280 };
                TextBlock txtTitle = new TextBlock { Text = g.Key, FontWeight = FontWeights.Bold, Foreground = Brushes.DimGray };
                DockPanel.SetDock(txtTitle, Dock.Left);
                grpHeader.Children.Add(txtTitle);
                TextBlock txtSub = new TextBlock { Text = $"${subtotal:N2}", FontWeight = FontWeights.Bold, Foreground = Brushes.DarkGreen, HorizontalAlignment=HorizontalAlignment.Right };
                DockPanel.SetDock(txtSub, Dock.Right);
                grpHeader.Children.Add(txtSub);
                
                TreeViewItem groupItem = new TreeViewItem { Header = grpHeader, IsExpanded = true };
                
                foreach(var t in g)
                {
                    double q = 0; if(stats.ContainsKey(t.Id)) q = stats[t.Id].Quantity;
                    
                    DockPanel typePanel = new DockPanel { Width = 260 };
                    StackPanel sp = new StackPanel { Orientation = Orientation.Horizontal };
                    DockPanel.SetDock(sp, Dock.Left);
                    Canvas c = new Canvas { Width = 12, Height = 12, Margin = new Thickness(0,0,8,0) };
                    try { c.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(t.FillColorHex)); } catch { c.Background = Brushes.Gray; }
                    sp.Children.Add(c);
                    sp.Children.Add(new TextBlock { Text = t.Name, FontWeight = FontWeights.Normal });
                    typePanel.Children.Add(sp);
                    
                    if (q > 0) 
                    {
                        TextBlock txtQty = new TextBlock { Text = $"{Math.Round(q,1)} {t.Unit}", Foreground=Brushes.Gray, FontSize=10, VerticalAlignment=VerticalAlignment.Center, HorizontalAlignment=HorizontalAlignment.Right };
                        DockPanel.SetDock(txtQty, Dock.Right);
                        typePanel.Children.Add(txtQty);
                    }

                    TreeViewItem typeItem = new TreeViewItem { Header = typePanel, Tag = t };
                    groupItem.Items.Add(typeItem);
                    if (t == _activeType) typeItem.IsSelected = true;
                }
                _typesTree.Items.Add(groupItem);
            }
        }

        
        // Duplicates removed


        private void UpdateInstanceList(TakeoffType t)
        {
            if (_currentStats.ContainsKey(t.Id))
            {
                UpdateInstanceGridUI(_currentStats[t.Id].InstanceDetails);
            }
            else
            {
                UpdateInstanceGridUI(new List<InstanceDetail>());
            }
        }

        private void UpdateInstanceGridUI(List<InstanceDetail> details)
        {
             System.Data.DataTable dt = new System.Data.DataTable();
             dt.Columns.Add("ID");
             dt.Columns.Add("Category");
             dt.Columns.Add("Element Name");
             dt.Columns.Add("Qty", typeof(double));
             
             foreach(var d in details) dt.Rows.Add(d.Id, d.Category, d.Name, Math.Round(d.Quantity, 2));
             _instanceGrid.ItemsSource = dt.DefaultView;
        }

        private double GetQuant(Element el, string unit) 
        { 
             if (unit == "EA") return 1;
             double v = 0;
             if (unit == null) return 0;
             if (unit.Contains("M2")) { Parameter p = el.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED); if(p==null) p=el.LookupParameter("Area"); if(p!=null) v=p.AsDouble()/10.7639; }
             else if (unit.Contains("M3")) { Parameter p = el.get_Parameter(BuiltInParameter.HOST_VOLUME_COMPUTED); if(p==null) p=el.LookupParameter("Volume"); if(p!=null) v=p.AsDouble()/35.3147; }
             else if (unit.Contains("ML")) { Parameter p = el.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH); if(p==null) p=el.LookupParameter("Length"); if(p!=null) v=p.AsDouble()/3.28084; }
             
             if (v == 0) 
             {
                 Parameter p = el.LookupParameter("Volume"); 
                 if(p!=null && unit.Contains("M3")) v=p.AsDouble()/35.3147;
             }
             return v;
        }
        
        // Tool Buttons management
        private List<Button> _toolButtons = new List<Button>();

        private Button MakeToolBtn(string t, TakeoffTool tool) {
            Button b = new Button { Content = t, Margin=new Thickness(0,0,5,0), Padding=new Thickness(10,5,10,5), Background=Brushes.White, Tag = tool, BorderBrush = Brushes.Gray, BorderThickness = new Thickness(1) };
            b.Click += (s,e) => { 
                if(_activeType!=null) {
                     _activeType.Tool = tool; 
                     UpdateToolButtons(tool);
                }
            };
            _toolButtons.Add(b);
            return b;
        }
        
        private void UpdateToolButtons(TakeoffTool activeTool)
        {
            foreach(var btn in _toolButtons)
            {
                if (btn.Tag is TakeoffTool t && t == activeTool)
                {
                    btn.Background = new SolidColorBrush(Color.FromRgb(200, 230, 255)); // Light Blue
                    btn.BorderBrush = new SolidColorBrush(Color.FromRgb(0, 120, 215));
                }
                else
                {
                    btn.Background = Brushes.White;
                    btn.BorderBrush = Brushes.Gray;
                }
            }
        }

        private TextBlock MakeLabel(string t) => new TextBlock { Text = t, Foreground = Brushes.Gray, FontSize = 10, Margin = new Thickness(0,10,0,2) };
        
        private void RefreshListVisuals() { 
             RecalculateInventory();
             if (_activeType != null) UpdateToolButtons(_activeType.Tool);
        }
    
    // Auxiliary classes
    public class InventoryItem 
    {
        public string TypeName; public string Unit; public string Classification; 
        public double UnitCost; public double Quantity; 
        public TakeoffType RefType;
        public List<ElementId> InstanceIds = new List<ElementId>();
        public List<InstanceDetail> InstanceDetails = new List<InstanceDetail>();
    }
    public class InstanceDetail { public string Id; public string Category; public string Name; public double Quantity; }
    }
}
