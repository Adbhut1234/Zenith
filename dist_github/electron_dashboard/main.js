const { app, BrowserWindow, ipcMain, shell, dialog, desktopCapturer } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { autoUpdater } = require('electron-updater');
const { spawn } = require('child_process');
const dgram = require('dgram');

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('ignore-gpu-blocklist');

const ENV_PATH = app.isPackaged 
  ? path.join(app.getPath('userData'), '.env') 
  : path.join(__dirname, '..', '.env');
const OLD_ENV_PATH = app.isPackaged 
  ? path.join(process.resourcesPath, '.env') 
  : path.join(__dirname, '..', '.env');

let overlayWindow = null;
let udpServer = null;
let overlayTopmostTimer = null;

function createOverlay() {
  if (overlayWindow) return;
  
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;
  const WIN_W = 680;
  const WIN_H = 380;

  overlayWindow = new BrowserWindow({
    width: WIN_W,
    height: WIN_H,
    x: Math.round((width - WIN_W) / 2),
    y: 5,
    transparent: true,
    frame: false,
    hasShadow: false,
    alwaysOnTop: true,
    focusable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false
    }
  });

  overlayWindow.setAlwaysOnTop(true, 'screen-saver', 1);
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  overlayWindow.loadFile(path.join(__dirname, 'jarvis_ui.html'));

  // Keep overlay window persistently topmost across Windows focus changes & desktop clicks
  if (overlayTopmostTimer) clearInterval(overlayTopmostTimer);
  overlayTopmostTimer = setInterval(() => {
    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.setAlwaysOnTop(true, 'screen-saver', 1);
      overlayWindow.moveTop();
    }
  }, 1000);

  if (!udpServer) {
    udpServer = dgram.createSocket('udp4');
    udpServer.on('message', (msg) => {
      const raw = msg.toString().trim();
      try {
        if (raw.startsWith('{') && raw.endsWith('}')) {
          const data = JSON.parse(raw);
          if (overlayWindow && !overlayWindow.isDestroyed()) {
            overlayWindow.webContents.send('music-event', data);
            if (data.type === 'weather') {
              overlayWindow.webContents.send('weather-event', data);
            }
          }
          return;
        }
      } catch (e) {
        // Fallback for string state
      }
      if (overlayWindow && !overlayWindow.isDestroyed()) {
        overlayWindow.webContents.send('ui-state', raw);
      }
    });
    udpServer.bind(49152);
  }
}

// --- Native Screen Vision Streamer (Zero-Friction Vision for Gemini Live) ---

let isScreenStreamingActive = false;

function postScreenFrame(jpegBuffer) {
  const req = http.request({
    hostname: '127.0.0.1',
    port: 49153,
    path: '/screen_frame',
    method: 'POST',
    headers: {
      'Content-Type': 'image/jpeg',
      'Content-Length': jpegBuffer.length
    },
    timeout: 800
  }, () => {});

  req.on('error', () => {});
  req.on('timeout', () => { req.destroy(); });
  req.write(jpegBuffer);
  req.end();
}

let screenStreamTimeout = null;
let isCapturingFrame = false;

async function captureAndSendScreen() {
  if (!isScreenStreamingActive || !zenithProcess || isCapturingFrame) return;
  isCapturingFrame = true;
  try {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 640, height: 360 }
    });
    if (sources && sources.length > 0) {
      const jpegBuf = sources[0].thumbnail.toJPEG(40);
      if (jpegBuf && jpegBuf.length > 0) {
        postScreenFrame(jpegBuf);
      }
    }
  } catch (e) {
  } finally {
    isCapturingFrame = false;
    if (isScreenStreamingActive) {
      screenStreamTimeout = setTimeout(captureAndSendScreen, 2500);
    }
  }
}

function startScreenStreaming() {
  if (isScreenStreamingActive) return;
  isScreenStreamingActive = true;
  captureAndSendScreen();
}

function stopScreenStreaming() {
  isScreenStreamingActive = false;
  if (screenStreamTimeout) {
    clearTimeout(screenStreamTimeout);
    screenStreamTimeout = null;
  }
}

