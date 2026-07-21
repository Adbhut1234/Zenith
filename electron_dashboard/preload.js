const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  readEnv: () => ipcRenderer.invoke('read-env'),
  saveEnv: (data) => ipcRenderer.invoke('save-env', data),
  startZenith: () => ipcRenderer.invoke('start-zenith'),
  stopZenith: () => ipcRenderer.invoke('stop-zenith'),
  checkZenithStatus: () => ipcRenderer.invoke('check-zenith-status'),
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  onUpdateMessage: (callback) => ipcRenderer.on('update-message', (event, msg) => callback(msg)),
  onUpdateProgress: (callback) => ipcRenderer.on('update-progress', (event, percent) => callback(percent))
});
