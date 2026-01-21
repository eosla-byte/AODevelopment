
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Autodesk.Revit.DB;

namespace RevitCivilConnector.Utils
{
    public static class DataExtractor
    {
        public static Dictionary<string, object> Extract(Document doc, ICollection<ElementId> selectionIds = null)
        {
            var data = new Dictionary<string, object>();
            
            // 1. Determine Scope
            IEnumerable<Element> elements;
            if (selectionIds != null && selectionIds.Count > 0)
            {
                elements = selectionIds.Select(id => doc.GetElement(id)).Where(e => e != null && e.Category != null);
            }
            else
            {
                // Full Doc (Filtered)
                elements = new FilteredElementCollector(doc)
                    .WhereElementIsNotElementType()
                    .Where(e => e.Category != null);
            }

            // 2. Group by Category
            var grouped = elements.GroupBy(e => e.Category.Name);
            var catStats = new List<Dictionary<string, object>>();

            foreach (var grp in grouped)
            {
                var catDict = new Dictionary<string, object>();
                catDict["name"] = grp.Key;
                catDict["count"] = grp.Count();

                // Limit elements to prevent timeouts on massive models, 
                // but since user asked for specific selection, we should be generous.
                // If selectionIds is provided, NO LIMIT. If full model, maybe 2000 limit per cat.
                var elementsList = (selectionIds != null) ? grp.ToList() : grp.Take(2000).ToList();

                var rows = new List<Dictionary<string, object>>();
                var availableHeaders = new HashSet<string>();

                foreach (Element e in elementsList)
                {
                    var row = new Dictionary<string, object>();
                    row["Id"] = e.Id.Value; // Changed from IntegerValue (int) to Value (long)
                    
                    // Element Name often varies (Family+Type or just Name)
                    row["Name"] = e.Name; 

                    // Extract ALL Parameters
                    foreach (Parameter p in e.Parameters)
                    {
                        if (p.Definition == null) continue;
                        string pName = p.Definition.Name;

                        // Skip empty/null usually? User said "Strictly all".
                        // We will try AsValueString first (formatted), then internal value.
                        string val = p.AsValueString();
                        
                        if (string.IsNullOrEmpty(val))
                        {
                             // Fallback to internal types
                             switch(p.StorageType)
                             {
                                 case StorageType.String: val = p.AsString(); break;
                                 case StorageType.Double: val = Math.Round(p.AsDouble(), 4).ToString(); break; // Raw internal units
                                 case StorageType.Integer: val = p.AsInteger().ToString(); break;
                                 case StorageType.ElementId: val = p.AsElementId().Value.ToString(); break; // Changed from IntegerValue
                             }
                        }
                        
                        // Clean nulls
                        if (val == null) val = "";

                        // Store
                        if (!row.ContainsKey(pName)) // Avoid dupes
                        {
                            row[pName] = val;
                            availableHeaders.Add(pName);
                        }
                    }

                    rows.Add(row);
                }

                catDict["rows"] = rows;
                catDict["headers"] = availableHeaders.OrderBy(x => x).ToList();

                catStats.Add(catDict);
            }


            // 3. Extract All Sheets (Always, for Compilacion Linking)
            var sheetCollector = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Sheets)
                .WhereElementIsNotElementType()
                .Cast<ViewSheet>();

            var sheetList = new List<string>();
            foreach (var sheet in sheetCollector)
            {
                // Format: "A101 - Name"
                string num = sheet.SheetNumber;
                string name = sheet.Name; 
                if (!string.IsNullOrEmpty(num))
                {
                    sheetList.Add($"{num} - {name}");
                }
            }
            sheetList.Sort();
            data["sheets"] = sheetList;

            // 4. Extract Schedules (Tablas de Cuantificacion)
            // Added per user request to import Schedules directly
            var scheduleData = new List<Dictionary<string, object>>();
            var schedules = new FilteredElementCollector(doc)
                .OfClass(typeof(ViewSchedule))
                .Cast<ViewSchedule>()
                .Where(v => !v.IsTemplate && !v.IsTitleblockRevisionSchedule && !v.IsInternalKeynoteSchedule);

            foreach (var vs in schedules)
            {
                try 
                {
                    var schedDict = new Dictionary<string, object>();
                    schedDict["name"] = vs.Name;
                    schedDict["id"] = vs.Id.Value; // Changed from IntegerValue

                    
                    // Extract Content
                    var rowsData = new List<Dictionary<string, string>>();
                    TableData tableData = vs.GetTableData();
                    TableSectionData sectionData = tableData.GetSectionData(SectionType.Body);
                    
                    if (sectionData != null)
                    {
                        int nRows = sectionData.NumberOfRows;
                        int nCols = sectionData.NumberOfColumns;

                        // Identify Headers (Row 0 usually, or headers section? Body usually starts with data if headers are separate, but typically Body includes headers in API view? No, Headers are separate SectionType.Header)
                        // Actually, GetCellText works on Body. 
                        // Let's assume First Row of Body is Header? Or usually Headers are in Header Section.
                        // Let's simplified: Column Names?
                        // For generic extraction, let's just grab Body. If it has headers, great.
                        
                        // We need column names to make the Dictionary keys.
                        // Let's allow generic keys "Col1", "Col2" if headers unavailable, but try to find headers.
                        var headers = new List<string>();
                        
                        // Try get headers from Body Row 0 or Header Section?
                        // Simple approach: Use Field Names if possible, or just Column Indexes.
                        // The user wants "replicar data".
                        
                        for (int c = 0; c < nCols; c++)
                        {
                            // Try to get a decent header name
                            string h = $"Column {c + 1}";
                            try {
                                // Sometimes Definition name? 
                                // ScheduleFieldId fieldId = vs.Definition.GetFieldId(c); // Not direct mapping index -> field
                                // Just read Row 0?
                                // Let's check Header Section
                                var headerSection = tableData.GetSectionData(SectionType.Header);
                                if (headerSection != null && headerSection.NumberOfRows > 0) {
                                     h = vs.GetCellText(SectionType.Header, headerSection.NumberOfRows - 1, c); // Last header row
                                }
                            } catch {}
                            if (string.IsNullOrWhiteSpace(h)) h = $"Column {c + 1}";
                            
                            // Dedupe
                            int suffix = 1;
                            string originalH = h;
                            while (headers.Contains(h)) { h = $"{originalH} ({suffix++})"; }
                            
                            headers.Add(h);
                        }

                        // Read Body Rows
                        for (int r = 0; r < nRows; r++)
                        {
                            var rowDict = new Dictionary<string, string>();
                            bool hasData = false;
                            for (int c = 0; c < nCols; c++)
                            {
                                string val = vs.GetCellText(SectionType.Body, r, c);
                                rowDict[headers[c]] = val;
                                if (!string.IsNullOrWhiteSpace(val)) hasData = true;
                            }
                            if (hasData) rowsData.Add(rowDict);
                        }
                    }
                    
                    schedDict["rows"] = rowsData;
                    // Only add if has rows? User might want empty schedule template.
                    scheduleData.Add(schedDict);
                }
                catch (Exception ex)
                {
                    // Skip schedule if fail
                    // Debug.WriteLine($"Error reading schedule {vs.Name}: {ex.Message}");
                }
            }
            
            data["schedules"] = scheduleData.OrderBy(s => s["name"]).ToList();

            data["categories"] = catStats.OrderByDescending(x => (int)x["count"]).ToList();
            return data;
        }
    }
}
