using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.ExtensibleStorage;
using RevitCivilConnector.models;
using Newtonsoft.Json;

namespace RevitCivilConnector.services
{
    public static class TakeoffStorageService
    {
        private static readonly Guid SchemaGuid = new Guid("A0D1AD10-3456-4ABC-DEF1-123456789ABC");
        private static readonly string SchemaName = "AO_TakeoffTypes_Schema";
        private static readonly string FieldName = "TakeoffTypesJson";

        public static void SavePackages(Document doc, List<TakeoffPackage> packages)
        {
            Schema schema = GetOrCreateSchema();
            Entity entity = GetStorageEntity(doc, schema);
            
            string json = JsonConvert.SerializeObject(packages);

            using (Transaction t = new Transaction(doc, "Save Takeoff Packages"))
            {
                t.Start();
                entity.Set(FieldName, json);
                doc.ProjectInformation.SetEntity(entity);
                t.Commit();
            }
        }

        public static List<TakeoffPackage> LoadPackages(Document doc)
        {
            Schema schema = GetOrCreateSchema();
            Entity entity = doc.ProjectInformation.GetEntity(schema);

            if (entity.IsValid())
            {
                try 
                {
                    string json = entity.Get<string>(FieldName);
                    if (!string.IsNullOrEmpty(json))
                    {
                        // Attempt to deserialize new structure
                        try 
                        {
                            return JsonConvert.DeserializeObject<List<TakeoffPackage>>(json);
                        }
                        catch
                        {
                            // Fallback: It might be the old List<TakeoffType> format.
                            // Migrate it to a default package.
                            var oldTypes = JsonConvert.DeserializeObject<List<TakeoffType>>(json);
                            if (oldTypes != null)
                            {
                                return new List<TakeoffPackage> 
                                { 
                                    new TakeoffPackage 
                                    { 
                                        Name = "Migrated / General", 
                                        Types = oldTypes 
                                    } 
                                };
                            }
                        }
                    }
                }
                catch {}
            }
            // Default if nothing found or error
            return new List<TakeoffPackage> { new TakeoffPackage { Name = "General", Version = "V1" } };
        }

        private static Schema GetOrCreateSchema()
        {
            Schema schema = Schema.Lookup(SchemaGuid);
            if (schema == null)
            {
                SchemaBuilder builder = new SchemaBuilder(SchemaGuid);
                builder.SetReadAccessLevel(AccessLevel.Public);
                builder.SetWriteAccessLevel(AccessLevel.Public);
                builder.SetSchemaName(SchemaName);
                builder.AddSimpleField(FieldName, typeof(string));
                schema = builder.Finish();
            }
            return schema;
        }

        private static Entity GetStorageEntity(Document doc, Schema schema)
        {
            Entity entity = doc.ProjectInformation.GetEntity(schema);
            if (!entity.IsValid())
            {
                entity = new Entity(schema);
            }
            return entity;
        }
    }
}
