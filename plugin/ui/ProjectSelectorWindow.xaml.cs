
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Windows;
using System.Windows.Controls;
using Newtonsoft.Json;
using System.Threading.Tasks;
using RevitCivilConnector.Auth;

namespace RevitCivilConnector.UI
{
    public partial class ProjectSelectorWindow : Window
    {
        public class SessionItem
        {
            public string session_id { get; set; }
            public string name { get; set; } // Subproject Name
            public string updated { get; set; }
        }

        public class FolderItem
        {
            public string id { get; set; }
            public string name { get; set; }
            public List<SessionItem> sessions { get; set; }
        }

        public class FolderListResponse
        {
            public List<FolderItem> folders { get; set; }
        }

        public string SelectedSessionId { get; private set; }
        public string SelectedProjectName { get; private set; }
        public string SelectedFolderId { get; private set; } // New property

        public ProjectSelectorWindow()
        {
            InitializeComponent();
            LoadProjects();
        }

        private async void LoadProjects()
        {
            try
            {
                using (HttpClient client = new HttpClient())
                {
                    // Add Auth
                    if (AuthService.Instance.IsLoggedIn)
                        client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                    string url = "https://aodevelopment-production.up.railway.app/api/plugin/cloud/list-folders";
                    var json = await client.GetStringAsync(url);
                    var response = JsonConvert.DeserializeObject<FolderListResponse>(json);
                    
                    lstFolders.ItemsSource = response.folders;
                }
            }
            catch (Exception ex)
            {
                txtStatus.Text = "Error conectando: " + ex.Message;
            }
        }

        private async void BtnCreateFolder_Click(object sender, RoutedEventArgs e)
        {
            string name = txtNewInput.Text;
            if (string.IsNullOrWhiteSpace(name) || name == "Nombre...")
            {
                MessageBox.Show("Ingrese un nombre para la carpeta.");
                return;
            }

            try 
            {
                using (HttpClient client = new HttpClient())
                {
                    // Add Auth
                    if (AuthService.Instance.IsLoggedIn)
                        client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                    string url = "https://aodevelopment-production.up.railway.app/api/plugin/cloud/create-folder";
                    var payload = new { name = name };
                    var content = new StringContent(JsonConvert.SerializeObject(payload), System.Text.Encoding.UTF8, "application/json");
                    
                    var res = await client.PostAsync(url, content);
                    if (res.IsSuccessStatusCode)
                    {
                        txtNewInput.Text = "Nombre...";
                        LoadProjects(); // Refresh
                    }
                    else
                    {
                         MessageBox.Show("Error al crear carpeta.");
                    }
                }
            }
            catch(Exception ex) { MessageBox.Show("Error: " + ex.Message); }
        }

        private void BtnCreateSub_Click(object sender, RoutedEventArgs e)
        {
            // Creates a NEW session inside this folder
            if (sender is Button btn && btn.Tag is string folderId)
            {
                string name = txtNewInput.Text;
                if (string.IsNullOrWhiteSpace(name) || name == "Nombre...")
                {
                    MessageBox.Show("Ingrese un nombre para el subproyecto en la caja de texto inferior.");
                    txtNewInput.Focus();
                    return;
                }

                SelectedProjectName = name;
                SelectedFolderId = folderId;
                SelectedSessionId = null; // Backend will generate or Plugin will start new
                
                this.DialogResult = true;
                this.Close();
            }
        }

