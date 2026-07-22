const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const { exec } = require('child_process');
const axios = require('axios');
const extract = require('extract-zip');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 500,
    frame: false,
    transparent: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, 'build/icon.ico')
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('get-default-path', () => {
  return path.join(process.env.LOCALAPPDATA, 'Programs', 'Zenith');
});

ipcMain.handle('select-directory', async (event) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  if (result.canceled) {
    return null;
  }
  return result.filePaths[0];
});

// Installation Logic
ipcMain.on('install-app', async (event, options) => {
  try {
    event.sender.send('install-status', 'Preparing installation...');
    
    // Pointing to GitHub Releases for fast, trusted distribution
    const payloadUrl = 'https://github.com/Adbhut1234/JARVIS/releases/download/v1.0.0/zenith.zip';

    // Use options or fallback to default
    const destDir = options && options.destDir 
      ? options.destDir 
      : path.join(process.env.LOCALAPPDATA, 'Programs', 'Zenith');
      
    const tempZipPath = path.join(app.getPath('temp'), 'zenith_payload.zip');

    // Make sure destination exists and is clean
    if (fs.existsSync(destDir)) {
      event.sender.send('install-status', 'Closing running instances...');
      // Force kill Zenith if it is currently running so we can delete the folder
      await new Promise((resolve) => {
        exec('taskkill /F /IM Zenith.exe', () => resolve());
      });
      
      // Wait a moment for the process lock to release
      await new Promise(r => setTimeout(r, 1000));

      event.sender.send('install-status', 'Removing old version...');
      try {
        await fs.remove(destDir);
      } catch (rmErr) {
        throw new Error('Could not remove the old folder. Please ensure Zenith is fully closed, close any File Explorer windows pointing to the Zenith folder, and try again.');
      }
    }
    await fs.ensureDir(destDir);

    event.sender.send('install-status', 'Downloading main application files...');

    // Download logic
    const writer = fs.createWriteStream(tempZipPath);

    const response = await axios({
      url: payloadUrl,
      method: 'GET',
      responseType: 'stream',
      onDownloadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          // Scale download from 0% to 70% of the overall progress bar
          event.sender.send('install-progress', Math.floor(percentCompleted * 0.7));
        }
      }
    });

    response.data.pipe(writer);

    await new Promise((resolve, reject) => {
      writer.on('finish', resolve);
      writer.on('error', reject);
    });

    event.sender.send('install-progress', 75);
    event.sender.send('install-status', 'Extracting files (Hardware Accelerated)...');

    // Extract logic: Try native Windows 10+ tar for 10x faster extraction, fallback to JS
    try {
      await new Promise((resolve, reject) => {
        exec(`tar -xf "${tempZipPath}" -C "${destDir}"`, { maxBuffer: 1024 * 1024 * 10 }, (err) => {
          if (err) reject(err);
          else resolve();
        });
      });
    } catch (tarErr) {
      console.log('Tar failed, falling back to JS extract-zip...');
      await extract(tempZipPath, { dir: destDir });
    }

    // Clean up temp zip
    await fs.remove(tempZipPath);

    event.sender.send('install-progress', 80);
    event.sender.send('install-status', 'Registering application...');

    // Create a simple Uninstaller script
    const uninstallerPath = path.join(destDir, 'Uninstall.bat');
    const uninstallScript = `@echo off\necho Uninstalling Zenith...\ntaskkill /F /IM Zenith.exe >nul 2>&1\nreg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Zenith" /f >nul 2>&1\ntimeout /t 2 >nul\nrmdir /S /Q "${destDir}"\n`;
    await fs.writeFile(uninstallerPath, uninstallScript);

    const exePath = path.join(destDir, 'Zenith.exe');
    
    // Write Registry Keys to show up in "Add/Remove Programs"
    const registryPsCommand = `
      $regPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Zenith"
      New-Item -Path $regPath -Force | Out-Null
      Set-ItemProperty -Path $regPath -Name "DisplayName" -Value "Zenith"
      Set-ItemProperty -Path $regPath -Name "DisplayIcon" -Value "${exePath}"
      Set-ItemProperty -Path $regPath -Name "Publisher" -Value "Enc0deX"
      Set-ItemProperty -Path $regPath -Name "DisplayVersion" -Value "1.0.0"
      Set-ItemProperty -Path $regPath -Name "UninstallString" -Value '"${uninstallerPath}"'
    `;

    const tempRegScript = path.join(app.getPath('temp'), 'zenith_reg.ps1');
    await fs.writeFile(tempRegScript, registryPsCommand);
    await new Promise((resolve) => {
      exec(`powershell -ExecutionPolicy Bypass -File "${tempRegScript}"`, () => resolve());
    });
    fs.remove(tempRegScript).catch(()=>{});

    event.sender.send('install-status', 'Creating shortcuts...');

    // Create Desktop Shortcut using PowerShell
    const desktopPath = path.join(process.env.USERPROFILE, 'Desktop', 'Zenith.lnk');
    const startMenuPath = path.join(process.env.APPDATA, 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Zenith.lnk');

    const createShortcutPS = (shortcutPath, targetPath) => {
      return `
        $WshShell = New-Object -comObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("${shortcutPath}")
        $Shortcut.TargetPath = "${targetPath}"
        $Shortcut.WorkingDirectory = "${path.dirname(targetPath)}"
        $Shortcut.Save()
      `;
    };

    let psCommand = '';
    if (options && options.createDesktop) {
      psCommand += createShortcutPS(desktopPath, exePath) + '\n';
    }
    if (options && options.createStartMenu) {
      psCommand += createShortcutPS(startMenuPath, exePath) + '\n';
    }

    if (psCommand) {
      const tempShortcutScript = path.join(app.getPath('temp'), 'zenith_shortcut.ps1');
      await fs.writeFile(tempShortcutScript, psCommand);
      await new Promise((resolve) => {
        exec(`powershell -ExecutionPolicy Bypass -File "${tempShortcutScript}"`, () => resolve());
      });
      fs.remove(tempShortcutScript).catch(()=>{});
    }

    event.sender.send('install-progress', 100);
    event.sender.send('install-status', 'Installation complete! Launching Zenith...');

    // Launch the app
    setTimeout(() => {
      shell.openPath(exePath);
      app.quit();
    }, 2000);

  } catch (error) {
    console.error("Install Error:", error);
    let userMessage = 'Installation failed: An unexpected error occurred.';
    
    // Check if it's a network-related error
    if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED' || error.message.includes('Network Error') || error.code === 'ETIMEDOUT') {
      userMessage = 'Network Error: Please check your internet connection and try again.';
    } else if (error.response && error.response.status === 404) {
      userMessage = 'Download Error: The installation files could not be found on the server.';
    } else if (error.message) {
      userMessage = 'Error: ' + error.message;
    }

    event.sender.send('install-error', userMessage);
  }
});

ipcMain.on('close-installer', () => {
  app.quit();
});
