const https = require('https');
const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const REPO_OWNER = 'Adbhut1234';
const REPO_NAME = 'Zenith';
const BRANCH = 'main';

// Safe list of files eligible for Over-The-Air (OTA) micro-updates
const SYNCABLE_FILES = new Set([
  'prompts.py',
  'prompts_data1.py',
  'prompts_data2.py',
  'agent.py',
  'computer_use.py',
  'uia_control.py',
  'ui_state.py',
  'zenith_memory.py',
  'manage_local_memory.py',
  'generate_token.py',
  'agent_tools/web.py',
  'agent_tools/music.py',
  'agent_tools/system.py',
  'VERSION'
]);

function getBackendDir() {
  if (app && app.isPackaged) return process.resourcesPath;
  return path.join(__dirname, '..');
}

function getCommitStateFile() {
  const userDir = (app && typeof app.getPath === 'function') 
    ? app.getPath('userData') 
    : (process.env.APPDATA || __dirname);
  return path.join(userDir, 'last_synced_commit.json');
}

function getLastSyncedSha() {
  try {
    const file = getCommitStateFile();
    if (fs.existsSync(file)) {
      const data = JSON.parse(fs.readFileSync(file, 'utf8'));
      return data.lastSha || null;
    }
  } catch (_) {}
  return null;
}

function saveLastSyncedSha(sha) {
  try {
    const file = getCommitStateFile();
    fs.writeFileSync(file, JSON.stringify({ lastSha: sha, syncedAt: new Date().toISOString() }, null, 2), 'utf8');
  } catch (e) {
    console.error('Failed to save patch sync state:', e);
  }
}

function httpsGetJson(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        'User-Agent': 'Zenith-Desktop-PatchSync',
        'Accept': 'application/json'
      },
      timeout: 10000
    }, (res) => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('Invalid JSON from ' + url));
        }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error('Timeout connecting to GitHub'));
    });
  });
}

function downloadRawFile(fileRelPath, commitSha) {
  return new Promise((resolve, reject) => {
    const rawUrl = `https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${commitSha}/${fileRelPath}`;
    const req = https.get(rawUrl, {
      headers: { 'User-Agent': 'Zenith-Desktop-PatchSync' },
      timeout: 15000
    }, (res) => {
      if (res.statusCode !== 200) {
        return reject(new Error(`HTTP ${res.statusCode} for ${fileRelPath}`));
      }
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => {
        const buffer = Buffer.concat(chunks);
        if (buffer.length < 10 || buffer.toString('utf8', 0, 15).includes('404')) {
          return reject(new Error(`Corrupted or missing download for ${fileRelPath}`));
        }
        resolve(buffer);
      });
    });
    req.on('error', reject);
    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Timeout downloading ${fileRelPath}`));
    });
  });
}

/**
 * Check and apply any micro-patches published to GitHub main branch.
 */
async function syncLatestPatches(notifyCallback) {
  try {
    const notify = (msg) => {
      console.log('[PatchSync]', msg);
      if (typeof notifyCallback === 'function') notifyCallback(msg);
    };

    // 1. Fetch latest commit SHA on main
    const branchInfo = await httpsGetJson(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/commits/${BRANCH}`);
    const latestSha = branchInfo.sha;
    if (!latestSha) return { updated: false, message: 'Could not resolve branch HEAD' };

    const lastSha = getLastSyncedSha();
    if (lastSha === latestSha) {
      return { updated: false, sha: latestSha, message: 'All AI agent patches are already up to date.' };
    }

    notify('Checking for recent AI patch updates...');

    // 2. Fetch commit details to see which files changed
    const commitDetails = await httpsGetJson(`https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/commits/${latestSha}`);
    const changedFiles = commitDetails.files || [];

    const targetFilesToUpdate = changedFiles
      .map(f => f.filename)
      .filter(name => SYNCABLE_FILES.has(name) || (name.startsWith('agent_tools/') && name.endsWith('.py')));

    if (targetFilesToUpdate.length === 0) {
      // Commit changed files we don't hot-patch (e.g. documentation or readme)
      saveLastSyncedSha(latestSha);
      return { updated: false, sha: latestSha, message: 'No executable code patches needed.' };
    }

    notify(`Found ${targetFilesToUpdate.length} updated AI patch(es). Downloading in background...`);
    const backendDir = getBackendDir();
    const updatedList = [];

    for (const relPath of targetFilesToUpdate) {
      try {
        const fileBuffer = await downloadRawFile(relPath, latestSha);
        const localDest = path.join(backendDir, relPath);

        // Ensure parent folder exists (e.g. agent_tools)
        fs.mkdirSync(path.dirname(localDest), { recursive: true });

        // Backup existing file if present
        if (fs.existsSync(localDest)) {
          fs.copyFileSync(localDest, localDest + '.bak');
        }

        fs.writeFileSync(localDest, fileBuffer);
        console.log(`[PatchSync] Patched ${relPath} (${fileBuffer.length} bytes)`);
        updatedList.push(relPath);
      } catch (err) {
        console.warn(`[PatchSync] Skipping file ${relPath}:`, err.message);
      }
    }

    saveLastSyncedSha(latestSha);

    if (updatedList.length > 0) {
      const msg = `Synced ${updatedList.length} AI patch(es): ${updatedList.join(', ')}`;
      notify(msg);
      return { updated: true, files: updatedList, sha: latestSha, message: msg };
    }

    return { updated: false, sha: latestSha, message: 'Patches checked; files kept current.' };
  } catch (error) {
    console.warn('[PatchSync Error]', error.message);
    return { updated: false, error: error.message };
  }
}

module.exports = {
  syncLatestPatches,
  getLastSyncedSha
};
