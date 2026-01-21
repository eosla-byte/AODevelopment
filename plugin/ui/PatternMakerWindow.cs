using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls; 
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using RevitCivilConnector.models;

using Point = System.Windows.Point;
using Canvas = System.Windows.Controls.Canvas;
using Rectangle = System.Windows.Shapes.Rectangle;

namespace RevitCivilConnector.ui
{
    public class PatternMakerWindow : Window
    {
        public PatternConfig Config { get; private set; }
        public bool IsConfirmed { get; private set; } = false;

        private Canvas _drawCanvas;
        private Point? _startPoint = null;
        private List<Line> _visualLines = new List<Line>();
        
        private TextBox txtName;
        private CheckBox chkModel;
        private TextBox txtTileW;
        private TextBox txtTileH;
        private CheckBox chkSnap;

        private double _canvasScale = 200.0; // Px per Unit

        public PatternMakerWindow()
        {
            Config = new PatternConfig();
            InitializeUI();
        }

        private void InitializeUI()
        {
            this.Title = "Pattern Maker - Trace & Create";
            this.Width = 900;
            this.Height = 700;
            this.WindowStartupLocation = WindowStartupLocation.CenterScreen;
            this.Background = new SolidColorBrush(Color.FromRgb(30, 30, 30));

            Grid mainGrid = new Grid();
            mainGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(250) }); // Sidebar
            mainGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); // Canvas

            // --- Sidebar ---
            StackPanel side = new StackPanel { Margin = new Thickness(10) };
            
            TextBlock title = new TextBlock { Text = "PATTERN MAKER", Foreground = Brushes.White, FontWeight = FontWeights.Bold, FontSize=18, Margin = new Thickness(0,0,0,20) };
            side.Children.Add(title);

            // Settings
            side.Children.Add(Label("Pattern Name:"));
            txtName = new TextBox { Text = "NewPattern", Margin = new Thickness(0,0,0,10) };
            side.Children.Add(txtName);

            chkModel = new CheckBox { Content = "Model Pattern", IsChecked = true, Foreground = Brushes.White, Margin = new Thickness(0,0,0,10) };
            side.Children.Add(chkModel);

            side.Children.Add(Label("Tile Size (m):"));
            Grid sizeGrid = new Grid();
            sizeGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            sizeGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            txtTileW = new TextBox { Text = "1.0", Margin = new Thickness(2) };
            txtTileW.TextChanged += (s,e) => UpdateCanvasGrid();
            txtTileH = new TextBox { Text = "1.0", Margin = new Thickness(2) };
            txtTileH.TextChanged += (s,e) => UpdateCanvasGrid();
            
            sizeGrid.Children.Add(txtTileW); Grid.SetColumn(txtTileW, 0);
            sizeGrid.Children.Add(txtTileH); Grid.SetColumn(txtTileH, 1);
            side.Children.Add(sizeGrid);

            // Snap
            chkSnap = new CheckBox { Content = "Snap to Grid (0.1m)", IsChecked = true, Foreground = Brushes.White, Margin = new Thickness(0,10,0,10) };
            side.Children.Add(chkSnap);

            // Image Loader
            Button btnLoadImg = new Button { Content = "Load Reference Image...", Height = 30, Margin = new Thickness(0,20,0,10) };
            btnLoadImg.Click += BtnLoadImg_Click;
            side.Children.Add(btnLoadImg);
            
            // Actions
            Button btnClear = new Button { Content = "Clear Lines", Height = 30, Margin = new Thickness(0,5,0,5), Background = Brushes.IndianRed };
            btnClear.Click += (s,e) => ClearLines();
            side.Children.Add(btnClear);

            Button btnCreate = new Button { Content = "CREATE PATTERN", Height = 40, Margin = new Thickness(0,20,0,0), FontWeight = FontWeights.Bold, Background = Brushes.DodgerBlue, Foreground = Brushes.White };
            btnCreate.Click += BtnCreate_Click;
            side.Children.Add(btnCreate);

            mainGrid.Children.Add(side);

            // --- Canvas Area ---
            Border canvasBorder = new Border { BorderBrush = Brushes.Gray, BorderThickness = new Thickness(1), Margin = new Thickness(10), Background = Brushes.Black, ClipToBounds = true };
            
            _drawCanvas = new Canvas();
            _drawCanvas.Background = Brushes.Transparent;
            _drawCanvas.MouseDown += Canvas_MouseDown;
            _drawCanvas.MouseMove += Canvas_MouseMove;
            _drawCanvas.MouseUp += Canvas_MouseUp; // Finish line logic? Usually Click-Click is better.

            canvasBorder.Child = _drawCanvas;
            
            Grid.SetColumn(canvasBorder, 1);
            mainGrid.Children.Add(canvasBorder);

            // Draw Initial Grid
            UpdateCanvasGrid();

            this.Content = mainGrid;
        }

        private TextBlock Label(string t) => new TextBlock { Text = t, Foreground = Brushes.LightGray };

        // Grid Visualization
        private void UpdateCanvasGrid()
        {
            // Clear Grid lines only (Keep user lines?)
            // For simplicitly, rebuild all background.
            // But we need to keep _visualLines separate.
            // We use ZIndex. Background = 0. Lines = 10.
            
            // Just Draw a Rectangle representing the Tile
            // Remove old Rects
            for(int i=_drawCanvas.Children.Count-1; i>=0; i--)
            {
                if (_drawCanvas.Children[i] is Rectangle) _drawCanvas.Children.RemoveAt(i);
            }

            if (double.TryParse(txtTileW.Text, out double w) && double.TryParse(txtTileH.Text, out double h))
            {
                double pxW = w * _canvasScale;
                double pxH = h * _canvasScale;

                // Draw Tile Bounds
                Rectangle r = new Rectangle 
                { 
                    Width = pxW, 
                    Height = pxH, 
                    Stroke = Brushes.Yellow, 
                    StrokeThickness = 2, 
                    StrokeDashArray = new DoubleCollection { 4, 2 } 
                };
                Canvas.SetLeft(r, 50); // Offset origin
                Canvas.SetTop(r, 50);
                _drawCanvas.Children.Add(r);
                Panel.SetZIndex(r, 1);
                
                // Draw 3x3 repetition preview (faint)?
                // Maybe later.
            }
        }

        private void BtnLoadImg_Click(object sender, RoutedEventArgs e)
        {
            Microsoft.Win32.OpenFileDialog dlg = new Microsoft.Win32.OpenFileDialog();
            dlg.Filter = "Images|*.jpg;*.png;*.bmp";
            if (dlg.ShowDialog() == true)
            {
                ImageBrush brush = new ImageBrush();
                brush.ImageSource = new BitmapImage(new Uri(dlg.FileName));
                brush.Opacity = 0.5;
                brush.Stretch = Stretch.Uniform; // Or matching tile?
                // Ideally User wants to trace.
                // We set canvas background?
                _drawCanvas.Background = brush;
            }
        }

        // --- Drawing Logic ---
        
        // Mode: Click-Drag or Click-Click?
        // Let's do Click-Drag for speed.
        
        private Line _currentLine;

        private void Canvas_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (e.LeftButton == MouseButtonState.Pressed)
            {
                Point p = e.GetPosition(_drawCanvas);
                p = Snap(p);
                _startPoint = p;
                
                _currentLine = new Line 
                { 
                    Stroke = Brushes.Cyan, 
                    StrokeThickness = 2, 
                    X1 = p.X, Y1 = p.Y, X2 = p.X, Y2 = p.Y 
                };
                _drawCanvas.Children.Add(_currentLine);
                Panel.SetZIndex(_currentLine, 10);
            }
        }

        private void Canvas_MouseMove(object sender, MouseEventArgs e)
        {
            if (_startPoint.HasValue && _currentLine != null)
            {
                Point p = e.GetPosition(_drawCanvas);
                // Snap preview?
                p = Snap(p, false); // Don't hard snap on move for smoothness? Or yes?
                // Let's snap if checked
                if(chkSnap.IsChecked == true) p = Snap(p);

                _currentLine.X2 = p.X;
                _currentLine.Y2 = p.Y;
            }
        }

        private void Canvas_MouseUp(object sender, MouseButtonEventArgs e)
        {
            if (_startPoint.HasValue && _currentLine != null)
            {
                 // Finalize
                 Point p = e.GetPosition(_drawCanvas);
                 p = Snap(p);
                 _currentLine.X2 = p.X;
                 _currentLine.Y2 = p.Y;
                 
                 // If len > 0
                 if (Math.Abs(p.X - _startPoint.Value.X) > 1 || Math.Abs(p.Y - _startPoint.Value.Y) > 1)
                 {
                     _visualLines.Add(_currentLine);
                 }
                 else
                 {
                     _drawCanvas.Children.Remove(_currentLine); // Too short
                 }

                 _startPoint = null;
                 _currentLine = null;
            }
        }

        private Point Snap(Point p, bool heavy = true)
        {
            if (chkSnap.IsChecked != true) return p;
            
            // Snap to 0.1m (20px)
            double snapUnit = 0.1 * _canvasScale; 
            double x = Math.Round((p.X - 50) / snapUnit) * snapUnit + 50;
            double y = Math.Round((p.Y - 50) / snapUnit) * snapUnit + 50;
            return new Point(x, y);
        }

        private void ClearLines()
        {
            foreach(var l in _visualLines) _drawCanvas.Children.Remove(l);
            _visualLines.Clear();
        }

        private void BtnCreate_Click(object sender, RoutedEventArgs e)
        {
            // Convert Visual Lines to Config Lines (Units)
            Config.Name = txtName.Text;
            Config.IsModelPattern = chkModel.IsChecked == true;
            if (double.TryParse(txtTileW.Text, out double w)) Config.TileWidth = w;
            if (double.TryParse(txtTileH.Text, out double h)) Config.TileHeight = h;

            foreach(var line in _visualLines)
            {
                // Unmap from Canvas coords (Origin 50,50, Scale _canvasScale)
                double x1 = (line.X1 - 50) / _canvasScale;
                double y1 = -(line.Y1 - 50) / _canvasScale; // Invert Y (Revit Y up, Canvas Y down)
                // Wait, if I invert Y, I must ensure Origin is consistent.
                // Let's assume Top-Left (Canvas 50,50) is (0, MaxY)? 
                // Creating a pattern: Origin (0,0) usually Bottom-Left.
                // Let's Map Canvas (50, 50 + H_px) to (0,0).
                
                double pxH = Config.TileHeight * _canvasScale;
                double originYPx = 50 + pxH;
                
                // P = (X - 50, originYPx - Y) / Scale
                
                double lx1 = (line.X1 - 50) / _canvasScale;
                double ly1 = (originYPx - line.Y1) / _canvasScale;
                double lx2 = (line.X2 - 50) / _canvasScale;
                double ly2 = (originYPx - line.Y2) / _canvasScale;
                
                Config.Lines.Add(new PatternLine 
                { 
                    Start = new Point(lx1, ly1), 
                    End = new Point(lx2, ly2) 
                });
            }

            IsConfirmed = true;
            Close();
        }
    }
}
