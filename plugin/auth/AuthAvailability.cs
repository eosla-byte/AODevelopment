using System;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace RevitCivilConnector.Auth
{
    /// <summary>
    /// Base Availability Class
    /// </summary>
    public abstract class BaseAuthAvailability : IExternalCommandAvailability
    {
        protected abstract string RequiredPermission { get; }

        public bool IsCommandAvailable(UIApplication applicationData, CategorySet selectedCategories)
        {
            if (applicationData.ActiveUIDocument == null) return false;
            
            if (!AuthService.Instance.IsLoggedIn) return false;
            
            // Check specific permission
            return AuthService.Instance.HasPermission(RequiredPermission);
        }
    }

    public class AuthAvailability : IExternalCommandAvailability
    {
        // Legacy or General Access
        public bool IsCommandAvailable(UIApplication applicationData, CategorySet selectedCategories)
        {
             if (applicationData.ActiveUIDocument == null) return false;
             return AuthService.Instance.IsLoggedIn;
        }
    }

    // Specific Categories
    public class CivilAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "CivilConnection";
    }

    public class GraphicsAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "Graficos";
    }
    
    public class DocsAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "Documentacion";
    }
    
    public class TopoAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "Topografia";
    }
    
    public class VegAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "Vegetacion";
    }

    public class DwgAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "DWGImport";
    }

    public class QuantAuthAvailability : BaseAuthAvailability
    {
        protected override string RequiredPermission => "Cuantificaciones";
    }

    public class MgmtAuthAvailability : BaseAuthAvailability
    {
        // Use a generic permission or reusing one, but 'Management' implies login check + maybe license
        protected override string RequiredPermission => "General"; // Or just rely on IsLoggedIn check if permission system is too granular
    }
}
