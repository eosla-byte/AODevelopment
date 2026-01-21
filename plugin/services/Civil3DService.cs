using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

// Civil 3D / AutoCAD References
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.Civil.ApplicationServices;
using Transaction = Autodesk.AutoCAD.DatabaseServices.Transaction;

using RevitCivilConnector.Models;
using RevitCivilConnector.Utils;

namespace RevitCivilConnector.Services
{
    public class Civil3DService
    {
        private dynamic _acadApp;
        private dynamic _civilDoc;

        public bool IsCivil3DRunning()
        {
            try
            {
                _acadApp = Marshal.GetActiveObject("AutoCAD.Application");
                return _acadApp != null;
            }
            catch
            {
                return false;
            }
        }

        public List<CivilCorridor> GetCorridors()
        {
            var list = new List<CivilCorridor>();

            try
            {
                if (_acadApp == null) IsCivil3DRunning();

                dynamic activeDoc = _acadApp.ActiveDocument;
                string docName = activeDoc.Name;
                
                // Reflection to get CivilDocument
                _civilDoc = activeDoc.GetType().InvokeMember("CivilDocument", BindingFlags.GetProperty, null, activeDoc, null);

                Logger.Log($"[DEBUG] Civil 3D Active Document: {docName}");

                dynamic corridors = _civilDoc.CorridorCollection;
                int count = corridors.Count;
                Logger.Log($"[DEBUG] Found {count} corridors.");

                for (int i = 0; i < count; i++)
                {
                    dynamic corridor = corridors[i];
                    string cName = corridor.Name;
                    string cHandle = corridor.Handle;

                    var c = new CivilCorridor
                    {
                        Name = cName,
                        Handle = cHandle,
                        Codes = new List<CorridorCode>()
                    };

                    HashSet<string> foundCodes = new HashSet<string>();
                    
                    try
                    {
                        // Safe dynamic access to feature lines
                        dynamic baselines = corridor.Baselines;
                        foreach (dynamic baseline in baselines)
                        {
                            try
                            {
                                dynamic featureLinesCol = baseline.MainBaselineFeatureLines;
                                if (featureLinesCol != null)
                                {
                                    object codeInfos = GetComProperty(featureLinesCol, "FeatureLineCodeInfos");
                                    List<object> infos = ComToList(codeInfos);
                                    
                                    foreach (dynamic info in infos)
                                    {
                                        try { foundCodes.Add(info.CodeName); } catch { }
                                    }
                                }
                            }
                            catch { }
                        }
                    }
                    catch (Exception ex)
                    {
                         Logger.Log($"[ERROR] Error scanning FeatureLines: {ex.Message}");
                    }

                    // Fallback to Assembly Scan Logic (Simplified)
                    if (foundCodes.Count == 0)
                    {
                         try
                         {
                             dynamic baselines = corridor.Baselines;
                             foreach (dynamic b in baselines)
                             {
                                 dynamic regions = b.BaselineRegions;
                                 foreach(dynamic r in regions)
                                 {
                                     dynamic asms = r.AppliedAssemblies;
                                     if(asms.Count > 0)
                                     {
                                         dynamic asm = asms[0];
                                         List<object> shapes = ComToList(GetComProperty(asm, "Shapes"));
                                         foreach(dynamic s in shapes) {
                                             object codes = GetComProperty(s, "CorridorCodes");
                                             if (codes == null) codes = GetComProperty(s, "Codes");
                                             foreach(dynamic code in ComToList(codes)) foundCodes.Add(code.Name);
                                         }
                                         List<object> links = ComToList(GetComProperty(asm, "Links"));
                                         foreach(dynamic l in links) {
                                             object codes = GetComProperty(l, "CorridorCodes");
                                             if (codes == null) codes = GetComProperty(l, "Codes");
                                             foreach(dynamic code in ComToList(codes)) foundCodes.Add(code.Name);
                                         }
                                         break;
                                     }
                                 }
                                 break;
                             }
                         }
                         catch {}
                    }

                    if (foundCodes.Count > 0)
                    {
                        var sortedCodes = foundCodes.OrderBy(x => x).ToList();
                        foreach (string code in sortedCodes)
                        {
                            c.Codes.Add(new CorridorCode 
                            { 
                                CodeName = code, 
                                IsSelected = false,
                                RevitCategory = BuiltInCategory.OST_GenericModel // Use default
                            });
                        }
                    }
                    else
                    {
                        c.Codes.Add(new CorridorCode { CodeName = "Top", IsSelected = true, RevitCategory = BuiltInCategory.OST_GenericModel });
                        c.Codes.Add(new CorridorCode { CodeName = "Datum", IsSelected = false, RevitCategory = BuiltInCategory.OST_GenericModel });
                    }

                    list.Add(c);
                }
            }
            catch (Exception ex)
            {
                Logger.Log($"[ERROR] GetCorridors failed: {ex.Message}");
            }

            return list;
        }


