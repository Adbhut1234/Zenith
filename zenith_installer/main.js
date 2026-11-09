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
    center: true,
    show: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    icon: path.join(__dirname, 'build/icon.ico')
  });

  mainWindow.loadFile('index.html');

  mainWindow.once('ready-to-show', () => {
    mainWindow.center();
    mainWindow.show();
    mainWindow.focus();
  });
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
    
    // Use options or fallback to default
    const destDir = options && options.destDir 
      ? options.destDir 
      : path.join(process.env.LOCALAPPDATA, 'Programs', 'Zenith');

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

    const tempExePath = path.join(app.getPath('temp'), 'Zenith-Setup-1.0.2.exe');

    // 1. Check if an offline setup package is already present on disk (instant install, skip 590MB download)
    const localCandidates = [
      path.join(__dirname, 'Zenith-Setup-1.0.2.exe'),
      path.join(__dirname, '..', 'electron_dashboard', 'dist', 'Zenith-Setup-1.0.2.exe'),
      path.join(process.cwd(), 'Zenith-Setup-1.0.2.exe')
    ];

    let foundLocal = false;
    for (const loc of localCandidates) {
      if (fs.existsSync(loc) && fs.statSync(loc).size > 100000000) {
        console.log('Found local setup package at:', loc);
        event.sender.send('install-status', 'Found local installation package, preparing setup...');
        event.sender.send('install-progress', 40);
        await fs.copy(loc, tempExePath);
        event.sender.send('install-progress', 85);
        foundLocal = true;
        break;
      }
    }

    if (!foundLocal) {
      event.sender.send('install-status', 'Connecting to high-speed release mirror...');

      // Resilient endpoints:
      // Endpoint 1: GitHub API asset endpoint redirects directly to Azure Blob storage (bypasses CDN 504 timeouts)
      // Endpoint 2: Direct release URL
      // Endpoint 3: Release v1.0.1 fallback
      const downloadEndpoints = [
        {
          url: 'https://api.github.com/repos/Adbhut1234/Zenith/releases/assets/702045937',
          headers: { 'User-Agent': 'Zenith-Windows-Installer', 'Accept': 'application/octet-stream' }
        },
        {
          url: 'https://github.com/Adbhut1234/Zenith/releases/download/v1.0.2/Zenith-Setup-1.0.2.exe',
          headers: { 'User-Agent': 'Zenith-Windows-Installer' }
        },
        {
          url: 'https://github.com/Adbhut1234/Zenith/releases/download/v1.0.1/Zenith-Setup-1.0.1.exe',
          headers: { 'User-Agent': 'Zenith-Windows-Installer' }
        }
      ];

      let stream = null;
      let totalBytes = 0;

      for (const ep of downloadEndpoints) {
        try {
          console.log('Attempting download from:', ep.url);
          const response = await axios({
            url: ep.url,
            method: 'GET',
            headers: ep.headers,
            maxRedirects: 10,
            timeout: 30000,
            responseType: 'stream'
          });

          if (response.status === 200) {
            stream = response.data;
            totalBytes = parseInt(response.headers['content-length'] || 0, 10);
            console.log('Connected to mirror, size:', totalBytes);
            break;
          }
        } catch (fetchErr) {
          console.warn('Endpoint failed:', ep.url, fetchErr.message);
        }
      }

      if (!stream) {
        throw new Error('All download mirrors timed out or were unreachable. Please verify your internet connection or run the offline installer directly.');
      }

      event.sender.send('install-status', 'Downloading main application files...');
      const writer = fs.createWriteStream(tempExePath);

      let downloadedBytes = 0;
      stream.on('data', (chunk) => {
        downloadedBytes += chunk.length;
        if (totalBytes > 0) {
          const percent = Math.min(85, Math.round((downloadedBytes / totalBytes) * 85));
          event.sender.send('install-progress', percent);
        }
      });

      stream.pipe(writer);

      await new Promise((resolve, reject) => {
        writer.on('finish', resolve);
        writer.on('error', reject);
      });
    }

    event.sender.send('install-progress', 90);
    event.sender.send('install-status', 'Installing Zenith silently...');
    await new Promise((resolve) => {
      exec(`"${tempExePath}" /S`, () => resolve());
    });

    fs.remove(tempExePath).catch(() => {});
    event.sender.send('install-progress', 100);
    event.sender.send('install-status', 'Installation complete! Launching Zenith...');
    setTimeout(() => {
      app.quit();
    }, 1500);
    return;

    // Fallback zip download logic
    const writer = fs.createWriteStream(tempZipPath);

    const response = await axios({
      url: payloadUrl,
      method: 'GET',
      responseType: 'stream',
      onDownloadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
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

    event.sender.send('install-status', 'Configuring system shortcuts...');

    // Helper to create valid Windows .lnk shortcuts via Windows Script Host (works without PS execution restrictions)
    const createWindowsShortcut = (shortcutPath, targetPath, workingDir, iconPath) => {
      const vbsPath = path.join(app.getPath('temp'), `zenith_sc_${Date.now()}_${Math.random().toString(36).substring(2, 6)}.vbs`);
      const vbsLines = [
        'Set ws = CreateObject("WScript.Shell")',
        `Set sc = ws.CreateShortcut(${JSON.stringify(shortcutPath)})`,
        `sc.TargetPath = ${JSON.stringify(targetPath)}`,
        `sc.WorkingDirectory = ${JSON.stringify(workingDir || path.dirname(targetPath))}`
      ];
      if (iconPath) {
        vbsLines.push(`sc.IconLocation = ${JSON.stringify(iconPath + ',0')}`);
      }
      vbsLines.push('sc.Save');

      fs.writeFileSync(vbsPath, vbsLines.join('\r\n'), 'utf8');
      try {
        require('child_process').execSync(`cscript //nologo "${vbsPath}"`, { windowsHide: true });
      } finally {
        try { fs.unlinkSync(vbsPath); } catch (_) {}
      }
    };

    // 1. Desktop Shortcut (Handles both UserProfile\Desktop and OneDrive\Desktop if present)
    const desktopDirs = new Set([
      app.getPath('desktop'),
      process.env.USERPROFILE ? path.join(process.env.USERPROFILE, 'Desktop') : null
    ]);

    const shouldCreateDesktop = Boolean(options && options.createDesktop);
    for (const dir of desktopDirs) {
      if (!dir) continue;
      const lnkPath = path.join(dir, 'Zenith.lnk');
      if (shouldCreateDesktop) {
        try {
          fs.ensureDirSync(dir);
          createWindowsShortcut(lnkPath, exePath, destDir, exePath);
        } catch (scErr) {
          console.error('Failed to create desktop shortcut in', dir, scErr);
        }
      } else {
        // Explicitly unchecked: ensure shortcut is not present
        try {
          if (fs.existsSync(lnkPath)) {
            fs.removeSync(lnkPath);
          }
        } catch (rmErr) {
          console.error('Failed to remove desktop shortcut in', dir, rmErr);
        }
      }
    }

    // 2. Start Menu Shortcut
    const startMenuDir = path.join(app.getPath('appData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs');
    const startMenuLnk = path.join(startMenuDir, 'Zenith.lnk');
    const shouldCreateStartMenu = Boolean(options && options.createStartMenu);

    if (shouldCreateStartMenu) {
      try {
        fs.ensureDirSync(startMenuDir);
        createWindowsShortcut(startMenuLnk, exePath, destDir, exePath);
      } catch (scErr) {
        console.error('Failed to create Start Menu shortcut', scErr);
      }
    } else {
      // Explicitly unchecked: ensure shortcut is not present
      try {
        if (fs.existsSync(startMenuLnk)) {
          fs.removeSync(startMenuLnk);
        }
      } catch (rmErr) {
        console.error('Failed to remove Start Menu shortcut', rmErr);
      }
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
