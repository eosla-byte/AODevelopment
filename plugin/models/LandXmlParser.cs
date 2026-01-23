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

                    // 1. Parse Points
                    var pnts = new Dictionary<int, XYZPoint>();
                    var def = surf.Element(ns + "Definition");
                    if (def != null)
                    {
                        var pntsNode = def.Element(ns + "Pnts");
                        if (pntsNode != null)
                        {
                            foreach (var p in pntsNode.Elements(ns + "P"))
                            {
                                int id = int.Parse(p.Attribute("id").Value);
                                var coords = p.Value.Trim().Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                                if (coords.Length >= 3) // Y X Z (LandXML usually Northing Easting Elev) or N E Z
                                {
                                    // LandXML: Y=Northing, X=Easting. Revit: X=Easting, Y=Northing.
                                    // So Revit X = LandXML Easting (X? check spec usually Y X Z or distinct)
                                    // Standard LandXML: "Y X Z" order for <P> content is common? No, actually space delimited: "North East Elev" -> Y X Z
                                    // Let's assume standard Y X Z based on typical C3D export
                                    
                                    double val1 = double.Parse(coords[0]); // Y (North)
                                    double val2 = double.Parse(coords[1]); // X (East)
                                    double val3 = double.Parse(coords[2]); // Z
                                    
                                    // Map to Revit: X=East, Y=North
                                    pnts[id] = new XYZPoint { X = val2, Y = val1, Z = val3 };
                                }
                            }
                        }
                        
                        // 2. Parse Faces
                        var facesNode = def.Element(ns + "Faces");
                        if (facesNode != null)
                        {
                            foreach (var f in facesNode.Elements(ns + "F"))
                            {
                                var ids = f.Value.Trim().Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                                if (ids.Length == 3)
                                {
                                    var facePoints = new List<XYZPoint>();
                                    foreach(var iStr in ids)
                                    {
                                        int pid = int.Parse(iStr);
                                        if(pnts.ContainsKey(pid)) facePoints.Add(pnts[pid]);
                                    }
                                    if(facePoints.Count == 3) civilSurf.Faces.Add(facePoints);
                                }
                            }
                        }
                    }
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
                    
                    var coordGeom = align.Element(ns + "CoordGeom");
                    if (coordGeom != null)
                    {
                         // Parse Lines and Curves to get points
                         // Simplified: Just grabbing start/end points of geometry for visualization
                         foreach(var elem in coordGeom.Elements())
                         {
                             // Line, Curve, Spiral
                             // Each has Start and End (or PI)
                             // This is complex, implementing simplified "Start" points sequence
                             // Usually <Start> Y X </Start> <End> Y X </End>
                             
                             // Try to find <Start> element
                             // Note: Namespace applies
                             var start = elem.Element(ns + "Start");
                             if (start != null)
                             {
                                 var coords = start.Value.Trim().Split(new[]{' '}, StringSplitOptions.RemoveEmptyEntries);
                                 if (coords.Length >= 2)
                                 {
                                     double n = double.Parse(coords[0]);
                                     double e = double.Parse(coords[1]);
                                     civilAlign.Points.Add(new XYZPoint { X = e, Y = n, Z = 0 }); 
                                 }
                             }
                             // Also End
                             var end = elem.Element(ns + "End");
                             if (end != null)
                             {
                                 var coords = end.Value.Trim().Split(new[]{' '}, StringSplitOptions.RemoveEmptyEntries);
                                 if (coords.Length >= 2)
                                 {
                                     double n = double.Parse(coords[0]);
                                     double e = double.Parse(coords[1]);
                                     civilAlign.Points.Add(new XYZPoint { X = e, Y = n, Z = 0 }); 
                                 }
                             }
                         }
                    }
                    data.Alignments.Add(civilAlign);
                }

            return data;
        }
    }
}
