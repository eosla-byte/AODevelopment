using System;
using System.Collections.Generic;
using System.Linq;
using System.Xml.Linq;
using System.IO;

namespace RevitCivilConnector.Models
{
    public class LandXmlData
    {
        public List<CivilSurface> Surfaces { get; set; } = new List<CivilSurface>();
        public List<CivilAlignment> Alignments { get; set; } = new List<CivilAlignment>();
    }

    public class CivilElement
    {
        public string Name { get; set; }
        public string Type { get; set; }
        public bool IsSelected { get; set; } = true;
        public string MaterialName { get; set; } = "<By Category>";
        // Helper specifically for UI binding
        public List<string> AvailableMaterials { get; set; } = new List<string>();
    }

    public class CivilSurface : CivilElement
    {
        public List<List<XYZPoint>> Faces { get; set; } = new List<List<XYZPoint>>();
    }

    public class CivilAlignment : CivilElement
    {
        public List<XYZPoint> Points { get; set; } = new List<XYZPoint>();
    }

    public class XYZPoint
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
    }

    public static class LandXmlParser
    {
        public static LandXmlData Parse(string filePath)
        {
            var data = new LandXmlData();
            
            if (!File.Exists(filePath)) return data;

            try
            {
                XDocument doc = XDocument.Load(filePath);
                XNamespace ns = doc.Root.Name.Namespace;

                // Parse Surfaces
                foreach (var surf in doc.Descendants(ns + "Surface"))
                {
                    var civilSurf = new CivilSurface
                    {
                        Name = surf.Attribute("name")?.Value ?? "Unnamed Surface",
                        Type = "Surface"
                    };

                    // Simple Parsing logic for Faces (3D faces)
                    // Note: Real implementation needs to parse Pnts and Faces definition
                    // This is a placeholder structure for the parser logic
                    data.Surfaces.Add(civilSurf);
                }

                // Parse Alignments
                foreach (var align in doc.Descendants(ns + "Alignment"))
                {
                    var civilAlign = new CivilAlignment
                    {
                        Name = align.Attribute("name")?.Value ?? "Unnamed Alignment",
                        Type = "Alignment"
                    };
                    data.Alignments.Add(civilAlign);
                }
            }
            catch (Exception ex)
            {
                // Log error
                Console.WriteLine("Error parsing LandXML: " + ex.Message);
            }

            return data;
        }
    }
}
