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
        public static Services.TransactionRecorder Recorder; // Public static for access from IAWindow
        private static bool _hasPromptedLogin = false;
        
        // UI Handler references for dynamic update (Explicit Namespace to avoid Ambiguity)
        private static Autodesk.Revit.UI.TextBox _tbUser;
        private static Autodesk.Revit.UI.TextBox _tbStatus;
        private static Autodesk.Revit.UI.TextBox _tbRole;

        // Dynamic Panel Management
        private static Dictionary<string, RibbonPanel> _managedPanels = new Dictionary<string, RibbonPanel>();

        private static string ICONS_PATH;

        public Result OnStartup(UIControlledApplication application)
        {
            // Init Auth & Tracking
            _tracker = new TrackingService(application);
            Recorder = new Services.TransactionRecorder(application.ControlledApplication);
            
            // Subscribe to Idling for First Run Login Check
            application.Idling += OnIdling;

            // Subscribe to Auth Login Event to update UI
            AuthService.Instance.OnLogin += UpdateUserInfo;

            // Init Visualizer
            var vizHandler = new Services.VisualizerHandler();
            var vizEvent = ExternalEvent.Create(vizHandler);
            AuthService.Instance.InitVisualizer(vizHandler, vizEvent);

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
            _managedPanels["CivilConnection"] = pCivil;
            
            PushButtonData btnCivil = new PushButtonData("cmdCivil", "Civil 3D\nImport", assemblyPath, "RevitCivilConnector.Command");
            btnCivil.LargeImage = GetIcon("icono1.png");
            btnCivil.ToolTip = "Importa Corridors de Civil 3D.";
            btnCivil.AvailabilityClassName = "RevitCivilConnector.Auth.CivilAuthAvailability";
            pCivil.AddItem(btnCivil);


            // ====================================================
            // PANEL: Graficos
            // ====================================================
            RibbonPanel pGraph = application.CreateRibbonPanel(tabName, "Graficos");
            _managedPanels["Graficos"] = pGraph;

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
            _managedPanels["Documentacion"] = pDoc;

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
            _managedPanels["Topografia"] = pTopo;

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
            _managedPanels["Vegetacion"] = pVeg;

            // Vegetation Scatter
            PushButtonData btnVeg = new PushButtonData("cmdVeg", "Vegetation\nScatter", assemblyPath, "RevitCivilConnector.VegetationScatterCommand");
            btnVeg.LargeImage = GetIcon("icono11.png");
            btnVeg.AvailabilityClassName = "RevitCivilConnector.Auth.VegAuthAvailability";
            
            pVeg.AddItem(btnVeg);


            // ====================================================
            // PANEL: DWGImport
            // ====================================================
            RibbonPanel pDwg = application.CreateRibbonPanel(tabName, "DWGImport");
            _managedPanels["DWGImport"] = pDwg;

            // DWG Transformer
            PushButtonData btnDwg = new PushButtonData("cmdDwg", "DWG\nTransformer", assemblyPath, "RevitCivilConnector.DWGToNativeCommand");
            btnDwg.LargeImage = GetIcon("icono12.png");
            btnDwg.AvailabilityClassName = "RevitCivilConnector.Auth.DwgAuthAvailability";

            pDwg.AddItem(btnDwg);


            // ====================================================
            // PANEL: Cuantificaciones
            // ====================================================
            RibbonPanel pQuant = application.CreateRibbonPanel(tabName, "Cuantificaciones");
            _managedPanels["Cuantificaciones"] = pQuant;
            
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
            _managedPanels["Management"] = pMgmt;

            // IA Assistant Button
            PushButtonData btnIA = new PushButtonData("cmdIA", "AO\niA", assemblyPath, "RevitCivilConnector.IACommand");
            btnIA.LargeImage = GetIcon("ia.png");
            btnIA.ToolTip = "Asistente IA para revisión y documentación";
            btnIA.AvailabilityClassName = "RevitCivilConnector.Auth.MgmtAuthAvailability";
            
            pMgmt.AddItem(btnIA);

            // ====================================================
            // PANEL: AO Labs (Experimental)
            // ====================================================
            RibbonPanel pLabs = application.CreateRibbonPanel(tabName, "AO Labs");
            _managedPanels["Labs"] = pLabs;
            pLabs.Visible = false; // Hidden by default

            // Experimental AI or new tools here
            // Re-using IA button as an example of what could be here, or a new placeholder
            PushButtonData btnExp = new PushButtonData("cmdExp", "Experimental\nTool", assemblyPath, "RevitCivilConnector.IACommand");
            btnExp.LargeImage = GetIcon("ia.png");
            btnExp.ToolTip = "Herramienta experimental (Solo Devs).";
            
            // AI MONITOR (Admin Only)
            PushButtonData btnMon = new PushButtonData("cmdAIMonitor", "AI\nMonitor", assemblyPath, "RevitCivilConnector.AIMonitorCommand");
            btnMon.LargeImage = GetIcon("ia.png"); // Reuse or new icon
            btnMon.ToolTip = "Monitor de Actividad de IA (Admin).";
            
            pLabs.AddItem(btnExp);
            pLabs.AddItem(btnMon);
            pLabs.AddSeparator();

            // 15 Generic Buttons (Stacked in groups of 3 -> 5 Columns)
            for (int i = 1; i <= 15; i += 3)
            {
                 // Create 3 buttons
                 // EXP 01 -> Sheet Manager
                 string cmd1Class = (i == 1) ? "RevitCivilConnector.Commands.SheetManagerCommand" : "RevitCivilConnector.IACommand";
                 string name1 = (i == 1) ? "Sheet\nManager" : $"Exp {i:00}";
                 
                 PushButtonData b1 = new PushButtonData($"cmdExp{i}", name1, assemblyPath, cmd1Class); 
                 b1.Image = GetIcon("icono7.png"); // Small Image
                 b1.ToolTip = (i == 1) ? "Gestor Avanzado de Sheets (Exp 01)" : $"Experimental Function {i}";

                 // EXP 02 -> Cloud Manager (was generic Exp 02)
                 // Replaces: PushButtonData b2 = new PushButtonData($"cmdExp{i+1}", $"Exp {i+1:00}", assemblyPath, "RevitCivilConnector.IACommand");
                 string cmd2Class = (i == 1) ? "RevitCivilConnector.CloudQuantifysCommand" : "RevitCivilConnector.IACommand";
                 string name2 = (i == 1) ? "Cloud\nManager" : $"Exp {i+1:00}";
                 string icon2 = (i == 1) ? "icono13.png" : "icono7.png";
                 string tip2 = (i == 1) ? "Acceso directo a Cloud Manager" : $"Experimental Function {i+1}";

                 PushButtonData b2 = new PushButtonData($"cmdExp{i+1}", name2, assemblyPath, cmd2Class);
                 b2.Image = GetIcon(icon2);
                 b2.ToolTip = tip2;

                 PushButtonData b3 = new PushButtonData($"cmdExp{i+2}", $"Exp {i+2:00}", assemblyPath, "RevitCivilConnector.IACommand");
                 b3.Image = GetIcon("icono7.png");
                 b3.ToolTip = $"Experimental Function {i+2}";
                 
                 pLabs.AddStackedItems(b1, b2, b3);
            }


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
            TextBoxData tdStatus = new TextBoxData("txtStatus");
            TextBoxData tdRole = new TextBoxData("txtRole");
            
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
            if (Recorder != null) Recorder.StopRecording();
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
                bool loggedIn = AuthService.Instance.IsLoggedIn;

                // Update UI TextBoxes
                if (loggedIn)
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

                // Update Panel Visibility Logic
                foreach (var kvp in _managedPanels)
                {
                    string permKey = kvp.Key;
                    RibbonPanel panel = kvp.Value;

                    if (!loggedIn)
                    {
                        // If Logged Out -> Hide everything except Login?
                        // Or hide everything. 
                        // But wait, the Login button is in the "Usuario" panel whch is NOT in _managedPanels.
                        // So panels like "Graficos", "CivilConnection" etc will be HIDDEN.
                        panel.Visible = false; 
                    }
                    else
                    {
                        if (permKey == "Labs")
                        {
                            // "Labs" special Check: Role = Developer/Admin or specific perm
                            // We check if "Labs" permission is explicitly true OR Role is special
                            string role = AuthService.Instance.CurrentUserRole ?? "";
                            bool isDev = role.IndexOf("Admin", StringComparison.OrdinalIgnoreCase) >= 0 || 
                                         role.IndexOf("Dev", StringComparison.OrdinalIgnoreCase) >= 0 ||
                                         role.IndexOf("Arquitecto", StringComparison.OrdinalIgnoreCase) >= 0; // Assuming Arqui is Dev for now

                            // Or check AuthService.Instance.HasPermission("Labs") if backend sends it
                            // For now, let's trust the permissions dict if it has it, else callback to Role
                            if (AuthService.Instance.HasPermission("Labs") && AuthService.Instance.UserPermissions != null && AuthService.Instance.UserPermissions.ContainsKey("Labs"))
                            {
                                // Explicitly allowed
                                panel.Visible = true;
                            }
                            else
                            {
                                // Fallback role check
                                panel.Visible = isDev; 
                            }
                        }
                        else
                        {
                            // Standard Panels
                            // If userPermissions is NULL or empty, HasPermission returns True.
                            // However, if we want to RESTRICT, we need to know if the user specifically HAS access.
                            // The backend should send the list of allowed modules.
                            // If `HasPermission` returns true for everything if the dict is missing, that's a security/UX risk if we want to hide things.
                            // But usually, Admin sets "Allowed Modules".
                            // Let's assume standard behavior: Show if allowed.
                            panel.Visible = AuthService.Instance.HasPermission(permKey);
                        }
                    }
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
