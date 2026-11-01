const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  readEnv: () => ipcRenderer.invoke('read-env'),
  saveEnv: (data) => ipcRenderer.invoke('save-env', data),
  startZenith: () => ipcRenderer.invoke('start-zenith'),
  stopZenith: () => ipcRenderer.invoke('stop-zenith'),
  checkZenithStatus: () => ipcRenderer.invoke('check-zenith-status'),
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  onUpdateMessage: (callback) => ipcRenderer.on('update-message', (event, msg) => callback(msg)),
  onUpdateProgress: (callback) => ipcRenderer.on('update-progress', (event, percent) => callback(percent)),
  toggleScreenVision: (enable) => ipcRenderer.invoke('toggle-screen-vision', enable),
  getScreenVisionStatus: () => ipcRenderer.invoke('get-screen-vision-status'),
  getSystemTelemetry: () => ipcRenderer.invoke('get-system-telemetry'),
  getCognitiveStats: () => ipcRenderer.invoke('get-cognitive-stats'),
  emergencyKill: () => ipcRenderer.invoke('emergency-kill'),
  minimizeWindow: () => ipcRenderer.invoke('window-minimize'),
  maximizeWindow: () => ipcRenderer.invoke('window-maximize'),
  closeWindow: () => ipcRenderer.invoke('window-close'),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  onUIState: (callback) => ipcRenderer.on('ui-state', (event, state) => callback(state))
});

contextBridge.exposeInMainWorld('electronAPI', {
  onUIState: (callback) => ipcRenderer.on('ui-state', (event, state) => callback(state)),
  onMusicEvent: (callback) => ipcRenderer.on('music-event', (event, data) => callback(data)),
  onWeatherEvent: (callback) => ipcRenderer.on('weather-event', (event, data) => callback(data)),
  setIgnoreMouseEvents: (ignore, options) => ipcRenderer.send('set-ignore-mouse-events', ignore, options)
});
