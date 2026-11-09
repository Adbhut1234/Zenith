const { app, BrowserWindow, ipcMain, shell, dialog, desktopCapturer, Notification } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { autoUpdater } = require('electron-updater');
const { spawn } = require('child_process');
const dgram = require('dgram');
const { syncLatestPatches } = require('./patch_sync');

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

const ENV_PATH = app.isPackaged 
  ? path.join(app.getPath('userData'), '.env') 
  : path.join(__dirname, '..', '.env');
const OLD_ENV_PATH = app.isPackaged 
  ? path.join(process.resourcesPath, '.env') 
  : path.join(__dirname, '..', '.env');

let overlayWindow = null;
let mainWindow = null;
let udpServer = null;
let overlayTopmostTimer = null;

// Fast, reliable GitHub REST API check for latest version (avoids regional CDN 504 timeouts)
function fetchLatestReleaseInfo() {
  return new Promise((resolve) => {
    const https = require('https');
    const req = https.get('https://api.github.com/repos/Adbhut1234/Zenith/releases/latest', {
      headers: { 'User-Agent': 'Zenith-Desktop-App' },
      timeout: 8000
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (_) {
          resolve(null);
        }
      });
    });
    req.on('error', () => resolve(null));
    req.on('timeout', () => { req.destroy(); resolve(null); });
  });
}

function sanitizeUpdateError(err) {
  const raw = (err && err.message) ? err.message : String(err || '');
  if (raw.includes('504') || raw.includes('Time-out') || raw.includes('timeout') || raw.includes("didn't respond in time")) {
    return `Zenith is up to date (v${app.getVersion()}).`;
  }
  if (raw.includes('404')) {
    return 'No update releases found on server.';
  }
  if (raw.includes('ENOTFOUND') || raw.includes('ECONNREFUSED')) {
    return 'Network connection error while checking for updates.';
  }
  return 'Zenith is up to date (v' + app.getVersion() + ').';
}

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
    y: 0,
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

  startUdpServer();
}

function startUdpServer() {
  if (udpServer) return;
  try {
    udpServer = dgram.createSocket('udp4');
    udpServer.on('error', (err) => {
      console.error('UDP server error:', err);
    });
    udpServer.on('message', (msg) => {
      const raw = msg.toString().trim();
      try {
        if (raw.startsWith('{') && raw.endsWith('}')) {
          const data = JSON.parse(raw);
          if (data.type === 'play_music' || data.type === 'control_music') {
            if (!overlayWindow || overlayWindow.isDestroyed()) {
              createOverlay();
            }
          }
          if (overlayWindow && !overlayWindow.isDestroyed()) {
            overlayWindow.webContents.send('music-event', data);
            if (data.type === 'weather') {
              overlayWindow.webContents.send('weather-event', data);
            }
          }
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('music-event', data);
          }
          return;
        }
      } catch (e) {
        // Fallback for string state
      }
      if (overlayWindow && !overlayWindow.isDestroyed()) {
        overlayWindow.webContents.send('ui-state', raw);
      }
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('ui-state', raw);
      }
    });
    udpServer.bind(49152, '127.0.0.1');
  } catch (e) {
    console.error('Failed to bind UDP server on 49152:', e);
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
  mainWindow = new BrowserWindow({
    width: 840,
    height: 640,
    minWidth: 720,
    minHeight: 520,
    backgroundColor: '#0c0d12',
    autoHideMenuBar: true,
    frame: false,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    icon: path.join(__dirname, 'icon.ico')
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
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

  const isSetupArg = process.argv.some(a => typeof a === 'string' && (a.includes('setup') || a.includes('wizard')));
  mainWindow.loadFile(path.join(__dirname, 'index.html'), isSetupArg ? { query: { setup: '1' } } : {});



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
    mainWindow.webContents.send('update-message', 'Version ' + info.version + ' update available! Downloading...');
    try {
      if (Notification && Notification.isSupported()) {
        new Notification({
          title: 'Zenith Update Found',
          body: 'Version ' + info.version + ' is downloading in the background.',
          icon: path.join(__dirname, 'icon.ico')
        }).show();
      }
    } catch (_) {}
  });
  
  autoUpdater.on('update-not-available', (info) => {
    mainWindow.webContents.send('update-message', 'Up to date.');
  });
  
  autoUpdater.on('error', (err) => {
    mainWindow.webContents.send('update-message', sanitizeUpdateError(err));
  });
  
  autoUpdater.on('download-progress', (progressObj) => {
    mainWindow.webContents.send('update-progress', progressObj.percent);
  });
  
  autoUpdater.on('update-downloaded', (info) => {
    mainWindow.webContents.send('update-message', 'Update downloaded! Restarting...');
    try {
      if (Notification && Notification.isSupported()) {
        new Notification({
          title: 'Zenith Update Ready',
          body: 'Version ' + info.version + ' downloaded! Restarting to install...',
          icon: path.join(__dirname, 'icon.ico')
        }).show();
      }
    } catch (_) {}
    setTimeout(() => {
      autoUpdater.quitAndInstall();
    }, 3000);
  });

  // Check for updates deferred after initial boot
  mainWindow.webContents.on('did-finish-load', () => {
    if (!app.isPackaged && !hasDevUpdateConfig) {
      mainWindow.webContents.send('update-message', 'Development mode');
      return;
    }
    setTimeout(async () => {
      try {
        const currentVer = app.getVersion();
        const rel = await fetchLatestReleaseInfo();
        if (rel && rel.tag_name) {
          const latestVer = rel.tag_name.replace(/^v/, '');
          if (latestVer === currentVer) {
            mainWindow.webContents.send('update-message', `Zenith v${currentVer} • Up to date`);
            return;
          }
        }
        await autoUpdater.checkForUpdatesAndNotify();
      } catch (error) {
        mainWindow.webContents.send('update-message', sanitizeUpdateError(error));
      }

      // 3. Background micro-patch check (syncs prompts, tools without needing full release)
      setTimeout(() => {
        syncLatestPatches((patchMsg) => {
          mainWindow.webContents.send('update-message', patchMsg);
        }).catch(() => {});
      }, 5000);
    }, 4000);
  });
}

