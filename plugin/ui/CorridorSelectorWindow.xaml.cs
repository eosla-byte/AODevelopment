using System;
using System.Collections.Generic;
using System.Windows;
using Autodesk.Revit.DB;
using RevitCivilConnector.Models;

namespace RevitCivilConnector.UI
{
    public partial class CorridorSelectorWindow : Window
    {
        public List<CivilCorridor> Corridors { get; set; }
        public List<Material> AvailableMaterials { get; set; }
        
        // Diccionario simple para mapear nombres de categorías a BuiltInCategory
        public Dictionary<string, BuiltInCategory> CategoryOptions { get; set; }

        public CorridorSelectorWindow(List<CivilCorridor> corridors, List<Material> materials)
        {
            InitializeComponent();
            Corridors = corridors;
            AvailableMaterials = materials;
            
            // Inicializar opciones de categoría
            CategoryOptions = new Dictionary<string, BuiltInCategory>
            {
                { "Generic Models", BuiltInCategory.OST_GenericModel },
                { "Floors", BuiltInCategory.OST_Floors },
                { "Site", BuiltInCategory.OST_Site },
                { "Roads", BuiltInCategory.OST_Roads }, // Si está disponible
                { "Structural Framing", BuiltInCategory.OST_StructuralFraming }
            };

            // DataContext para Binding
            this.DataContext = this;
        }

        private void BtnImport_Click(object sender, RoutedEventArgs e)
        {
            this.DialogResult = true;
            this.Close();
        }

        private void BtnCancel_Click(object sender, RoutedEventArgs e)
        {
            this.DialogResult = false;
            this.Close();
        }
    }
}
