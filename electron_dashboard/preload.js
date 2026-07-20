const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  readEnv: () => ipcRenderer.invoke('read-env'),
  saveEnv: (data) => ipcRenderer.invoke('save-env', data),
  startZenith: () => ipcRenderer.invoke('start-zenith'),
  stopZenith: () => ipcRenderer.invoke('stop-zenith'),
  checkZenithStatus: () => ipcRenderer.invoke('check-zenith-status')
});