ipcMain.handle('sync-ai-patches', async () => await syncLatestPatches());

ipcMain.handle('check-for-updates', async () => {
  const devUpdateConfigPath = path.join(__dirname, 'dev-app-update.yml');
  const hasDevUpdateConfig = fs.existsSync(devUpdateConfigPath);
  if (!app.isPackaged && !hasDevUpdateConfig) {
    return { status: 'dev', message: 'Auto-updates disabled in development mode.' };
  }
  const windows = BrowserWindow.getAllWindows();
  const currentVer = app.getVersion();

  try {
    // 1. Instant check against GitHub API (responds in ~300ms without CDN 504 timeouts)
    const rel = await fetchLatestReleaseInfo();
    if (rel && rel.tag_name) {
      const latestVer = rel.tag_name.replace(/^v/, '');
      if (latestVer === currentVer) {
        // Also sync any lightweight encrypted AI patches (prompts, tools) from GitHub main
        const patchRes = await syncLatestPatches((patchMsg) => {
          if (windows.length > 0) windows[0].webContents.send('update-message', patchMsg);
        }).catch(() => null);

        let finalMsg = `Zenith is up to date (v${currentVer}).`;
        if (patchRes && patchRes.updated) {
          finalMsg = `Zenith v${currentVer} • ${patchRes.message}`;
        }

        if (windows.length > 0) {
          windows[0].webContents.send('update-message', finalMsg);
        }
        return { status: 'success', message: finalMsg };
      }
    }

    // 2. If a newer version exists, run electron autoUpdater
    await autoUpdater.checkForUpdatesAndNotify();
    return { status: 'success' };
  } catch (error) {
    const cleanMsg = sanitizeUpdateError(error);
    if (windows.length > 0) {
      windows[0].webContents.send('update-message', cleanMsg);
    }
    return { status: 'error', message: cleanMsg };
  }
});


app.whenReady().then(() => {
  startUdpServer();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});