        private void BtnJoin_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.Tag is SessionItem session)
            {
                SelectedProjectName = session.name;
                SelectedSessionId = session.session_id;
                SelectedFolderId = null; // Existing session, folder association is in DB, plugin doesn't need to re-send it necessarily?
                // Actually, tracked session loop in Plugin might re-sync. 
                // Ideally we should know the folder ID, but if we don't pass it, backend shouldn't unset it.
                // But let's check update loop.
                
                this.DialogResult = true;
                this.Close();
            }
        }

        private async void BtnDeleteFolder_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.Tag is string fId)
            {
                if (MessageBox.Show("¿Eliminar carpeta y contenidos?", "Confirmar", MessageBoxButton.YesNo) == MessageBoxResult.Yes)
                {
                    try {
                        using (HttpClient client = new HttpClient()) {
                             if (AuthService.Instance.IsLoggedIn)
                                client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                             var payload = new { folder_id = fId };
                             // Request expects JSON for embed=True check in FastAPI? 
                             // FastAPI Body(embed=True) means: { "folder_id": "..." }
                             var json = JsonConvert.SerializeObject(payload);
                             var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                             
                             await client.PostAsync("https://aodevelopment-production.up.railway.app/api/plugin/cloud/delete-folder", content);
                             LoadProjects();
                        }
                    } catch {}
                }
            }
        }

        private async void BtnArchiveSession_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.Tag is string sId)
            {
                if (MessageBox.Show("¿Eliminar subproyecto?", "Confirmar", MessageBoxButton.YesNo) == MessageBoxResult.Yes)
                {
                    using (HttpClient client = new HttpClient())
                    {
                         if (AuthService.Instance.IsLoggedIn)
                            client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                         await client.PostAsync($"https://aodevelopment-production.up.railway.app/api/plugin/cloud/archive-project?session_id={sId}", null);
                         LoadProjects();
                    }
                }
            }
        }

        private void TxtNewInput_GotFocus(object sender, RoutedEventArgs e)
        {
            if (txtNewInput.Text == "Nombre...")
            {
                txtNewInput.Text = "";
                txtNewInput.Foreground = System.Windows.Media.Brushes.White;
            }
        }

        private void TxtNewInput_LostFocus(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrWhiteSpace(txtNewInput.Text))
            {
                txtNewInput.Text = "Nombre...";
                txtNewInput.Foreground = System.Windows.Media.Brushes.Gray;
            }
        }

        private async void BtnRenameFolder_Click(object sender, RoutedEventArgs e)
        {
            if (sender is Button btn && btn.Tag is string fId)
            {
                string newName = ShowInput("Renombrar Carpeta", "Ingresa el nuevo nombre:");
                if (!string.IsNullOrWhiteSpace(newName))
                {
                    try {
                        using (HttpClient client = new HttpClient()) {
                             if (AuthService.Instance.IsLoggedIn)
                                client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                             var payload = new { folder_id = fId, new_name = newName };
                             var json = JsonConvert.SerializeObject(payload);
                             var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                             
                             var res = await client.PostAsync("https://aodevelopment-production.up.railway.app/api/plugin/cloud/rename-folder", content);
                             if (res.IsSuccessStatusCode)
                                LoadProjects();
                             else
                                MessageBox.Show("Error al renombrar.");
                        }
                    } catch (Exception ex) { MessageBox.Show("Error: " + ex.Message); }
                }
            }
        }

        private async void BtnRenameSession_Click(object sender, RoutedEventArgs e)
        {
             if (sender is Button btn && btn.Tag is string sId)
            {
                string newName = ShowInput("Renombrar Proyecto", "Ingresa el nuevo nombre:");
                if (!string.IsNullOrWhiteSpace(newName))
                {
                    try {
                        using (HttpClient client = new HttpClient()) {
                             if (AuthService.Instance.IsLoggedIn)
                                client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", AuthService.Instance.AccessToken);

                             var payload = new { session_id = sId, new_name = newName };
                             var json = JsonConvert.SerializeObject(payload);
                             var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                             
                             var res = await client.PostAsync("https://aodevelopment-production.up.railway.app/api/plugin/cloud/rename-session", content);
                             if (res.IsSuccessStatusCode)
                                LoadProjects();
                             else
                                MessageBox.Show("Error al renombrar.");
                        }
                    } catch (Exception ex) { MessageBox.Show("Error: " + ex.Message); }
                }
            }
        }

        private string ShowInput(string title, string prompt)
        {
            Window win = new Window()
            {
                Width = 300, Height = 150, Title = title,
                WindowStartupLocation = WindowStartupLocation.CenterScreen,
                ResizeMode = ResizeMode.NoResize,
                WindowStyle = WindowStyle.ToolWindow,
                Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(43, 45, 56))
            };
            
            StackPanel sp = new StackPanel() { Margin = new Thickness(20) };
            
            TextBlock lbl = new TextBlock() { Text = prompt, Foreground = System.Windows.Media.Brushes.White, Margin = new Thickness(0,0,0,10), FontSize=14 };
            TextBox txt = new TextBox() { Margin = new Thickness(0,0,0,15), Height=25, VerticalContentAlignment=VerticalAlignment.Center };
            
            Button btn = new Button() { Content = "Confirmar", IsDefault = true, Height=30, Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(79, 70, 229)), Foreground = System.Windows.Media.Brushes.White, BorderThickness=new Thickness(0) };
            btn.Click += (s, ev) => { win.DialogResult = true; win.Close(); };
            
            sp.Children.Add(lbl);
            sp.Children.Add(txt);
            sp.Children.Add(btn);
            win.Content = sp;
            
            bool? result = win.ShowDialog();
            if (result == true) return txt.Text;
            return null;
        }