        public List<GeometryData> GetSolidsForCorridorCode(string corridorHandle, string codeName)
        {
            List<GeometryData> results = new List<GeometryData>();

            try
            {
                Logger.Log($"[DEBUG] GetSolids (Native). Handle: {corridorHandle}, Code: {codeName}");

                Database db = HostApplicationServices.WorkingDatabase;
                if (db == null) return results;

                using (Transaction tr = db.TransactionManager.StartTransaction())
                {
                    long hn = Convert.ToInt64(corridorHandle, 16);
                    Handle handle = new Handle(hn);
                    ObjectId id = db.GetObjectId(false, handle, 0);

                    // --- KEY FIX: USE DYNAMIC FOR CORRIDOR TO AVOID AecBaseMgd REFERENCE ERROR ---
                    dynamic corr = tr.GetObject(id, OpenMode.ForRead);
                    
                    // Simple check if it's the right object type by name (safeguard)
                    if (corr != null)
                    {
                        // Use Reflection to instantiate ExportCorridorSolidsParams from Civil 3D assembly
                        // This avoids "ExportCorridorSolidsParams" type usage which might trigger assembly lookup
                        // actually, ExportCorridorSolidsParams is in Autodesk.Civil.DatabaseServices.
                        // If we can't use that using, we need to load it via reflection.
                        // Let's try to use the type if it's in Autodesk.Civil.DatabaseServices.dll which we REF.
                        // The issue was 'Corridor' pulling in 'Entity' from AecBaseMgd. 
                        // 'ExportCorridorSolidsParams' might be fine if it doesn't inherit from Entity.
                        // To be safe, let's use Activator if possible, OR just dynamic usage of the type if referenced.
                        
                        dynamic exportParams = null;
                        try 
                        {
                            // Try direct instantiation if the dll is ref'd
                            // If this fails compile-time due to missing AecBaseMgd, we'll need Activator.
                            // But usually Params are structurally simple.
                            // Let's rely on the fact that we have the Civil dll usage.
                            // If this line fails to compile, we will know.
                            // For now, I'll allow the type usage but cache it in dynamic.
                            // UPDATE: The error log didn't complain about ExportCorridorSolidsParams, only Corridor.
                            exportParams = new Autodesk.Civil.DatabaseServices.ExportCorridorSolidsParams();
                        }
                        catch 
                        {
                            // Fallback? Unlikely to work if reference is missing. 
                        }

                        if (exportParams != null)
                        {
                            try { exportParams.AddShapeCode(codeName); } catch {}
                            try { exportParams.AddLinkCode(codeName); } catch {}
                            
                            // Call ExportSolids using dynamic dispatch on 'corr'
                            ObjectId[] solidIds = corr.ExportSolids(exportParams, db);
                            Logger.Log($"[DEBUG] ExportSolids returned {solidIds.Length} solids.");

                            foreach (ObjectId solidId in solidIds)
                            {
                                Solid3d solid = tr.GetObject(solidId, OpenMode.ForWrite) as Solid3d;
                                if (solid != null)
                                {
                                    ProcessSolid(solid, results, codeName);
                                    solid.Erase();
                                }
                            }
                        }

                        tr.Commit();
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.Log($"[CRITICAL] Native Export Failed: {ex.Message}\n{ex.StackTrace}");
            }

            return results;
        }

        private void ProcessSolid(Solid3d solid, List<GeometryData> results, string matName)
        {
             try
            {
                Type brepType = GetBrepType();
                Type meshFilterType = GetMesh2dFilterType();
                Type mesh2dType = GetMesh2dType();
                
                if (brepType != null && meshFilterType != null && mesh2dType != null)
                {
                    dynamic brep = Activator.CreateInstance(brepType, new object[] { solid });
                    dynamic filter = Activator.CreateInstance(meshFilterType);
                    filter.MaxNodeSpacing = 5.0;
                    
                    dynamic mesh2d = Activator.CreateInstance(mesh2dType, new object[] { brep, filter });
                    
                    GeometryData geo = new GeometryData { MaterialName = matName };
                    
                    foreach(dynamic element in mesh2d.Element2ds)
                    {
                        List<int> indices = new List<int>();
                        foreach(dynamic node in element.Nodes)
                        {
                            dynamic p = node.Point;
                            geo.Vertices.Add(new double[] { p.X, p.Y, p.Z });
                            indices.Add(geo.Vertices.Count - 1);
                        }
                        
                        if (indices.Count == 3) 
                            geo.Faces.Add(new int[] { indices[0], indices[1], indices[2] });
                        else if (indices.Count == 4) {
                            geo.Faces.Add(new int[] { indices[0], indices[1], indices[2] });
                            geo.Faces.Add(new int[] { indices[0], indices[2], indices[3] });
                        }
                    }
                    
                    if (geo.Faces.Count > 0) results.Add(geo);
                    
                    try { ((IDisposable)mesh2d).Dispose(); } catch {}
                    try { ((IDisposable)filter).Dispose(); } catch {}
                    try { ((IDisposable)brep).Dispose(); } catch {}
                }
            }
            catch (Exception ex)
            {
                Logger.Log($"[WARNING] Brep Tessellation failed: {ex.Message}");
            }
        }

        // --- REFLECTION HELPERS FOR BREP ---
        private Type GetBrepType()
        {
            return Type.GetType("Autodesk.AutoCAD.BoundaryRepresentation.Brep, AcDbMgdBrep") ??
                   AppDomain.CurrentDomain.GetAssemblies().SelectMany(a => a.GetTypes()).FirstOrDefault(t => t.Name == "Brep" && t.Namespace == "Autodesk.AutoCAD.BoundaryRepresentation");
        }
        private Type GetMesh2dFilterType()
        {
             return Type.GetType("Autodesk.AutoCAD.BoundaryRepresentation.Mesh2dFilter, AcDbMgdBrep") ??
                    AppDomain.CurrentDomain.GetAssemblies().SelectMany(a => a.GetTypes()).FirstOrDefault(t => t.Name == "Mesh2dFilter");
        }
        private Type GetMesh2dType()
        {
             return Type.GetType("Autodesk.AutoCAD.BoundaryRepresentation.Mesh2d, AcDbMgdBrep") ??
                    AppDomain.CurrentDomain.GetAssemblies().SelectMany(a => a.GetTypes()).FirstOrDefault(t => t.Name == "Mesh2d");
        }

        // --- COM HELPERS ---
        private object GetComProperty(object obj, string name)
        {
            try { return obj.GetType().InvokeMember(name, BindingFlags.GetProperty, null, obj, null); }
            catch { return null; }
        }

        private List<object> ComToList(object comCollection)
        {
            var list = new List<object>();
            if (comCollection == null) return list;
            try
            {
                System.Collections.IEnumerable enumerable = comCollection as System.Collections.IEnumerable;
                if (enumerable != null) { foreach (object item in enumerable) list.Add(item); return list; }
                int count = (int)GetComProperty(comCollection, "Count");
                for (int i = 0; i < count; i++) {
                    object item = comCollection.GetType().InvokeMember("Item", BindingFlags.InvokeMethod, null, comCollection, new object[] { i });
                    list.Add(item);
                }
            } catch { }
            return list;
        }
    }
    
    public class GeometryData
    {
        public List<double[]> Vertices { get; set; } = new List<double[]>();
        public List<int[]> Faces { get; set; } = new List<int[]>();
        public string MaterialName { get; set; }
    }
}
