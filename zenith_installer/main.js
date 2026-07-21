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
    
    // This URL automatically resolves to the latest version uploaded to your GitHub Releases.
    // Replace 'YourGitHubUsername' and 'ZenithApp' with your actual GitHub details.
    const payloadUrl = 'https://github.com/Adbhut1234/Zenith/releases/latest/download/zenith.zip';

    // Use options or fallback to default
    const destDir = options && options.destDir 
      ? options.destDir 
      : path.join(process.env.LOCALAPPDATA, 'Programs', 'Zenith');
      
    const tempZipPath = path.join(app.getPath('temp'), 'zenith_payload.zip');

    // Make sure destination exists and is clean
    if (fs.existsSync(destDir)) {
      event.sender.send('install-status', 'Removing old version...');
      await fs.remove(destDir);
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
    event.sender.send('install-status', 'Extracting files...');

    // Extract logic
    await extract(tempZipPath, { dir: destDir });

    // Clean up temp zip
    await fs.remove(tempZipPath);

    event.sender.send('install-progress', 80);
    event.sender.send('install-status', 'Creating shortcuts...');

    // Create Desktop Shortcut using PowerShell
    const exePath = path.join(destDir, 'Zenith.exe');
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
      psCommand += createShortcutPS(desktopPath, exePath) + ' ; ';
    }
    if (options && options.createStartMenu) {
      psCommand += createShortcutPS(startMenuPath, exePath) + ' ; ';
    }

    if (psCommand) {
      await new Promise((resolve, reject) => {
        exec(`powershell -Command "${psCommand.replace(/\n/g, ' ')}"`, (err) => {
          if (err) resolve(); // Ignore shortcut errors
          else resolve();
        });
      });
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
