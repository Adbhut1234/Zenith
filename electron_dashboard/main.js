const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

const ENV_PATH = path.join(__dirname, '..', '.env');
const ENV_EXAMPLE_PATH = path.join(__dirname, '..', '.env.example');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    require('electron').shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.loadFile('index.html');
}

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
  if (jarvisProcess) {
    // Kill the cmd process and all its children (the python engine) on Windows
    const { exec } = require('child_process');
    exec(`taskkill /pid ${jarvisProcess.pid} /T /F`);
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
    return { status: 'success', message: 'Settings saved to J.A.R.V.I.S. matrix!' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

const { spawn } = require('child_process');
let jarvisProcess = null;

ipcMain.handle('start-jarvis', () => {
  try {
    if (jarvisProcess) {
      return { status: 'error', message: 'J.A.R.V.I.S. is already online.' };
    }

    const batScript = `.\\venv\\Scripts\\activate && python agent.py console > jarvis.log 2>&1`;
    jarvisProcess = spawn('cmd.exe', ['/c', batScript], {
      cwd: path.join(__dirname, '..'),
      stdio: 'ignore',
      windowsHide: true,
      env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' }
    });
    
    jarvisProcess.on('exit', () => {
      jarvisProcess = null;
    });

    return { status: 'success' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

ipcMain.handle('stop-jarvis', () => {
  try {
    if (jarvisProcess) {
      const { exec } = require('child_process');
      exec(`taskkill /pid ${jarvisProcess.pid} /T /F`);
      jarvisProcess = null;
      return { status: 'success', message: 'J.A.R.V.I.S. terminated.' };
    }
    return { status: 'error', message: 'J.A.R.V.I.S. is not running.' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});
