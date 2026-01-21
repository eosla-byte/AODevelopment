using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.Services
{
    using RevitCivilConnector.Utils;

    public class RevitGeometryService
    {
        private Document _doc;

        public RevitGeometryService(Document doc)
        {
            _doc = doc;
        }

        public void CreateDirectShapes(List<GeometryData> geometryDataList, BuiltInCategory category, Material material)
        {
            // 1. Get Shared Coordinate Transform
            // This handles Position AND Rotation (True North)
            Transform sharedToInternal = Transform.Identity;
            ProjectLocation activeLoc = _doc.ActiveProjectLocation;
            if (activeLoc != null)
            {
               sharedToInternal = activeLoc.GetTotalTransform().Inverse; 
            }
            
            // DIAGNOSTIC SUMMARY
            int totalChunks = geometryDataList.Count;
            Logger.Log($"RevitGeometryService: Received {totalChunks} chunks.");
            if (totalChunks == 0) return;

            // 2. CHECK COORDINATES STRATEGY
            // We verify if Shared Coordinates are valid by testing the first point.
            // If transformed point is within range, we use Shared Coordinates (Correct Placement/Rotation).
            // If NOT, we fallback to Auto-Centering (Incorrect Rotation, but visible geometry).
            
            XYZ globalOffset = XYZ.Zero;
            bool useSharedCoords = false;
            bool autoCenter = false; 
            double scaleFactor = 3.28084; // Meters to Feet
            
            if (geometryDataList[0].Vertices.Count > 0)
            {
                double[] firstV = geometryDataList[0].Vertices[0];
                XYZ pRaw = new XYZ(firstV[0] * scaleFactor, firstV[1] * scaleFactor, firstV[2] * scaleFactor);
                XYZ pTransformed = sharedToInternal.OfPoint(pRaw);
                
                // Revit Limit Check (~30,000 ft)
                bool transformedIsSafe = Math.Abs(pTransformed.X) < 30000 && Math.Abs(pTransformed.Y) < 30000;
                
                if (transformedIsSafe)
                {
                    useSharedCoords = true;
                    Logger.Log($"[INFO] Shared Coordinates Valid. Transformed Point: {pTransformed}. Using Shared Placement.");
                }
                else
                {
                    autoCenter = true;
                    // Center using raw values to keep it simple, ignoring rotation since Shared setup is obviously wrong
                    globalOffset = new XYZ(firstV[0], firstV[1], 0); 
                    Logger.Log($"[WARNING] Shared Coordinates result too large ({pTransformed}). Shared Site might be missing. Fallback to Auto-Center.");
                }
            }

            foreach (var geoData in geometryDataList)
            {
                try
                {
                    TessellatedShapeBuilder builder = new TessellatedShapeBuilder();
                    builder.OpenConnectedFaceSet(false);
                    
                    List<XYZ> vertices = new List<XYZ>();
                    foreach(var v in geoData.Vertices)
                    {
                        XYZ finalPt;
                        
                        if (useSharedCoords)
                        {
                            // Correct Path: Scale -> Transform
                            XYZ raw = new XYZ(v[0] * scaleFactor, v[1] * scaleFactor, v[2] * scaleFactor);
                            finalPt = sharedToInternal.OfPoint(raw);
                        }
                        else
                        {
                            // Fallback Path: Offset -> Scale
                            double x = v[0] - globalOffset.X;
                            double y = v[1] - globalOffset.Y;
                            double z = v[2]; // Keep Z relative to 0 or absolute? Usually absolute Z is fine in simple cases.
                            finalPt = new XYZ(x * scaleFactor, y * scaleFactor, z * scaleFactor);
                        }
                        
                        vertices.Add(finalPt);
                    }
                    
                    Logger.Log($"  Chunk Vertices: {vertices.Count}. First (Local): {vertices[0]}");

                    if (geoData.Faces.Count == 0)
                    {
                        Logger.Log("  [WARNING] Chunk has 0 faces. Skipping.");
                        continue;
                    }

                    foreach (var faceIndices in geoData.Faces)
                    {
                        if (faceIndices.Length >= 3)
                        {
                            List<XYZ> faceVerts = new List<XYZ>();
                            bool valid = true;
                            for(int k=0; k<3; k++) 
                            { 
                                int idx = faceIndices[k];
                                if(idx >= 0 && idx < vertices.Count)
                                    faceVerts.Add(vertices[idx]);
                                else
                                    valid = false;
                            }
                            
                            if (valid)
                            {
                                TessellatedFace tFace = new TessellatedFace(faceVerts, ElementId.InvalidElementId);
                                if (material != null)
                                {
                                    tFace.MaterialId = material.Id;
                                }
                                builder.AddFace(tFace);
                            }
                        }
                    }

                    builder.CloseConnectedFaceSet();
                    
                    // IMPORTANT: Change to AnyGeometry to allow Open Shells (Meshes)
                    builder.Target = TessellatedShapeBuilderTarget.AnyGeometry; 
                    builder.Fallback = TessellatedShapeBuilderFallback.Mesh;
                    
                    builder.Build();
                    TessellatedShapeBuilderResult result = builder.GetBuildResult();
                    
                    var geomObjects = result.GetGeometricalObjects();
                    if (geomObjects.Count > 0)
                    {
                        DirectShape ds = DirectShape.CreateElement(_doc, new ElementId(category));
                        ds.SetShape(geomObjects);
                        ds.Name = "Civil 3D Corridor Geometry";
                        Logger.Log("  DirectShape created successfully.");
                    }
                    else
                    {
                        Logger.Log($"  Builder failed. Result state: {result.Outcome}");
                        // foreach(var issue in result.Issues) Logger.Log($"    - {issue}");
                        
                        // Fallback fallback: Wireframe
                         Logger.Log("  Trying Wireframe fallback...");
                         List<GeometryObject> curves = new List<GeometryObject>();
                         for(int i=0; i<vertices.Count-1; i++)
                         {
                             try { curves.Add(Line.CreateBound(vertices[i], vertices[i+1])); } catch {}
                         }
                         if (curves.Count > 0)
                         {
                             DirectShape dsLines = DirectShape.CreateElement(_doc, new ElementId(BuiltInCategory.OST_Lines));
                             dsLines.SetShape(curves);
                             dsLines.Name = "Civil 3D Wireframe (Solid Failed)";
                             Logger.Log("  Wireframe fallback created.");
                         }
                    }
                }
                catch (Exception ex)
                {
                    Logger.Log($"  [ERROR] Error creating shape: {ex.Message} \n {ex.StackTrace}");
                }
            }
        }
    }
}
