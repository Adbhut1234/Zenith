const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  readEnv: () => ipcRenderer.invoke('read-env'),
  saveEnv: (data) => ipcRenderer.invoke('save-env', data),
  startJarvis: () => ipcRenderer.invoke('start-jarvis'),
  stopJarvis: () => ipcRenderer.invoke('stop-jarvis')
});
