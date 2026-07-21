const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const { autoUpdater } = require('electron-updater');

const ENV_PATH = app.isPackaged 
  ? path.join(process.resourcesPath, '.env')
  : path.join(__dirname, '..', '.env');
const ENV_EXAMPLE_PATH = app.isPackaged 
  ? path.join(process.resourcesPath, '.env.example')
  : path.join(__dirname, '..', '.env.example');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, 'icon.ico')
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.loadFile('index.html');

  // Auto Updater logic
  autoUpdater.forceDevUpdateConfig = true;
  
  autoUpdater.on('checking-for-update', () => {
    mainWindow.webContents.send('update-message', 'Checking for updates...');
  });
  
  autoUpdater.on('update-available', (info) => {
    mainWindow.webContents.send('update-message', `Version ${info.version} update available! Downloading...`);
  });
  
  autoUpdater.on('update-not-available', (info) => {
    mainWindow.webContents.send('update-message', 'Up to date.');
  });
  
  autoUpdater.on('error', (err) => {
    mainWindow.webContents.send('update-message', 'Update error. ' + err.message);
  });
  
  autoUpdater.on('download-progress', (progressObj) => {
    mainWindow.webContents.send('update-progress', progressObj.percent);
  });
  
  autoUpdater.on('update-downloaded', (info) => {
    mainWindow.webContents.send('update-message', 'Update downloaded! Restarting...');
    setTimeout(() => {
      autoUpdater.quitAndInstall();
    }, 3000);
  });

  // Check for updates after the window is loaded
  mainWindow.webContents.on('did-finish-load', async () => {
    try {
      await autoUpdater.checkForUpdatesAndNotify();
    } catch (error) {
      let msg = error.message;
      if (msg.includes('404')) msg = 'Unable to fetch latest release from server.';
      mainWindow.webContents.send('update-message', 'Update error: ' + msg);
    }
  });
}

ipcMain.handle('check-for-updates', async () => {
  try {
    await autoUpdater.checkForUpdatesAndNotify();
    return { status: 'success' };
  } catch (error) {
    let msg = error.message;
    if (msg.includes('404')) msg = 'Unable to fetch latest release from server.';
    BrowserWindow.getAllWindows()[0].webContents.send('update-message', 'Update error: ' + msg);
    return { status: 'error', message: msg };
  }
});


app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});


app.on('before-quit', () => {
  if (zenithProcess) {
    // Kill the cmd process and all its children (the python engine) on Windows
    const { exec } = require('child_process');
    exec(`taskkill /pid ${zenithProcess.pid} /T /F`);
  }
});

ipcMain.handle('read-env', () => {
  let content = '';
  if (fs.existsSync(ENV_PATH)) {
    content = fs.readFileSync(ENV_PATH, 'utf-8');
  } else if (fs.existsSync(ENV_EXAMPLE_PATH)) {
    content = fs.readFileSync(ENV_EXAMPLE_PATH, 'utf-8');
  }

  const config = {};
  const lines = content.split('\n');
  lines.forEach(line => {
    if (line.includes('=') && !line.trim().startsWith('#')) {
      const [key, ...rest] = line.split('=');
      config[key.trim()] = rest.join('=').trim();
    }
  });
  return config;
});

ipcMain.handle('save-env', (event, data) => {
  try {
    let content = '';
    if (fs.existsSync(ENV_PATH)) {
      content = fs.readFileSync(ENV_PATH, 'utf-8');
    } else if (fs.existsSync(ENV_EXAMPLE_PATH)) {
      content = fs.readFileSync(ENV_EXAMPLE_PATH, 'utf-8');
    }

    const lines = content.split('\n');
    const envDict = { ...data };
    const newLines = [];
    const updatedKeys = new Set();

    lines.forEach(line => {
      if (line.includes('=') && !line.trim().startsWith('#')) {
        const key = line.split('=')[0].trim();
        if (key in envDict && envDict[key] !== undefined && envDict[key] !== null) {
          newLines.push(`${key}=${envDict[key]}`);
          updatedKeys.add(key);
        } else {
          newLines.push(line);
        }
      } else {
        newLines.push(line);
      }
    });

    for (const key in envDict) {
      if (!updatedKeys.has(key) && envDict[key]) {
        newLines.push(`${key}=${envDict[key]}`);
      }
    }

    fs.writeFileSync(ENV_PATH, newLines.join('\n'));
    return { status: 'success', message: 'Settings saved to Zenith matrix!' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

const { spawn } = require('child_process');
let zenithProcess = null;

ipcMain.handle('start-zenith', () => {
  try {
    if (zenithProcess) {
      return { status: 'error', message: 'Zenith is already online.' };
    }

    const backendDir = app.isPackaged
      ? process.resourcesPath
      : path.join(__dirname, '..');
      
    // Activate virtual environment and run the script
    const batScript = `.\\venv\\Scripts\\activate && python agent.py console > zenith.log 2>&1`;
    zenithProcess = spawn('cmd.exe', ['/c', batScript], {
      cwd: backendDir,
      stdio: 'ignore',
      windowsHide: true,
      env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' }
    });
    
    zenithProcess.on('exit', () => {
      zenithProcess = null;
    });

    return { status: 'success' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

ipcMain.handle('stop-zenith', () => {
  try {
    if (zenithProcess) {
      const { exec } = require('child_process');
      exec(`taskkill /pid ${zenithProcess.pid} /T /F`);
      zenithProcess = null;
      return { status: 'success', message: 'Zenith terminated.' };
    }
    return { status: 'error', message: 'Zenith is not running.' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

ipcMain.handle('check-zenith-status', () => {
  return zenithProcess !== null;
});
