using System;
using System.Collections.Generic;
using System.Reflection;
using System.Windows.Media.Imaging;
using Autodesk.Revit.UI;
using RevitCivilConnector.Auth;
using RevitCivilConnector.UI;
using System.IO;

namespace RevitCivilConnector
{
    public class App : IExternalApplication
    {
        private static TrackingService _tracker;
        private static bool _hasPromptedLogin = false;
        
        // UI Handler references for dynamic update (Explicit Namespace to avoid Ambiguity)
        private static Autodesk.Revit.UI.TextBox _tbUser;
        private static Autodesk.Revit.UI.TextBox _tbStatus;
        private static Autodesk.Revit.UI.TextBox _tbRole;

        private static string ICONS_PATH;

        public Result OnStartup(UIControlledApplication application)
        {
            // Init Auth & Tracking
            _tracker = new TrackingService(application);
            
            // Subscribe to Idling for First Run Login Check
            application.Idling += OnIdling;

            // Subscribe to Auth Login Event to update UI
            AuthService.Instance.OnLogin += UpdateUserInfo;

            // Create Ribbon Tab
            string tabName = "AOdev";
            try
            {
                application.CreateRibbonTab(tabName);
            }
            catch (Exception) { } 

            string assemblyPath = Assembly.GetExecutingAssembly().Location;

            // ====================================================
            // PANEL: CivilConnection
            // ====================================================
            RibbonPanel pCivil = application.CreateRibbonPanel(tabName, "CivilConnection");
            
            PushButtonData btnCivil = new PushButtonData("cmdCivil", "Civil 3D\nImport", assemblyPath, "RevitCivilConnector.Command");
            btnCivil.LargeImage = GetIcon("icono1.png");
            btnCivil.ToolTip = "Importa Corridors de Civil 3D.";
            btnCivil.AvailabilityClassName = "RevitCivilConnector.Auth.CivilAuthAvailability";
            pCivil.AddItem(btnCivil);


            // ====================================================
            // PANEL: Graficos
            // ====================================================
            RibbonPanel pGraph = application.CreateRibbonPanel(tabName, "Graficos");

            // Apply Halftone
            PushButtonData btnApplyH = new PushButtonData("cmdApplyH", "Apply\nHalftone", assemblyPath, "RevitCivilConnector.ApplyHalftoneCommand");
            btnApplyH.LargeImage = GetIcon("icono2.png");
            btnApplyH.AvailabilityClassName = "RevitCivilConnector.Auth.GraphicsAuthAvailability";
            
            // Remove Halftone
            PushButtonData btnRemH = new PushButtonData("cmdRemH", "Remove\nHalftone", assemblyPath, "RevitCivilConnector.RemoveHalftoneCommand");
            btnRemH.LargeImage = GetIcon("icono3.png");
            btnRemH.AvailabilityClassName = "RevitCivilConnector.Auth.GraphicsAuthAvailability";
            
            // Inverse Halftone
            PushButtonData btnInvH = new PushButtonData("cmdInvH", "Inverse\nHalftone", assemblyPath, "RevitCivilConnector.InverseHalftoneCommand");
            btnInvH.LargeImage = GetIcon("icono4.png");
            btnInvH.AvailabilityClassName = "RevitCivilConnector.Auth.GraphicsAuthAvailability";

            // VG Master
            PushButtonData btnVG = new PushButtonData("cmdVG", "VG\nMaster", assemblyPath, "RevitCivilConnector.VGMasterCommand");
            btnVG.LargeImage = GetIcon("icono5.png");
            btnVG.AvailabilityClassName = "RevitCivilConnector.Auth.GraphicsAuthAvailability";

            // Pattern Maker
            PushButtonData btnPat = new PushButtonData("cmdPat", "Pattern\nMaker", assemblyPath, "RevitCivilConnector.PatternMakerCommand");
            btnPat.LargeImage = GetIcon("icono6.png");
            btnPat.AvailabilityClassName = "RevitCivilConnector.Auth.GraphicsAuthAvailability";

            pGraph.AddItem(btnApplyH);
            pGraph.AddItem(btnRemH);
            pGraph.AddItem(btnInvH);
            pGraph.AddSeparator();
            pGraph.AddItem(btnVG);
            pGraph.AddItem(btnPat);


            // ====================================================
            // PANEL: Documentacion
            // ====================================================
            RibbonPanel pDoc = application.CreateRibbonPanel(tabName, "Documentacion");

            // Generate Details
            PushButtonData btnGenDet = new PushButtonData("cmdGenDet", "Generate\nDetails", assemblyPath, "RevitCivilConnector.CreateDetailViewsCommand");
            btnGenDet.LargeImage = GetIcon("icono7.png");
            btnGenDet.AvailabilityClassName = "RevitCivilConnector.Auth.DocsAuthAvailability";

            // Tag Pipes
            PushButtonData btnTag = new PushButtonData("cmdTag", "Tag\nPipes", assemblyPath, "RevitCivilConnector.TagPipesCommand");
            btnTag.LargeImage = GetIcon("icono8.png");
            btnTag.AvailabilityClassName = "RevitCivilConnector.Auth.DocsAuthAvailability";

            pDoc.AddItem(btnGenDet);
            pDoc.AddItem(btnTag);


            // ====================================================
            // PANEL: Topografia
            // ====================================================
            RibbonPanel pTopo = application.CreateRibbonPanel(tabName, "Topografia");

            // Profile Grid
            PushButtonData btnProf = new PushButtonData("cmdProf", "Profile\nGrid", assemblyPath, "RevitCivilConnector.CreateProfileGridCommand");
            btnProf.LargeImage = GetIcon("icono9.png");
            btnProf.AvailabilityClassName = "RevitCivilConnector.Auth.TopoAuthAvailability";

            // Coordenadas
            PushButtonData btnCoord = new PushButtonData("cmdCoord", "Coordenadas", assemblyPath, "RevitCivilConnector.CoordinatesCommand");
            btnCoord.LargeImage = GetIcon("icono10.png");
            btnCoord.AvailabilityClassName = "RevitCivilConnector.Auth.TopoAuthAvailability";

            pTopo.AddItem(btnProf);
            pTopo.AddItem(btnCoord);


            // ====================================================
            // PANEL: Vegetacion
            // ====================================================
            RibbonPanel pVeg = application.CreateRibbonPanel(tabName, "Vegetacion");

            // Vegetation Scatter
            PushButtonData btnVeg = new PushButtonData("cmdVeg", "Vegetation\nScatter", assemblyPath, "RevitCivilConnector.VegetationScatterCommand");
            btnVeg.LargeImage = GetIcon("icono11.png");
            btnVeg.AvailabilityClassName = "RevitCivilConnector.Auth.VegAuthAvailability";
            
            pVeg.AddItem(btnVeg);


            // ====================================================
            // PANEL: DWGImport
            // ====================================================
            RibbonPanel pDwg = application.CreateRibbonPanel(tabName, "DWGImport");

            // DWG Transformer
            PushButtonData btnDwg = new PushButtonData("cmdDwg", "DWG\nTransformer", assemblyPath, "RevitCivilConnector.DWGToNativeCommand");
            btnDwg.LargeImage = GetIcon("icono12.png");
            btnDwg.AvailabilityClassName = "RevitCivilConnector.Auth.DwgAuthAvailability";

            pDwg.AddItem(btnDwg);


            // ====================================================
            // ====================================================
            // PANEL: Cuantificaciones
            // ====================================================
            RibbonPanel pQuant = application.CreateRibbonPanel(tabName, "Cuantificaciones");
            
            // Button 1: Cloud Quantifys
            PushButtonData btnCloud = new PushButtonData("cmdCloudQ", "Cloud\nQuantifys", assemblyPath, "RevitCivilConnector.CloudQuantifysCommand");
            btnCloud.LargeImage = GetIcon("icono13.png"); 
            btnCloud.ToolTip = "Vinculación de Datos Cloud y Gestión de Cards.";
            btnCloud.AvailabilityClassName = "RevitCivilConnector.Auth.QuantAuthAvailability";
            
            // Button 2: Create Card (Selection)
            PushButtonData btnCard = new PushButtonData("cmdCreateCard", "Crear\nTarjeta", assemblyPath, "RevitCivilConnector.CreateCardCommand");
            btnCard.LargeImage = GetIcon("icono7.png"); 
            btnCard.ToolTip = "Crea una tarjeta de cuantificación a partir de la selección actual";
            btnCard.AvailabilityClassName = "RevitCivilConnector.Auth.QuantAuthAvailability";

            pQuant.AddItem(btnCloud);
            pQuant.AddItem(btnCard);


            // ====================================================
            // PANEL: Management model
            // ====================================================
            RibbonPanel pMgmt = application.CreateRibbonPanel(tabName, "Management model");

            // IA Assistant Button
            PushButtonData btnIA = new PushButtonData("cmdIA", "AO\niA", assemblyPath, "RevitCivilConnector.IACommand");
            btnIA.LargeImage = GetIcon("ia.png");
            btnIA.ToolTip = "Asistente IA para revisión y documentación";
            
            pMgmt.AddItem(btnIA);

            // ====================================================
            // PANEL: Usuario (Right Side)
            // ====================================================
            RibbonPanel pUser = application.CreateRibbonPanel(tabName, "Usuario");

            // Login Button
            PushButtonData btnLogin = new PushButtonData("cmdLogin", "AO\nLogin", assemblyPath, "RevitCivilConnector.LoginCommand");
            btnLogin.LargeImage = GetIcon("logo_ao_white.png"); // Using new white logo for ribbon too if desired, or keep LOGO AO DEV.png
            btnLogin.ToolTip = "Iniciar sesión";
            
            pUser.AddItem(btnLogin);

            pUser.AddSeparator();



            // User Info TextBoxes (Stacked)
            
            TextBoxData tdUser = new TextBoxData("txtUser");

            // Width set later on instance
            
            TextBoxData tdStatus = new TextBoxData("txtStatus");

            // Width set later on instance

            TextBoxData tdRole = new TextBoxData("txtRole");

            // Width set later on instance
            
            // We can stack 3 items.
            IList<RibbonItem> stacked = pUser.AddStackedItems(tdUser, tdStatus, tdRole);
            
            if (stacked.Count >= 3)
            {
                _tbUser = stacked[0] as Autodesk.Revit.UI.TextBox;
                _tbStatus = stacked[1] as Autodesk.Revit.UI.TextBox;
                _tbRole = stacked[2] as Autodesk.Revit.UI.TextBox;

                if (_tbUser != null) { _tbUser.Width = 150; _tbUser.Value = "Desconectado"; _tbUser.Enabled = false; }
                if (_tbStatus != null) { _tbStatus.Width = 150; _tbStatus.Value = "Offline"; _tbStatus.Enabled = false; }
                if (_tbRole != null) { _tbRole.Width = 150; _tbRole.Value = "--"; _tbRole.Enabled = false; }
            }

            // ====================================================
            // PANEL: Info (Right Most - Logo)
            // ====================================================
            RibbonPanel pInfo = application.CreateRibbonPanel(tabName, "AO Info");
            
            PushButtonData btnInfo = new PushButtonData("cmdInfo", "AO\nDev", assemblyPath, "RevitCivilConnector.InfoCommand");
            btnInfo.LargeImage = GetIcon("LOGO_AO_DEV_32.png");
            btnInfo.ToolTip = "Información del Plugin AO Development";
            
            pInfo.AddItem(btnInfo);

            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication application)
        {
            if (_tracker != null) _tracker.Stop();
            return Result.Succeeded;
        }

