using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.Models
{
    // Clase para representar un Corridor de Civil 3D
    public class CivilCorridor
    {
        public string Name { get; set; }
        public string Handle { get; set; }
        public List<CorridorCode> Codes { get; set; } = new List<CorridorCode>();
        public bool IsSelected { get; set; }
    }

    // Clase para representar un código de material (ej. "Pavimento1", "Base")
    public class CorridorCode
    {
        public string CodeName { get; set; } // Nombre del código en Civil 3D
        public BuiltInCategory RevitCategory { get; set; } = BuiltInCategory.OST_GenericModel; // Categoría por defecto
        public Material RevitMaterial { get; set; } // Material seleccionado en Revit
        public bool IsSelected { get; set; } = true;
    }
}