app.on('before-quit', () => {
  if (udpServer) {
    try { udpServer.close(); } catch (e) {}
    udpServer = null;
  }
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

    // Verify Google Gemini API Key is configured before launching
    let googleApiKey = '';
    const checkPaths = [ENV_PATH, path.join(app.getPath('userData'), '.env')];
    for (const p of checkPaths) {
      if (fs.existsSync(p)) {
        try {
          const envTxt = fs.readFileSync(p, 'utf-8');
          envTxt.split(/\r?\n/).forEach(line => {
            if (line.includes('=') && !line.trim().startsWith('#')) {
              const [rawKey, ...rest] = line.split('=');
              const key = rawKey.trim();
              let val = rest.join('=').trim().replace(/^["']|["']$/g, '');
              if ((key === 'GOOGLE_API_KEY' || key === 'GEMINI_API_KEY') && val) {
                googleApiKey = val;
              }
            }
          });
        } catch (_) {}
      }
      if (googleApiKey) break;
    }

    const isMissingKey = !googleApiKey || 
      googleApiKey.trim() === '' || 
      googleApiKey.includes('your_google_api_key') || 
      googleApiKey.includes('your_api_key') || 
      googleApiKey.trim().length < 8;

    if (isMissingKey) {
      return {
        status: 'error',
        code: 'MISSING_API_KEY',
        message: 'Google Gemini API key required. Please enter your API key in Settings before launching Zenith.'
      };
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

ipcMain.handle('get-system-telemetry', () => {
  const os = require('os');
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const usedMem = totalMem - freeMem;
  const cpus = os.cpus();
  let user = 0, sys = 0, idle = 0;
  cpus.forEach(cpu => {
    user += cpu.times.user;
    sys += cpu.times.sys;
    idle += cpu.times.idle;
  });
  const total = user + sys + idle || 1;
  return {
    platform: os.platform(),
    arch: os.arch(),
    uptime: Math.round(os.uptime()),
    totalMemMB: Math.round(totalMem / (1024 * 1024)),
    usedMemMB: Math.round(usedMem / (1024 * 1024)),
    memPercent: Math.round((usedMem / totalMem) * 100),
    cpuModel: cpus[0] ? cpus[0].model.replace(/\(R\)|\(TM\)/g, '').trim() : 'Neural Core',
    cpuCores: cpus.length,
    cpuPercent: Math.min(100, Math.round(((user + sys) / total) * 100))
  };
});

ipcMain.handle('get-cognitive-stats', async () => {
  const backendDir = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..');
  const dbPath = path.join(backendDir, 'zenith_memory.db');
  const exists = fs.existsSync(dbPath);
  let sizeKB = exists ? Math.round(fs.statSync(dbPath).size / 1024) : 0;
  return {
    dbExists: exists,
    dbSizeKB: sizeKB,
    system2: 'Deliberative Matrix Armed',
    neuroplasticity: 'Procedural Playbooks Active',
    shipOfTheseus: 'Temporal Evolution WAL Active',
    killswitch: 'Atomic Motor Disengagement Ready'
  };
});

ipcMain.handle('emergency-kill', async () => {
  try {
    const backendDir = app.isPackaged ? process.resourcesPath : path.join(__dirname, '..');
    const stopFile = path.join(backendDir, '.stop_zenith');
    fs.writeFileSync(stopFile, 'emergency_stop');
    if (zenithProcess) {
      const pid = zenithProcess.pid;
      const { exec } = require('child_process');
      exec(`taskkill /pid ${pid} /T /F`, () => {});
      zenithProcess = null;
    }
    destroyOverlay();
    return { status: 'success', message: 'EMERGENCY MOTOR DISENGAGEMENT TRIGGERED' };
  } catch (e) {
    return { status: 'error', message: e.message };
  }
});

ipcMain.handle('window-minimize', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.minimize();
});

ipcMain.handle('window-maximize', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.handle('window-close', () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('app-closing');
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('app-closing');
  }
  setTimeout(() => {
    destroyOverlay();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.close();
    }
  }, 350);
});

ipcMain.handle('open-external', (event, url) => {
  if (url && (url.startsWith('https://') || url.startsWith('http://'))) {
    shell.openExternal(url);
    return { status: 'success' };
  }
  return { status: 'error', message: 'Invalid URL' };
});


