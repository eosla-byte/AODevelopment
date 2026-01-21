[Setup]
AppName=AOdev Plugin
AppVersion=1.4.0
DefaultDirName={userappdata}\Autodesk\Revit\Addins\2024
OutputDir=A:\AO_DEVELOPMENT\AO-Instaladores
OutputBaseFilename=Install_AOdev_Plugin_v1.4.0
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "A:\AO_DEVELOPMENT\AODevelopment\plugin\bin\Release\net48\*.dll"; DestDir: "{app}\AOdev"; Flags: ignoreversion
Source: "A:\AO_DEVELOPMENT\AODevelopment\plugin\AOdev_Release.addin"; DestDir: "{app}"; DestName: "AOdev.addin"; Flags: ignoreversion
