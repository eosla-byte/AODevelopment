
using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Windows;
using System.Windows.Controls;
using Newtonsoft.Json;
using System.Threading.Tasks;

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
                    string url = "http://localhost:8000/api/plugin/cloud/list-folders";
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
                    string url = "http://localhost:8000/api/plugin/cloud/create-folder";
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
                             var payload = new { folder_id = fId };
                             // Request expects JSON for embed=True check in FastAPI? 
                             // FastAPI Body(embed=True) means: { "folder_id": "..." }
                             var json = JsonConvert.SerializeObject(payload);
                             var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
                             
                             await client.PostAsync("http://localhost:8000/api/plugin/cloud/delete-folder", content);
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
                         await client.PostAsync($"http://localhost:8000/api/plugin/cloud/archive-project?session_id={sId}", null);
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
    }
}
