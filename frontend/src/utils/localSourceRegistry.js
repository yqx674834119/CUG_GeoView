const registry = new Map();

function toRawFile(entry) {
  if (!entry) {
    return null;
  }
  if (entry instanceof File) {
    return entry;
  }
  if (entry.raw instanceof File) {
    return entry.raw;
  }
  return null;
}

function revokeExisting(path) {
  const current = registry.get(path);
  if (current?.objectUrl) {
    try {
      URL.revokeObjectURL(current.objectUrl);
    } catch (error) {
      // ignore revoke failures
    }
  }
}

export function registerLocalSource(path, file, meta = {}) {
  const rawFile = toRawFile(file);
  if (!path || !rawFile) {
    return null;
  }
  revokeExisting(path);
  const objectUrl = URL.createObjectURL(rawFile);
  const record = {
    path,
    objectUrl,
    file: rawFile,
    filename: meta.filename || rawFile.name,
    mime: meta.mime || rawFile.type || "",
    size: rawFile.size || 0,
    createdAt: Date.now(),
  };
  registry.set(path, record);
  return record;
}

function takeByName(nameMap, fallbackFiles, filename) {
  const named = nameMap.get(filename);
  if (named?.length) {
    return named.shift();
  }
  return fallbackFiles.shift() || null;
}

export function registerUploadedSources(uploadedItems = [], fileEntries = []) {
  const files = fileEntries.map(toRawFile).filter(Boolean);
  const filesByName = new Map();
  files.forEach((file) => {
    const bucket = filesByName.get(file.name) || [];
    bucket.push(file);
    filesByName.set(file.name, bucket);
  });
  const fallbackFiles = [...files];

  return uploadedItems.map((item) => {
    const file = takeByName(filesByName, fallbackFiles, item?.filename);
    return registerLocalSource(item?.src, file, {
      filename: item?.filename,
    });
  }).filter(Boolean);
}

export function getLocalSource(path) {
  return registry.get(path) || null;
}

export function getLocalSourceUrl(path) {
  return getLocalSource(path)?.objectUrl || "";
}

export function hasLocalSource(path) {
  return registry.has(path);
}

export function clearLocalSource(path) {
  revokeExisting(path);
  registry.delete(path);
}

export function listLocalSources() {
  return Array.from(registry.values());
}