        private void OnIdling(object sender, Autodesk.Revit.UI.Events.IdlingEventArgs e)
        {
            if (_hasPromptedLogin)
            {
                if (sender is UIControlledApplication app) app.Idling -= OnIdling;
                return;
            }

            _hasPromptedLogin = true;
            
            if (!AuthService.Instance.IsLoggedIn)
            {
                 // Prompt Login
                 LoginWindow win = new LoginWindow();
                 win.ShowDialog();
            }
        }

        private static void UpdateUserInfo()
        {
            try 
            {
                if (AuthService.Instance.IsLoggedIn)
                {
                    if (_tbUser != null) _tbUser.Value = AuthService.Instance.CurrentUserName;
                    if (_tbStatus != null) _tbStatus.Value = $"En Linea - {DateTime.Now:dd/MM/yyyy}";
                    if (_tbRole != null) _tbRole.Value = $"{AuthService.Instance.CurrentUserRole} | v{AuthService.Instance.LatestPluginVersion ?? "1.0"}";
                }
                else
                {
                    if (_tbUser != null) _tbUser.Value = "Desconectado";
                    if (_tbStatus != null) _tbStatus.Value = "Offline";
                    if (_tbRole != null) _tbRole.Value = "--";
                }
            } 
            catch { }
        }

        private System.Windows.Media.ImageSource GetIcon(string fileName)
        {
            try
            {
                // Load from Embedded Resource
                var assembly = Assembly.GetExecutingAssembly();
                // Resource ID convention: Namespace.Folder.Filename
                string resourceName = "RevitCivilConnector.Resources." + fileName;

                using (Stream stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream != null)
                    {
                        BitmapImage bmp = new BitmapImage();
                        bmp.BeginInit();
                        bmp.StreamSource = stream;
                        bmp.CacheOption = BitmapCacheOption.OnLoad;
                        bmp.EndInit();
                        bmp.Freeze();
                        return bmp;
                    }
                }
            }
            catch (Exception) { }
            return null;
        }
    }
}