function destroyOverlay() {
  stopScreenStreaming();
  if (overlayTopmostTimer) {
    clearInterval(overlayTopmostTimer);
    overlayTopmostTimer = null;
  }
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.close();
    overlayWindow = null;
  }
  if (udpServer) {
    udpServer.close();
    udpServer = null;
  }
}

ipcMain.on('set-ignore-mouse-events', (event, ignore, options) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (win && !win.isDestroyed()) {
    win.setIgnoreMouseEvents(ignore, options);
    // Re-assert topmost position on every hover state transition
    win.setAlwaysOnTop(true, 'screen-saver', 1);
    win.moveTop();
  }
});

const ENV_EXAMPLE_PATH = app.isPackaged 
  ? path.join(process.resourcesPath, '.env.example')
  : path.join(__dirname, '..', '.env.example');

// Migrate old .env from resources path to userData if it exists (for users updating to this version)
if (app.isPackaged) {
  if (fs.existsSync(OLD_ENV_PATH) && !fs.existsSync(ENV_PATH)) {
    try {
      fs.copyFileSync(OLD_ENV_PATH, ENV_PATH);
    } catch (e) {
      console.error('Failed to migrate .env', e);
    }
  }
}

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

  mainWindow.webContents.on('render-process-gone', (event, details) => {
    console.error('Renderer process gone:', details);
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Auto Updater logic
  const devUpdateConfigPath = path.join(__dirname, 'dev-app-update.yml');
  const hasDevUpdateConfig = fs.existsSync(devUpdateConfigPath);

  if (!app.isPackaged) {
    if (hasDevUpdateConfig) {
      autoUpdater.forceDevUpdateConfig = true;
    }
  }
  
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
    mainWindow.webContents.send('update-message', 'Update error: ' + err.message);
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
    if (!app.isPackaged && !hasDevUpdateConfig) {
      mainWindow.webContents.send('update-message', 'Development mode');
      return;
    }
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
  const devUpdateConfigPath = path.join(__dirname, 'dev-app-update.yml');
  const hasDevUpdateConfig = fs.existsSync(devUpdateConfigPath);
  if (!app.isPackaged && !hasDevUpdateConfig) {
    return { status: 'dev', message: 'Auto-updates disabled in development mode.' };
  }
  try {
    await autoUpdater.checkForUpdatesAndNotify();
    return { status: 'success' };
  } catch (error) {
    let msg = error.message;
    if (msg.includes('404')) msg = 'Unable to fetch latest release from server.';
    const windows = BrowserWindow.getAllWindows();
    if (windows.length > 0) {
      windows[0].webContents.send('update-message', 'Update error: ' + msg);
    }
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

    // Sanitize any accidentally pasted "KEY=" prefixes
    for (const key of Object.keys(envDict)) {
      if (typeof envDict[key] === 'string') {
        let val = envDict[key].trim();
        if (val.startsWith(`${key}=`)) {
          val = val.substring(`${key}=`.length).trim();
        } else if (val.includes('=')) {
          const parts = val.split('=');
          if (parts[0].trim().toUpperCase() === key.toUpperCase()) {
            val = parts.slice(1).join('=').trim();
          }
        }
        envDict[key] = val;
      }
    }

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

    const updatedContent = newLines.join('\n');
    fs.writeFileSync(ENV_PATH, updatedContent);

    // Keep userData synced as well if different from ENV_PATH
    const userDataEnv = path.join(app.getPath('userData'), '.env');
    if (ENV_PATH !== userDataEnv && fs.existsSync(userDataEnv)) {
      try {
        fs.writeFileSync(userDataEnv, updatedContent);
      } catch (e) {
        // ignore
      }
    }

    return { status: 'success', message: 'Settings saved to Zenith matrix!' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

let zenithProcess = null;

ipcMain.handle('start-zenith', () => {
  try {
    if (zenithProcess) {
      return { status: 'error', message: 'Zenith is already online.' };
    }

    const backendDir = app.isPackaged
      ? process.resourcesPath
      : path.join(__dirname, '..');
      
    const stopFile = path.join(backendDir, '.stop_zenith');
    if (fs.existsSync(stopFile)) {
      fs.unlinkSync(stopFile);
    }
      
    // Try to launch the compiled executable first (for portable distribution)
    let exePath = path.join(backendDir, 'zenith_backend', 'zenith_backend.exe');
    if (!app.isPackaged && !fs.existsSync(exePath)) {
        exePath = path.join(backendDir, 'dist', 'zenith_backend', 'zenith_backend.exe');
    }
    
    let command, args, cwdToUse;
    
    if (fs.existsSync(exePath)) {
        command = exePath;
        args = ['console'];
        cwdToUse = path.dirname(exePath);
    } else {
        // Fallback to virtual environment (development mode)
        const venvPython = path.join(backendDir, 'venv', 'Scripts', 'python.exe');
        if (fs.existsSync(venvPython)) {
            command = venvPython;
            args = ['agent.py', 'console'];
        } else {
            command = 'cmd.exe';
            args = ['/c', `.\\venv\\Scripts\\activate && python agent.py console`];
        }
        cwdToUse = backendDir;
    }

    // Read .env and inject it so agent.py can access it
    const envVars = { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' };
    try {
      if (fs.existsSync(ENV_PATH)) {
        const content = fs.readFileSync(ENV_PATH, 'utf-8');
        const lines = content.split('\n');
        lines.forEach(line => {
          if (line.includes('=') && !line.trim().startsWith('#')) {
            const [rawKey, ...rest] = line.split('=');
            const key = rawKey.trim();
            let val = rest.join('=').trim();
            if (val.startsWith(`${key}=`)) {
              val = val.substring(`${key}=`.length).trim();
            }
            if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
              val = val.slice(1, -1);
            }
            envVars[key] = val;
          }
        });
      }
    } catch (e) {
      console.error('Failed to parse .env', e);
    }

    if (envVars['ZENITH_INPUT_DEVICE']) {
      args.push('--input-device', envVars['ZENITH_INPUT_DEVICE']);
    }

    zenithProcess = spawn(command, args, {
      cwd: cwdToUse,
      windowsHide: true,
      env: envVars
    });
    
    // Pipe logs manually so we don't need cmd.exe redirect
    const logStream = fs.createWriteStream(path.join(cwdToUse, 'zenith.log'), { flags: 'w' });
    zenithProcess.stdout.pipe(logStream);
    zenithProcess.stderr.pipe(logStream);
    
    zenithProcess.on('exit', () => {
      zenithProcess = null;
      destroyOverlay();
    });

    createOverlay();
    // startScreenStreaming(); // Runs in Smart On-Demand mode by default for zero jitter

    return { status: 'success' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

ipcMain.handle('stop-zenith', () => {
  try {
    if (zenithProcess) {
      const backendDir = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..');
      const stopFile = path.join(backendDir, '.stop_zenith');
      fs.writeFileSync(stopFile, 'stop');
      
      const pidToKill = zenithProcess.pid;
      zenithProcess = null;
      
      const { exec } = require('child_process');
      // Send graceful close signal to let Python run shutdown hooks (memory save)
      exec(`taskkill /pid ${pidToKill} /T`, () => {});
      
      setTimeout(() => {
        // Force kill if it didn't exit gracefully
        exec(`taskkill /pid ${pidToKill} /T /F`, () => {});
        if (fs.existsSync(stopFile)) fs.unlinkSync(stopFile);
      }, 3500);
    }
    destroyOverlay();
    return { status: 'success', message: 'Zenith terminated.' };
  } catch (error) {
    return { status: 'error', message: error.message };
  }
});

ipcMain.handle('check-zenith-status', () => {
  return zenithProcess !== null;
});

ipcMain.handle('toggle-screen-vision', (event, enable) => {
  if (enable) {
    startScreenStreaming();
  } else {
    stopScreenStreaming();
  }
  return { status: 'success', active: isScreenStreamingActive };
});

ipcMain.handle('get-screen-vision-status', () => {
  return { active: isScreenStreamingActive && zenithProcess !== null };
});
